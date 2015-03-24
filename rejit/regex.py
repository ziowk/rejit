#encoding: utf8

import functools

class RegexError(Exception): pass

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

