#encoding: utf8

import pytest

import rejit.nfa
from rejit.nfa import NFA
from rejit.dfa import DFA

class TestDFA:
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

