#encoding: utf8

import functools
import string
import copy

class RegexError(Exception): pass

class RegexParseError(RegexError): pass

class RegexCompilationError(RegexError): pass

class NFAInvalidError(RegexError): pass

class NFAArgumentError(RegexError): pass

class State:
    _state_counter = 0
    def __init__(self):
        self._edges = [] # Edge = ('char', State)
        self._state_num = State._state_counter # for printing purposes only
        State._state_counter += 1

    def add(self,edge,state):
        self._edges.append((edge,state))

    def __repr__(self):
        return '<State: {num}, id: {ident}, edges: {e}>'.format(num=str(self._state_num), ident=str(id(self)),
                                                                e=list(map(lambda x: (x[0],x[1]._state_num), self._edges)))
    def __deepcopy__(self, memo):
        st = State()
        st._edges = copy.deepcopy(self._edges, memo)
        return st

class NFA:
    def __init__(self,start,end):
        self._start = start
        self._end = end
        self._description = ''

    @property
    def description(self):
        return self._description

    @property
    def valid(self):
        return self._start is not None

    def accept(self,s):
        if not self.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        states = {self._start}
        while states:
            states = NFA._moveEpsilon(states)
            if not s:
                break
            states = NFA._moveChar(states,s[0])
            s = s[1:]
        return self._end in states and s == ''

    def __str__(self):
        return '<NFA id: {ident}, regex: {desc}>'.format(ident=id(self), desc=self.description)

    def _invalidate(self):
        self._start = None
        self._end = None
        self._description = None

    @staticmethod
    def _get_char_states(state, char):
        return set(map(lambda edge: edge[1], filter(lambda edge: edge[0]==char, state._edges)))

    @staticmethod
    def _moveEpsilon(in_to_check):
        to_check = in_to_check.copy()
        checked = set()
        while to_check:
            st = to_check.pop()
            checked.add(st)
            new = NFA._get_char_states(st,'')
            to_check = (to_check | new) - checked
        assert in_to_check <= checked
        return checked

    @staticmethod
    def _moveChar(in_to_check, char):
        return functools.reduce(
                lambda x, st: x | NFA._get_char_states(st,char) | NFA._get_char_states(st,'any'),
                in_to_check,
                set())

    @staticmethod
    def empty():
        n = NFA(State(),State())
        n._start.add('',n._end)
        n._description = r'\E'
        return n

    @staticmethod
    def symbol(a):
        n = NFA(State(),State())
        n._start.add(a,n._end)
        n._description = escape_symbol(a)
        return n

    @staticmethod
    def any():
        n = NFA(State(),State())
        n._start.add('any',n._end)
        n._description = '.'
        return n

    @staticmethod
    def none():
        n = NFA(State(),State()) 
        n._description = '[]'
        return n

    @staticmethod
    def union(s,t):
        if not s.valid or not t.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        if s is t:
            raise NFAArgumentError("Can't use the same object for both parameters")
        n = NFA(State(),State())
        n._start.add('',s._start)
        n._start.add('',t._start)
        s._end.add('',n._end)
        t._end.add('',n._end)
        n._description = '('+s._description+'|'+t._description+')'
        s._invalidate()
        t._invalidate()
        return n

    @staticmethod
    def concat(s,t):
        if not s.valid or not t.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        if s is t:
            raise NFAArgumentError("Can't use the same object for both parameters")
        n = NFA(s._start,t._end)
        s._end.add('',t._start)
        n._description = s._description+t._description
        s._invalidate()
        t._invalidate()
        return n

    @staticmethod
    def kleene(s):
        if not s.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        q = State()
        f = State()
        q.add('',s._start)
        q.add('',f)
        s._end.add('',s._start)
        s._end.add('',f)
        n = NFA(q,f)
        n._description = '('+s._description+')*'
        s._invalidate()
        return n

    @staticmethod
    def kleene_plus(s):
        # validation and invalidation of `s` is performed inside `concat`
        s_copy = copy.deepcopy(s)
        s_description = s._description
        n = NFA.concat(s,NFA.kleene(s_copy))
        n._description = '('+s_description+')+'
        return n

class Regex:
    def __init__(self, pattern=None):
        if pattern is not None:
            self.pattern = pattern
            self._ast = self._parse(pattern)
            self._final_ast = self._transform(self._ast)
            self._matcher = self._compile(self._final_ast)

    def accept(self, s):
        return self._matcher.accept(s)

    def get_NFA_description(self):
        return self._matcher.description

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
            concat_list = ast[1]
            assert len(concat_list) > 1
            return functools.reduce(
                    lambda acc, x: NFA.concat(self._compile(x),acc),
                    reversed(concat_list[:-2]),
                    NFA.concat(self._compile(concat_list[-2]),self._compile(concat_list[-1]))
                )
        elif ast[0] == 'union':
            union_list = ast[1]
            assert len(union_list) > 1
            return functools.reduce(
                    lambda acc, x: NFA.union(self._compile(x),acc),
                    reversed(union_list[:-2]),
                    NFA.union(self._compile(union_list[-2]),self._compile(union_list[-1]))
                )
            return NFA.union(self._compile(ast[1][0]),self._compile(ast[1][1]))
        elif ast[0] == 'kleene-star':
            return NFA.kleene(self._compile(ast[1]))
        elif ast[0] == 'kleene-plus':
            return NFA.kleene_plus(self._compile(ast[1]))
        elif ast[0] == 'zero-or-one':
            return NFA.union(self._compile(ast[1]),NFA.empty())
        elif ast[0] == 'any':
            return NFA.any()
        elif ast[0] == 'empty':
            return NFA.empty()
        elif ast[0] == 'symbol':
            return NFA.symbol(ast[1])
        elif ast[0] == 'set':
            symbol_list = ast[1]
            if not symbol_list:
                return NFA.none()
            else:
                return functools.reduce(
                        lambda acc, x: NFA.union(acc, NFA.symbol(x)),
                        symbol_list[1:],
                        NFA.symbol(symbol_list[0]))
        raise RegexCompilationError("Unknown AST node: {node}".format(node=ast))

    def _transform(self, input_ast):
        return functools.reduce(
            lambda ast, transform: transform(ast),
            [
                functools.partial(self._flatten_nodes,'concat'),
                functools.partial(self._flatten_nodes,'union'),
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
        if self._last_char == '^':
            raise RegexParseError('Negative character set not supported')
        while self._last_char and self._last_char != ']':
            symbol1 = self._last_char
            self._getchar()
            if self._last_char == '-':
                self._getchar() # '-'
                if self._last_char:
                    symbol_list += list(Regex.char_range(symbol1,self._last_char))
                    self._getchar()
                else:
                    raise RegexParseError('Expected a symbol after "-" but the end of the pattern reached')
            else:
                symbol_list.append(symbol1)
        if self._last_char != ']':
            raise RegexParseError('Expected "]" but end of the pattern reached'.format(self._last_char))
        self._getchar() # ']'
        ast = ('set',symbol_list)
        return ast

    @staticmethod
    def char_range(c1, c2):
        """Generates the characters from `c1` to `c2`, inclusive."""
        for c in range(ord(c1), ord(c2)+1):
            yield chr(c)

def escape_symbol(symbol):
    return "\\" + symbol if symbol in special_chars else symbol

supported_chars = string.ascii_letters + string.digits + '`~!@#$%&=_{}:;"\'<>,/'
special_chars = '\\^*()-+[]|?.'

