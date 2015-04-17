#encoding: utf8

import functools
import copy

from rejit.common import RejitError
from rejit.common import special_chars

from rejit.nfa import NFA
from rejit.dfa import DFA

class RegexParseError(RejitError): pass

class RegexCompilationError(RejitError): pass

class RegexMatcherError(RejitError): pass

class Regex:
    def __init__(self, pattern=None):
        self.pattern = pattern
        self._ast = None
        self._final_ast = None
        self._matcher = None
        self._matcher_type = 'None'
        if self.pattern is not None:
            self._ast = self._parse(pattern)
            self._final_ast = self._transform(self._ast)
            self._matcher = self._compile(self._final_ast)
            self._matcher_type = 'NFA'

    def accept(self, s):
        if self._matcher:
            return self._matcher.accept(s)
        raise RegexMatcherError("No matcher found")

    def get_matcher_description(self):
        if self._matcher:
            return self._matcher.description
        raise RegexMatcherError("No matcher found")

    @property
    def description(self):
        return self.get_matcher_description()

    def compile_to_DFA(self):
        if self._matcher_type != 'NFA':
            raise RegexCompilationError(
                    "Can only compile NFA-type matcher to a DFA. Current matcher type: {}".format(self._matcher_type))
        self._matcher = DFA(self._matcher)
        self._matcher_type = 'DFA'

    def _getchar(self):
        if self._input:
            self._last_char = self._input[0]
            self._input = self._input[1:]
        else:
            self._last_char = ''

    def _parse(self, pattern):
        self._input = pattern
        self._last_char = ''
        self._getchar()
        if not self._last_char:
            return ('empty',)
        else:
            ast = self._unionRE()
            if self._last_char == ')':
                raise RegexParseError('Unmatched parentheses')
            return ast

    def _compile(self, ast):
        if ast[0] == 'concat':
            return NFA.concat_many(list(map(self._compile, ast[1])))
        elif ast[0] == 'union':
            return NFA.union_many(list(map(self._compile, ast[1])))
        elif ast[0] == 'kleene-star':
            return NFA.kleene(self._compile(ast[1]))
        elif ast[0] == 'kleene-plus':
            return NFA.kleene_plus(self._compile(ast[1]))
        elif ast[0] == 'zero-or-one':
            return NFA.zero_or_one(self._compile(ast[1]))
        elif ast[0] == 'any':
            return NFA.any()
        elif ast[0] == 'empty':
            return NFA.empty()
        elif ast[0] == 'symbol':
            return NFA.symbol(ast[1])
        elif ast[0] == 'set':
            return NFA.char_set(ast[1],ast[2])
        raise RegexCompilationError("Unknown AST node: {node}".format(node=ast))

    def _transform(self, input_ast):
        return functools.reduce(
            lambda ast, transform: transform(ast),
            [
                functools.partial(self._flatten_nodes,'concat'),
                functools.partial(self._flatten_nodes,'union'),
                self._simplify_quant,
            ],
            input_ast)

    def _flatten_nodes(self, node_type, ast):
        # for a list of nodes return a list of transformed nodes
        if isinstance(ast, list):
            return list(map(functools.partial(self._flatten_nodes,node_type), ast))
        # for leaf nodes return a copy 
        if ast[0] in ['any','empty','symbol','set']:
            return copy.deepcopy(ast)
        # for nodes with children return node with its children transformed by `_flatten_nodes`
            # for tuple based node ast[1:] are children
            # ('type', _flatten(child1), _flatten(child2))
            # for list based node ast[1] is a list of children
            # ('type', [ _flatten(child1), _flatten(child2)]
        if ast[0] != node_type:
            return tuple([ast[0]] + list(map(functools.partial(self._flatten_nodes,node_type), ast[1:])))
        # for `concat` node transform children with `flatten_nodes`
        left = self._flatten_nodes(node_type,ast[1][0])
        right = self._flatten_nodes(node_type,ast[1][1])
        # `concat` node list is created from lists extracted from children `concat` nodes, or by simply inserting other nodes
        node_list = (left[1] if left[0] == node_type else [left]) + (right[1] if right[0] == node_type else [right])
        return (node_type , node_list)

    def _simplify_quant(self, ast):
        quant_nodes = {'kleene-star','kleene-plus','zero-or-one'}
        if isinstance(ast, list):
            return list(map(self._simplify_quant, ast))
        if ast[0] in ['any','empty','symbol','set']:
            return copy.deepcopy(ast)
        if ast[0] not in quant_nodes:
            return tuple([ast[0]] + list(map(self._simplify_quant, ast[1:])))
        child = self._simplify_quant(ast[1])
        if child[0] in quant_nodes:
            if child[0] == ast[0] == 'kleene-plus':
                return ('kleene-plus', child[1])
            elif child[0] == ast[0] == 'zero-or-one':
                return ('zero-or-one', child[1])
            else:
                return ('kleene-star', child[1])
        else:
            return (ast[0], child)

    def _unionRE(self):
        ast1 = self._concatRE()
        if self._last_char == '|':
            self._getchar() # '|'
            ast2 = self._unionRE()
            return ('union',[ast1,ast2])
        return ast1

    def _concatRE(self):
        ast1 = self._kleeneRE()
        if self._last_char and self._last_char not in '|)':
            ast2 = self._concatRE()
            return ('concat', [ast1, ast2])
        return ast1

    def _kleeneRE(self):
        ast = self._elementaryRE()
        if self._last_char == '*':
            self._getchar() # '*'
            return ('kleene-star', ast)
        elif self._last_char == '+':
            self._getchar() # '+'
            return ('kleene-plus', ast)
        elif self._last_char == '?':
            self._getchar() # '?'
            return ('zero-or-one', ast)
        else:
            return ast

    def _elementaryRE(self):
        if self._last_char == '(':
            self._getchar()
            ast_paren = self._unionRE()
            if self._last_char != ')':
                raise RegexParseError('Expected ")", got {}'.format(self._last_char))
            self._getchar() # ')'
            return ast_paren
        elif self._last_char == '.':
            self._getchar() # '.'
            return ('any',)
        elif self._last_char == '[':
            return self._parse_charset()
        elif self._last_char == '':
            raise RegexParseError('Unexpected end of the pattern')
        else:
            return self._symbolRE()

    def _symbolRE(self):
        if self._last_char in special_chars and self._last_char != '\\':
            raise RegexParseError('Unescaped special character "{}" can\'t be used here'.format(self._last_char))
        if self._last_char == "\\":
            self._getchar() # '\'
        if not self._last_char:
            raise RegexParseError('Unexpected end of the pattern after an escape character "\\"')
        ast = ('symbol', self._last_char)
        self._getchar()
        return ast

    def _parse_charset(self):
        self._getchar() # '['
        symbol_list = []
        charset_desc = '['
        if self._last_char == '^':
            raise RegexParseError('Negative character set not supported')
        while self._last_char and self._last_char != ']':
            symbol1 = self._last_char
            self._getchar()
            if self._last_char == '-':
                self._getchar() # '-'
                if self._last_char:
                    charset_desc += symbol1 + '-'
                    symbol_list += list(Regex.char_range(symbol1,self._last_char))
                    charset_desc += self._last_char
                    self._getchar()
                else:
                    raise RegexParseError('Expected a symbol after "-" but the end of the pattern reached')
            else:
                charset_desc += symbol1
                symbol_list.append(symbol1)
        if self._last_char != ']':
            raise RegexParseError('Expected "]" but end of the pattern reached'.format(self._last_char))
        self._getchar() # ']'
        charset_desc += ']'
        ast = ('set',symbol_list,charset_desc)
        return ast

    @staticmethod
    def char_range(c1, c2):
        """Generates the characters from `c1` to `c2`, inclusive."""
        for c in range(ord(c1), ord(c2)+1):
            yield chr(c)

