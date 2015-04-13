#encoding: utf8

import copy
import pytest

import rejit.nfa
from rejit.nfa import NFA
from rejit.nfa import State
from tests.helper import accept_test_helper

import tests.automaton_test_cases as auto_cases

class TestNFAaccept:
    def test_empty_NFA(self):
        accept_test_helper(auto_cases.empty_nfa, auto_cases.empty_cases)

    def test_symbol_NFA(self):
        for nfa,cases in zip(auto_cases.symbol_nfas, auto_cases.symbol_cases):
            accept_test_helper(nfa, cases)

    def test_any_NFA(self):
        accept_test_helper(auto_cases.any_nfa,auto_cases.any_cases)

    def test_none_NFA(self):
        accept_test_helper(auto_cases.none_nfa,auto_cases.none_cases)

    def test_kleene_NFA(self):
        accept_test_helper(auto_cases.kleene_nfa,auto_cases.kleene_cases)

    def test_kleene_plus_NFA(self):
        accept_test_helper(auto_cases.kleene_plus_nfa,auto_cases.kleene_plus_cases)

    def test_concat_NFA(self):
        accept_test_helper(auto_cases.concat_nfa_1,auto_cases.concat_cases_1)
        accept_test_helper(auto_cases.concat_nfa_2,auto_cases.concat_cases_2)

    def test_concat_many_NFA(self):
        accept_test_helper(auto_cases.concat_many_nfa_1,auto_cases.concat_many_cases_1)
        accept_test_helper(auto_cases.concat_many_nfa_2,auto_cases.concat_many_cases_2)
        accept_test_helper(auto_cases.concat_many_nfa_3,auto_cases.concat_many_cases_3)

    def test_union_NFA(self):
        accept_test_helper(auto_cases.union_nfa,auto_cases.union_cases)

    def test_union_many_NFA(self):
        accept_test_helper(auto_cases.union_many_nfa_1,auto_cases.union_many_cases_1)
        accept_test_helper(auto_cases.union_many_nfa_2,auto_cases.union_many_cases_2)
        accept_test_helper(auto_cases.union_many_nfa_3,auto_cases.union_many_cases_3)

    def test_char_set_NFA(self):
        accept_test_helper(auto_cases.char_set_nfa_1,auto_cases.char_set_cases_1)
        accept_test_helper(auto_cases.char_set_nfa_2,auto_cases.char_set_cases_2)

    def test_zero_or_one_NFA(self):
        accept_test_helper(auto_cases.zero_or_one_nfa,auto_cases.zero_or_one_cases)

    def test_complex_NFA(self):
        accept_test_helper(auto_cases.complex_nfa_1,auto_cases.complex_cases_1)
        accept_test_helper(auto_cases.complex_nfa_2,auto_cases.complex_cases_2)

