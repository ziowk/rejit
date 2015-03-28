#encoding: utf8

import functools
import string
import copy

class RegexError(Exception): pass

class RegexParseError(RegexError): pass

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
        return functools.reduce(lambda x, st: x | NFA._get_char_states(st,char) | NFA._get_char_states(st,'any'), in_to_check, set())

    @staticmethod
    def empty():
        n = NFA(State(),State())
        n._start.add('',n._end)
        n._description = '\\E'
        return n

    @staticmethod
    def symbol(a):
        n = NFA(State(),State())
        n._start.add(a,n._end)
        n._description = a
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
        s._end._edges = t._start._edges
        # the END state of S now shares the edge list with the START state of T.
        # alternatively we can just add an empty edge from S._end to T._start
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

class Regex:
    def __init__(self, pattern):
        self.pattern = pattern
        self._matcher = self._parse(pattern)

    def accept(self, s):
        return self._matcher.accept(s)

    def get_parsed_description(self):
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
        return self._unionRE()

    def _unionRE(self):
        r1 = self._concatRE()
        if self._last_char == '|':
            self._getchar() # '|'
            r2 = self._unionRE()
            return NFA.union(r1,r2)
        return r1

    def _concatRE(self):
        r1 = self._kleeneRE()
        if self._last_char and self._last_char not in '|)':
            return NFA.concat(r1,self._concatRE())
        return r1

    def _kleeneRE(self):
        relem = self._elementaryRE()
        if self._last_char == '*':
            self._getchar() # '*'
            return NFA.kleene(relem)
        elif self._last_char == '+':
            self._getchar() # '+'
            return NFA.concat(relem,NFA.kleene(copy.deepcopy(relem)))
        elif self._last_char == '?':
            self._getchar() # '?'
            return NFA.union(relem,NFA.empty())
        else:
            return relem

    def _elementaryRE(self):
        if self._last_char == '(':
            self._getchar()
            rparen = self._unionRE()
            if self._last_char != ')':
                raise RegexParseError('Expected ")", got {}'.format(self._last_char))
            self._getchar() # ')'
            return rparen
        elif self._last_char == '.':
            self._getchar() # '.'
            return NFA.any()
        elif self._last_char == '[':
            return self._parse_charset()
        elif self._last_char == '':
            #assert self.pattern == ''
            return NFA.empty()
        else:
            if self._last_char not in supported_chars:
                raise RegexParseError('Not supported character "{}"'.format(self._last_char))
            rchar = NFA.symbol(self._last_char)
            self._getchar()
            return rchar

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
        if not symbol_list:
            reg = NFA.none()
        else:
            reg = functools.reduce(lambda acc, x: NFA.union(acc, NFA.symbol(x)),symbol_list[1:],NFA.symbol(symbol_list[0]))
        return reg

    @staticmethod
    def char_range(c1, c2):
        """Generates the characters from `c1` to `c2`, inclusive."""
        for c in range(ord(c1), ord(c2)+1):
            yield chr(c)


supported_chars = string.ascii_letters + string.digits

