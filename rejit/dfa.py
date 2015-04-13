#encoding: utf8

import functools
import collections

from rejit.nfa import NFA
from rejit.nfa import NFAInvalidError

try:
    import graphviz
except ImportError:
    pass

class DFA:
    def __init__(self, nfa):
        if not nfa.valid:
            raise NFAInvalidError('Trying to use an invalid NFA object')

        # all nfa's states reachable from the start state
        nfa_states = frozenset(NFA._get_all_reachable_states(nfa._start))

        # nfa described without use of epsilon edges.
        # nfa_state_edges is constructed as {state_num: {char: {state_num}}}
        # which maps state_num to dictionaries which map each char to 
        # a set of state_nums which are reachable from the state using that char
        nfa_state_edges = {
                st._state_num: DFA._nfa_char2statenum_set(st)
                for st in nfa_states
            }

        # newstates is an early representation of the constructed DFA
        # newstates is constructed as {multiname: {char: {state_num}}} where
        # multiname key is a string which describes a set of states from the nfa
        # and it points to a dictionary which map each char to a set of 
        # state_nums which are reachable from the set of states using that char.
        # newstates is initialized with multistates which correspond to 
        # the nfa's states.
        newstates = {DFA._multistate_name({num}): c2s for num,c2s in nfa_state_edges.items()}

        # m2ss dict maps multiname to a corresponding state_num set
        m2ss = {DFA._multistate_name({num}): {num} for num in nfa_state_edges}

        # toadd contains sets of state_nums which are multistates to be added to newstates
        toadd = [s for st,d in nfa_state_edges.items() for char,s in d.items()]

        while toadd:
            states = toadd.pop()
            name = DFA._multistate_name(states)
            # check if they are already added, if not create a multistate by merging singlestates
            if name not in newstates:
                _, c2s = DFA._merge_states(states,nfa_state_edges)
                newstates[name] = c2s
                m2ss[name] = states
                # merging multistate could create new multistates to add 
                for char,s in c2s.items():
                    toadd.append(s)

        # convert newstates to {multiname:{char:multiname}} dict
        for st,c2s in newstates.items():
            for c,s in c2s.items():
                c2s[c] = DFA._multistate_name(s)

        # end states are multistates which contain nfa._end state ...
        end_states = set(filter(lambda st: nfa._end._state_num in m2ss[st], newstates))
        # ... and singlestates from nfa which can reach nfa._end with epsilon-moves
        end_states |= set(map(
            lambda st: DFA._multistate_name({st._state_num}), 
            filter(lambda st: nfa._end in NFA._moveEpsilon({st}), nfa_states)))

        # filter unreachable multistates from newstates
        reachable_newstates = set()
        to_check = {DFA._multistate_name({nfa._start._state_num})}
        while to_check:
            st = to_check.pop()
            reachable_newstates.add(st)
            to_check |= set(filter(lambda x: x not in reachable_newstates, newstates[st].values()))

        newstates = dict(filter(lambda kv: kv[0] in reachable_newstates, newstates.items()))

        # filter unreachable multistates from end_states
        end_states = set(filter(lambda st: st in reachable_newstates, end_states))

        # save relevant data
        # start state
        self._start = DFA._multistate_name({nfa._start._state_num})
        # DFA state/edge dict
        self._states_edges = newstates
        # set of accepting states
        self._end_states = frozenset(end_states)
        # description
        self._description = nfa.description

    @property
    def description(self):
        return self._description

    def accept(self,s):
        state = self._start
        while s:
            # check for char edge from current state
            if s[0] in self._states_edges[state]:
                state = self._states_edges[state][s[0]]
                s = s[1:]
            # check also for `any` edge, but only after char edges
            elif 'any' in self._states_edges[state]:
                state = self._states_edges[state]['any']
                s = s[1:]
            # rejecting state - no edge could match s[0]
            else:
                return False
        return state in self._end_states

    @staticmethod
    def _nfa_reachable_noneps_edges(state):
        return filter(lambda e: e[0], functools.reduce(lambda x,y: x+y,[s._edges for s in NFA._moveEpsilon({state})]))

    @staticmethod
    def _nfa_char2statenum_set(st):
        char2statenum_set = collections.defaultdict(lambda: set())
        # gather all non-epsilon edges reachable from `st`
        # for each char in edges find all states reachable using that char
        for e in DFA._nfa_reachable_noneps_edges(st):
            char2statenum_set[e[0]] |= {e[1]._state_num} | set(map(lambda x: x._state_num, NFA._moveEpsilon({e[1]})))
        # if `any` edge reachable, than all other chars can use it too
        if 'any' in char2statenum_set:
            for char in char2statenum_set:
                char2statenum_set[char] |= char2statenum_set['any']
        return char2statenum_set

    @staticmethod
    def _multistate_name(states):
        return functools.reduce(lambda acc, x: acc + ',' + x, sorted(map(str,states)))

    @staticmethod
    def _merge_states(merged_states,nfa_states_edges):
        name = DFA._multistate_name(merged_states)
        char2statenum_set = collections.defaultdict(lambda: set())
        for st in merged_states:
            merged_c2s = nfa_states_edges[st]
            for c in merged_c2s:
                char2statenum_set[c] |= merged_c2s[c]
            if 'any' in char2statenum_set:
                for char in char2statenum_set:
                    char2statenum_set[char] |= char2statenum_set['any']
        return name, char2statenum_set

    def _view_graph(self):
        g = graphviz.Digraph(self.description, format='png', filename='graphs/DFA_'+str(id(self)))
        g.attr('node', shape='square')
        g.node(self._start)
        g.attr('node', shape='doublecircle')
        for st in self._end_states:
            g.node(st)
        g.attr('node', shape='circle')
        for st in self._states_edges:
            g.node(st)
            for char in self._states_edges[st]:
                g.edge(st, self._states_edges[st][char], label=char)
        g.body.append(r'label = "\n\n{}"'.format(self.description))
        g.body.append('fontsize=20')
        g.view()