class TestNFAvalidation:
    def test_accept_validation(self):
        nfa = NFA.char_set(['a','b'], '[ab]')
        nfa._invalidate()
        assert not nfa.valid
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfa.accept('a')

    def test_concat_invalidation(self):
        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfac = NFA.concat(nfa,nfab)
        assert not nfa.valid
        assert not nfab.valid
        assert nfac.valid
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfa.accept('a')
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfab.accept('b')
        assert nfac.accept('ab') == True
        assert nfac.accept('a') == False

    def test_union_invalidation(self):
        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfau = NFA.union(nfa,nfab)
        assert not nfa.valid
        assert not nfab.valid
        assert nfau.valid
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfa.accept('a')
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfab.accept('b')
        assert nfau.accept('a') == True
        assert nfau.accept('b') == True
        assert nfau.accept('ab') == False

    def test_kleene_invalidation(self):
        nfa = NFA.symbol('a')
        nfak = NFA.kleene(nfa)
        assert not nfa.valid
        assert nfak.valid
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfa.accept('a')
        assert nfak.accept('aaa') == True
        assert nfak.accept('aab') == False

    def test_kleene_plus_invalidation(self):
        nfa = NFA.symbol('a')
        nfap = NFA.kleene_plus(nfa)
        assert not nfa.valid
        assert nfap.valid
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfa.accept('a')
        assert nfap.accept('a') == True
        assert nfap.accept('aaa') == True
        assert nfap.accept('') == False
        assert nfap.accept('b') == False
        assert nfap.accept('aab') == False

    def test_zero_or_one_invalidation(self):
        nfa = NFA.symbol('a')
        nfaz = NFA.zero_or_one(nfa)
        assert not nfa.valid
        assert nfaz.valid
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfa.accept('a')
        assert nfaz.accept('') == True
        assert nfaz.accept('a') == True
        assert nfaz.accept('b') == False
        assert nfaz.accept('aaa') == False

    def test_concat_many_invalidation(self):
        nfa_list = [NFA.symbol('a'), NFA.symbol('b'), NFA.symbol('c')]
        nfacm = NFA.concat_many(nfa_list)
        for nfa in nfa_list:
            assert not nfa.valid
            with pytest.raises(rejit.nfa.NFAInvalidError):
                nfa.accept('a')
        assert nfacm.valid
        assert nfacm.accept('abc') == True
        assert nfacm.accept('') == False
        assert nfacm.accept('abcd') == False

    def test_union_many_invalidation(self):
        nfa_list = [NFA.symbol('a'), NFA.symbol('b'), NFA.symbol('c')]
        nfaum = NFA.union_many(nfa_list)
        for nfa in nfa_list:
            assert not nfa.valid
            with pytest.raises(rejit.nfa.NFAInvalidError):
                nfa.accept('a')
        assert nfaum.valid
        assert nfaum.accept('a') == True
        assert nfaum.accept('b') == True
        assert nfaum.accept('c') == True
        assert nfaum.accept('') == False
        assert nfaum.accept('abc') == False

    def test_kleene_validation(self):
        nfa = NFA.symbol('a')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfakk = NFA.kleene(nfa)

    def test_union_validation(self):
        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfau = NFA.union(nfa,nfab)
        assert nfab.accept('b') == True
        assert nfab.accept('c') == False
        assert nfak.accept('aaa') == True
        assert nfak.accept('aax') == False

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfab)
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfau = NFA.union(nfa,nfab)
        assert nfa.accept('a') == True
        assert nfa.accept('c') == False
        assert nfak.accept('bbb') == True
        assert nfak.accept('bbx') == False

    def test_concat_validation(self):
        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfac = NFA.concat(nfa,nfab)
        assert nfab.accept('b') == True
        assert nfab.accept('c') == False
        assert nfak.accept('aaa') == True
        assert nfak.accept('aax') == False

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfab)
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfac = NFA.concat(nfa,nfab)
        assert nfa.accept('a') == True
        assert nfa.accept('c') == False
        assert nfak.accept('bbb') == True
        assert nfak.accept('bbx') == False

    def test_kleene_plus_validation(self):
        nfa = NFA.symbol('a')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfap = NFA.kleene_plus(nfa)
        assert nfak.accept('a') == True
        assert nfak.accept('aaa') == True
        assert nfak.accept('aak') == False

    def test_zero_or_one_validation(self):
        nfa = NFA.symbol('a')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfaz = NFA.zero_or_one(nfa)
        assert nfak.accept('a') == True
        assert nfak.accept('aaa') == True
        assert nfak.accept('aak') == False

    def test_concat_many_validation(self):
        nfa_list = [NFA.symbol('a'), NFA.symbol('a'), NFA.symbol('a')]
        nfak = NFA.kleene(nfa_list[-1])
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfacm = NFA.concat_many(nfa_list)
        assert nfak.accept('a') == True
        assert nfak.accept('aaa') == True
        assert nfak.accept('aak') == False
        assert nfa_list[0].accept('a') == True
        assert nfa_list[0].accept('b') == False
        assert nfa_list[1].accept('a') == True
        assert nfa_list[1].accept('b') == False

    def test_union_many_validation(self):
        nfa_list = [NFA.symbol('a'), NFA.symbol('a'), NFA.symbol('a')]
        nfak = NFA.kleene(nfa_list[-1])
        with pytest.raises(rejit.nfa.NFAInvalidError):
            nfaum = NFA.union_many(nfa_list)
        assert nfak.accept('a') == True
        assert nfak.accept('aaa') == True
        assert nfak.accept('aak') == False
        assert nfa_list[0].accept('a') == True
        assert nfa_list[0].accept('b') == False
        assert nfa_list[1].accept('a') == True
        assert nfa_list[1].accept('b') == False

    def test_concat_duplicates(self):
        nfa = NFA.symbol('a')
        with pytest.raises(rejit.nfa.NFAArgumentError):
            nfaa = NFA.concat(nfa,nfa)

    def test_union_duplicates(self):
        nfa = NFA.symbol('a')
        with pytest.raises(rejit.nfa.NFAArgumentError):
            nfaa = NFA.union(nfa,nfa)

    def test_union_many_duplicates(self):
        nfb = NFA.symbol('b')
        with pytest.raises(rejit.nfa.NFAArgumentError):
            nfaum = NFA.union_many([nfb,NFA.symbol('a'),nfb])

    def test_concat_many_duplicates(self):
        nfb = NFA.symbol('b')
        with pytest.raises(rejit.nfa.NFAArgumentError):
            nfacm = NFA.concat_many([nfb,NFA.symbol('a'),nfb])

class TestNFAother:
    def test_deepcopy(self):
        nfa = NFA.union(NFA.concat(NFA.symbol('a'),NFA.kleene(NFA.symbol('b'))),NFA.symbol('c'))
        nfc = copy.deepcopy(nfa)

        # test state deep copy
        st1 = State()
        st2 = State()
        st1.add('a',st2)
        st1c = copy.deepcopy(st1)
        assert st1 is not st1c
        assert st1._edges is not st1c._edges
        assert st1._state_num != st1c._state_num
        assert st2 is not st1c._edges[0][1]
        assert st2._edges is not st1c._edges[0][1]._edges
        assert st2._state_num != st1c._edges[0][1]._state_num

        # test if internals are different objects
        assert nfa is not nfc
        assert nfa._start is not nfc._start
        assert nfa._end is not nfc._end

        # get all states
        def get_all_states_helper(n):
            states = set()
            temp = {n._start}
            while temp:
                st = temp.pop()
                states.add(st)
                temp |= set(map(lambda e: e[1], filter(lambda e: e[1] not in states, st._edges)))
            return states

        # assert no shared states
        sta = get_all_states_helper(nfa)
        stc = get_all_states_helper(nfc)
        assert not set(map(id, sta)) & set(map(id, stc))

        # test if both still work as intended
        cases = [
                    ('a',True),
                    ('c',True),
                    ('ab',True),
                    ('abbbbb',True),
                    ('',False),
                    ('x',False),
                    ('ac',False),
                    ('bc',False),
                    ('ba',False),
                    ('b',False),
                    ('abbbbc',False),
                    ('accccc',False),
                    ('acbbbb',False),
                ]
        accept_test_helper(nfa, cases)
        accept_test_helper(nfc, cases)

