#encoding: utf8

import functools
import string

class RegexError(Exception): pass

class RegexParseError(RegexError): pass

class State:
    state = 0
    def __init__(self):
        self.e = [] # Edge = ('char', State)
        self.s = State.state # for printing purposes only
        State.state += 1

    def add(self,edge,state):
        self.e.append((edge,state))

    def __repr__(self):
        return '<State: {num}, id: {ident}, edges: {e}>'.format(num=str(self.s), ident=str(id(self)),
                                                                e=list(map(lambda x: (x[0],x[1].s), self.e)))

class NFA:
    def __init__(self,start,end):
        self.start = start
        self.end = end
        self.description = ''

    def accept(self,s):
        states = {self.start}
        while states:
            states = NFA.moveEpsilon(states)
            if not s:
                break
            states = NFA.moveChar(states,s[0])
            s = s[1:]
        return self.end in states and s == ''

    def __str__(self):
        return self.description

    @staticmethod
    def get_char_states(state, char):
        return set(map(lambda edge: edge[1], filter(lambda edge: edge[0]==char, state.e)))

    @staticmethod
    def moveEpsilon(in_to_check):
        to_check = in_to_check.copy()
        checked = set()
        while to_check:
            st = to_check.pop()
            checked.add(st)
            new = NFA.get_char_states(st,'')
            to_check = (to_check | new) - checked
        assert in_to_check <= checked
        return checked

    @staticmethod
    def moveChar(in_to_check, char):
        return functools.reduce(lambda x, st: x | NFA.get_char_states(st,char), in_to_check, set())

    @staticmethod
    def empty():
        n = NFA(State(),State())
        n.start.add('',n.end)
        n.description = '\\E'
        return n

    @staticmethod
    def symbol(a):
        n = NFA(State(),State())
        n.start.add(a,n.end)
        n.description = a
        return n

    @staticmethod
    def union(s,t):
        n = NFA(State(),State())
        n.start.add('',s.start)
        n.start.add('',t.start)
        s.end.add('',n.end)
        t.end.add('',n.end)
        n.description = '('+s.description+'|'+t.description+')'
        return n

    @staticmethod
    def concat(s,t):
        n = NFA(s.start,t.end)
        s.end.e = t.start.e
        # the END state of S now shares the edge list with the START state of T.
        # alternatively we can just add an empty edge from S.end to T.start
        n.description = s.description+t.description
        return n

    @staticmethod
    def kleene(s):
        q = State()
        f = State()
        q.add('',s.start)
        q.add('',f)
        s.end.add('',s.start)
        s.end.add('',f)
        n = NFA(q,f)
        n.description = '('+s.description+')*'
        return n

class Regex:
    def __init__(self, pattern):
        self.pattern = pattern
        self._matcher = self._parse(pattern)

    def accept(self, s):
        return self._matcher.accept(s)

    def get_parsed_description(self):
        return str(self._matcher)

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
            raise NotImplementedError('Kleene plus not implemented yet')
            # return NFA.concat(relem,NFA.kleene(relem)) # deep copy of relem needed to pass to NFA.kleene
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
            raise NotImplementedError('Period character wildcard not implemented yet')
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
        raise NotImplementedError('Character set parsing not implemented yet')


supported_chars = string.ascii_letters + string.digits

