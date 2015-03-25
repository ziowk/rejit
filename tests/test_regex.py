#encoding: utf8

import pytest
import rejit.regex
from rejit.regex import NFA

@pytest.fixture(scope='module')
def symbol_list():
    return rejit.regex.supported_chars

def accept_test_helper(regex,cases):
    for s,expected in cases:
        result = regex.accept(s) 
        print("regex:{regex}, string:{s}, result:{result}, expected:{expected}, {ok}".format(
            regex=regex,
            s=s,
            result=result,
            expected=expected,
            ok='OK' if result == expected else 'FAILED'))
        assert result == expected

class TestNFA:
    def test_empty_NFA(self):
        nfa = NFA.empty()
        cases = [
                    ('',True),
                    ('a',False),
                ]
        accept_test_helper(nfa,cases)

    def test_symbol_NFA(self, symbol_list):
        for char in symbol_list:
            nfa = NFA.symbol(char)
            cases = zip(symbol_list,map(lambda c: c == char,symbol_list)) 
            accept_test_helper(nfa,cases)

    def test_kleene_NFA(self):
        nfa = NFA.kleene(NFA.symbol('a'))
        cases = [
                    ('',True),
                    ('a',True),
                    ('aa',True),
                    ('aaaaaaa',True),
                    ('b',False),
                    ('aaaaaab',False),
                    ('baaaaaa',False),
                    ('aaabaaa',False),
                ]
        accept_test_helper(nfa,cases)

    def test_concat_NFA(self):
        nfa = NFA.concat(NFA.symbol('a'),NFA.symbol('b'))
        cases = [
                    ('ab',True),
                    ('',False),
                    ('a',False),
                    ('b',False),
                    ('abb',False),
                    ('aab',False),
                ]
        accept_test_helper(nfa,cases)

        nfa = NFA.concat(NFA.concat(NFA.symbol('a'),NFA.symbol('b')),NFA.symbol('c'))
        cases = [
                    ('abc',True),
                    ('',False),
                    ('a',False),
                    ('b',False),
                    ('c',False),
                    ('ab',False),
                    ('ac',False),
                    ('bc',False),
                    ('abcx',False),
                ]
        accept_test_helper(nfa,cases)

    def test_union_NFA(self):
        nfa = NFA.union(NFA.symbol('a'),NFA.symbol('b'))
        cases = [
                    ('a',True),
                    ('b',True),
                    ('',False),
                    ('ab',False),
                    ('aa',False),
                    ('bb',False),
                ]
        accept_test_helper(nfa,cases)

    def test_complex_NFA(self):
        # equivalent to 'aa(bb|(cc)*)
        nfa = NFA.concat(
                NFA.concat(NFA.symbol('a'),NFA.symbol('a')),
                NFA.union(
                    NFA.concat(NFA.symbol('b'),NFA.symbol('b')),
                    NFA.kleene(
                        NFA.concat(NFA.symbol('c'),NFA.symbol('c'))
                        )
                    )
                )
        cases = [
                    ('aa',True),
                    ('aabb',True),
                    ('aacc',True),
                    ('aacccccc',True),
                    ('',False),
                    ('aac',False),
                    ('aaccc',False),
                    ('aabbc',False),
                    ('aabbcc',False),
                    ('aabbcccccc',False),
                    ('bbcc',False),
                    ('cc',False),
                ]
        accept_test_helper(nfa,cases)

