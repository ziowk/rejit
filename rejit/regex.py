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
    """Nondeterministic finite automaton for accepting regular languages.

    A NFA is essentially a graph, made of states connected by edges. All edges
    in the automaton form a transition function. There are two special states
    in the NFA: `_start` state from which the automaton starts, and `_end`
    state, which is the accepting state. For details regarding states and edges
    see `State` class docs.

    A NFA object can be used to determine if a string belongs to the NFA's
    accepted language. The NFA's accepted language is equivalent to a regular
    expression, which means that the NFA can be used for matching them.

    NFA objects should only be created with NFA generation methods or
    combined using NFA combination methods. NFA generation methods create new
    basic NFA objects. NFA combination methods transform input NFA objects
    to create complex ones out of them.

    NFA class uses a concept of object validity. Only a valid object can
    be used to `accept` strings, or be passed to NFA's combination methods.
    
    Valid objects are ones created with NFA's generation methods or returned
    from NFA's combination methods.

    Invalid objects are ones passed to NFA's combination methods. If user wants
    to use a NFA object after it was passed to a NFA's combining method, user
    should create a copy of the NFA using `deepcopy` method from standard
    library's `copy` module.

    Attributes:
    description (str): read-only property containing regular expression
        equivalent of the NFA
    valid (bool): indicates if the NFA object is valid for use
    _start (State): NFA's starting state
    _end (State): NFA's finishing state
    _description (str): internal variable for `description` property
    """

    def __init__(self,start,end):
        """Construct an empty NFA object with starting and finishing states

        Warning:
        User probably should never directly create NFAs. Use NFA's generation
        methods such as `empty`, `none`, `any`, `symbol`, `char_set` and
        combine them using NFA's combination methods `union`, `concat`,
        `kleene`, `kleene_plus`, `union_many`, `concat_many`, `zero_or_one`.

        Args:
        start (State): NFA's starting state
        end (State): NFA's finishing state

        Returns:
        An empty NFA object with provided starting and finishing states
            and empty description.
        """
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
        """Check if a string belongs to the NFA's accepted language.

        In other words, this checks if the string exactly matches the NFA's
        regular expression equivalent.

        Args:
        s (str): the string which is tested for a match

        Returns:
        A bool which indicates if the string is accepted by the NFA.
        """
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
        """Invalidate a NFA object making it not suitable for any use.
        
        Any use of an invalid NFA object will result in raising
        an NFAInvalidError.
        """
        self._start = None
        self._end = None
        self._description = None

    @staticmethod
    def _get_char_states(state, char):
        """Return a set of states connected to a `state` by an immediate edge
        labeled exactly with `char` string.

        Args:
        state (State): the state from which the search is performed
        char (str): the edge's label which filters the search

        Returns:
        A set of states connected to a `state` by an immediate edge labeled
        exactly with `char` string.
        """
        return set(map(lambda edge: edge[1], filter(lambda edge: edge[0]==char, state._edges)))

    @staticmethod
    def _moveEpsilon(in_to_check):
        """Return a set of states which are reachable from the input
        set of states by using epsilon-moves only.

        Note:
        Returned set includes also `in_to_check` states, which are reachable
        a priori.

        Args:
        in_to_check (set of States): the set of states from which the search
            is performed

        Returns:
        A set of states rechable from the input set by using epsilon-moves only.
        """
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
        """Return a set of states which are reachable from the input set
        of states by consuming `char` character without eplison-moves.

        Args:
        in_to_check (set of States): the set of states from which the search
            is performed
        char (str): a character to be consumed by the move

        Returns:
        A set of states which are reachable from the input set of states
        by consuming `char` character without eplison-moves.
        """
        return functools.reduce(
                lambda x, st: x | NFA._get_char_states(st,char) | NFA._get_char_states(st,'any'),
                in_to_check,
                set())

    @staticmethod
    def empty():
        """Return `empty` NFA which accepts only an empty string.

        `empty` NFA is described as regular expression `\E`, which imitates
        epsilon letter, unavailable on Windows' console.

        Returned NFA object is valid.

        Returns:
        A valid NFA which accepts only an empty string.
        """
        n = NFA(State(),State())
        n._start.add('',n._end)
        n._description = r'\E'
        return n

    @staticmethod
    def symbol(a):
        """Return a NFA which accepts only literal character from parameter `a`.

        `symbol` NFA is described as regular expression by its character `a`,
        but the character in the description might be escaped using backslash
        `\\` if it is one of the special characters.
        (see rejit.regex.special_chars)

        Returned NFA object is valid.

        Args:
        a (str): A literal character which will be the only accepted one.

        Returns:
        A valid NFA which accepts only literal character from parameter `a`.
        """
        n = NFA(State(),State())
        n._start.add(a,n._end)
        n._description = escape_symbol(a)
        return n

    @staticmethod
    def any():
        """Return a NFA which accepts any single character.

        `any` NFA is described as regular expression `.` (period).

        Returned NFA object is valid.

        Returns:
        A valid NFA which accepts any single character.
        """
        n = NFA(State(),State())
        n._start.add('any',n._end)
        n._description = '.'
        return n

    @staticmethod
    def none():
        """Return a NFA which accepts empty set.

        `none` NFA doesn't accept any input, it returns `False` for every
        possible string passed to `accept`. `none` NFA is described as regular
        expression `[]` which means empty set of characters.

        Returned NFA object is valid.

        Returns:
        A valid NFA which accepts empty set.
        """
        n = NFA(State(),State()) 
        n._description = '[]'
        return n

    @staticmethod
    def char_set(char_list, description):
        """Return a NFA which accepts one character from a set.

        `char_set` NFA accepts a string which comprises exactly one character
        from a set of character literals. Character set is passed by a
        `char_list` - list of str, which allows duplicates. Duplicates don't
        change the behavior of the NFA, but result in creation of unnecessary
        states and edges in the NFA, and thus it is discouraged.

        `char_list` can be empty. Returned NFA is equivalent to `none` NFA.

        `char_set` is also passed a `description` parameter, which is used
        as a description of the NFA. The external description is used because
        any description created knowing only `char_list` could be misleading.
        Example: for a regular expression `[a-e]` user passes a list
        `['a','b','c','d','e']`, but `char_set` doesn't know whether user had
        `[a-e]` or `[abcde]` in mind. Therefore user has to pass the expected
        description.

        Returned NFA object is valid.

        Warning:
        This method is likely to change in future versions.

        Args:
        char_list (list of str): A list of character literals one of which
            should be accepted. Allows duplicates. Can be empty.
        description (str): A regular expression description for the NFA.
            Due to its limitations, `char_set` can't reconstruct the expected
            description from `char_list` only.

        Returns:
        A NFA which accepts one character from a set.
        """
        # Empty set results in `none` NFA, as in `union_many`
        n = NFA.union_many(list(map(NFA.symbol, char_list)))
        n._description = description
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

    @staticmethod
    def zero_or_one(s):
        # validation and invalidation of `s` is performed inside `union`
        s_description = s._description
        n = NFA.union(s,NFA.empty())
        n._description = '('+s_description+')?'
        return n
    
    @staticmethod
    def concat_many(concat_list):
        # Validation of elements of `concat_list` is performed also outside of `concat`,
        # because `concat_many` shouldn't invalidate part of `concat_list` before reaching
        # an invalid NFA.
        # Invalidation of elements of `concat_list` is performed
        # inside `concat`. This algorithm sets good description without
        # intervention. 
        # Empty list results in `empty` NFA
        if not concat_list:
            return NFA.empty()
        if not all(map(lambda x: x.valid, concat_list)):
            raise NFAInvalidError('Trying to use invalid NFA object')
        if len(set(concat_list)) != len(concat_list):
            raise NFAArgumentError("Can't use the same object more than once in the concat_list")
        return functools.reduce(
                lambda acc, x: NFA.concat(acc,x),
                concat_list
            )

    @staticmethod
    def union_many(union_list):
        # Empty list results in `none` NFA
        if not union_list:
            return NFA.none()
        if not all(map(lambda x: x.valid, union_list)):
            raise NFAInvalidError('Trying to use invalid NFA object')
        if len(set(union_list)) != len(union_list):
            raise NFAArgumentError("Can't use the same object more than once in the union_list")
        n = NFA(State(),State())
        for u in union_list:
            n._start.add('',u._start)
            u._end.add('',n._end)
        n._description = '(' + functools.reduce(lambda acc, x: acc+"|"+x.description,union_list[1:],union_list[0].description) + ')'
        for x in union_list:
            x._invalidate()
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

def escape_symbol(symbol):
    return "\\" + symbol if symbol in special_chars else symbol

supported_chars = string.ascii_letters + string.digits + '`~!@#$%&=_{}:;"\'<>,/'
special_chars = '\\^*()-+[]|?.'

