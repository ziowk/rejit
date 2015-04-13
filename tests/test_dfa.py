#encoding: utf8

import pytest

import rejit.nfa
from rejit.nfa import NFA
from rejit.dfa import DFA
from tests.helper import accept_test_helper

import tests.automaton_test_cases as auto_cases

class TestDFA:
    def test_empty_DFA(self):
        accept_test_helper(DFA(auto_cases.empty_nfa), auto_cases.empty_cases)

    def test_symbol_DFA(self):
        for nfa,cases in zip(auto_cases.symbol_nfas, auto_cases.symbol_cases):
            accept_test_helper(DFA(nfa), cases)

    def test_any_DFA(self):
        accept_test_helper(DFA(auto_cases.any_nfa),auto_cases.any_cases)

    def test_none_DFA(self):
        accept_test_helper(DFA(auto_cases.none_nfa),auto_cases.none_cases)

    def test_kleene_DFA(self):
        accept_test_helper(DFA(auto_cases.kleene_nfa),auto_cases.kleene_cases)

    def test_kleene_plus_DFA(self):
        accept_test_helper(DFA(auto_cases.kleene_plus_nfa),auto_cases.kleene_plus_cases)

    def test_concat_DFA(self):
        accept_test_helper(DFA(auto_cases.concat_nfa_1),auto_cases.concat_cases_1)
        accept_test_helper(DFA(auto_cases.concat_nfa_2),auto_cases.concat_cases_2)

    def test_concat_many_DFA(self):
        accept_test_helper(DFA(auto_cases.concat_many_nfa_1),auto_cases.concat_many_cases_1)
        accept_test_helper(DFA(auto_cases.concat_many_nfa_2),auto_cases.concat_many_cases_2)
        accept_test_helper(DFA(auto_cases.concat_many_nfa_3),auto_cases.concat_many_cases_3)

    def test_union_DFA(self):
        accept_test_helper(DFA(auto_cases.union_nfa),auto_cases.union_cases)

    def test_union_many_DFA(self):
        accept_test_helper(DFA(auto_cases.union_many_nfa_1),auto_cases.union_many_cases_1)
        accept_test_helper(DFA(auto_cases.union_many_nfa_2),auto_cases.union_many_cases_2)
        accept_test_helper(DFA(auto_cases.union_many_nfa_3),auto_cases.union_many_cases_3)

    def test_char_set_DFA(self):
        accept_test_helper(DFA(auto_cases.char_set_nfa_1),auto_cases.char_set_cases_1)
        accept_test_helper(DFA(auto_cases.char_set_nfa_2),auto_cases.char_set_cases_2)

    def test_zero_or_one_DFA(self):
        accept_test_helper(DFA(auto_cases.zero_or_one_nfa),auto_cases.zero_or_one_cases)

    def test_complex_DFA(self):
        accept_test_helper(DFA(auto_cases.complex_nfa_1),auto_cases.complex_cases_1)
        accept_test_helper(DFA(auto_cases.complex_nfa_2),auto_cases.complex_cases_2)

    def test_validation(self):
        nfa = NFA.symbol('a')
        nfak = NFA.kleene(nfa)
        assert not nfa.valid
        assert nfak.valid
        with pytest.raises(rejit.nfa.NFAInvalidError):
            DFA(nfa)
        dfa = DFA(nfak)
        assert nfak.accept('aaa') == True
        assert nfak.accept('aab') == False
        assert dfa.accept('aaa') == True
        assert dfa.accept('aab') == False

