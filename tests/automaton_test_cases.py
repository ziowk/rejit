#encoding: utf8

import rejit.common
from rejit.nfa import NFA

empty_nfa = NFA.empty()
empty_cases = [
                ('',True),
                ('a',False),
              ]

all_chars = rejit.common.supported_chars + rejit.common.special_chars

symbol_nfas = [NFA.symbol(char) for char in all_chars]
symbol_cases = [list(zip(all_chars,map(lambda c: c == char,all_chars))) for char in all_chars]

any_nfa = NFA.any()
any_cases = list(zip(all_chars,[True]*len(all_chars)))

none_nfa = NFA.none()
none_cases = list(zip(all_chars,[False]*len(all_chars))) + [('',False)]

kleene_nfa = NFA.kleene(NFA.symbol('a'))
kleene_cases = [
                    ('',True),
                    ('a',True),
                    ('aa',True),
                    ('aaaaaaa',True),
                    ('b',False),
                    ('aaaaaab',False),
                    ('baaaaaa',False),
                    ('aaabaaa',False),
                ]

kleene_plus_nfa = NFA.kleene_plus(NFA.symbol('a'))
kleene_plus_cases = [
            ('a',True),
            ('aa',True),
            ('aaaaaaa',True),
            ('',False),
            ('b',False),
            ('aaaaaab',False),
            ('baaaaaa',False),
            ('aaabaaa',False),
        ]

concat_nfa_1 = NFA.concat(NFA.symbol('a'),NFA.symbol('b'))
concat_cases_1 = [
            ('ab',True),
            ('',False),
            ('a',False),
            ('b',False),
            ('abb',False),
            ('aab',False),
        ]

concat_nfa_2 = NFA.concat(NFA.concat(NFA.symbol('a'),NFA.symbol('b')),NFA.symbol('c'))
concat_cases_2 = [
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

concat_many_nfa_1 = NFA.concat_many([NFA.symbol('a'), NFA.symbol('b'), NFA.kleene_plus(NFA.symbol('c')), NFA.symbol('d')])
concat_many_cases_1 = [
            ('abcd',True),
            ('abcccccd',True),
            ('',False),
            ('x',False),
            ('ab',False),
            ('abd',False),
            ('abdccccc',False),
        ]

concat_many_nfa_2 = NFA.concat_many([NFA.symbol('a')])
concat_many_cases_2 = [
            ('a',True),
            ('',False),
            ('b',False),
            ('aa',False),
        ]

concat_many_nfa_3 = NFA.concat_many([])
concat_many_cases_3 = [
            ('',True),
            ('a',False),
        ]

union_nfa = NFA.union(NFA.symbol('a'),NFA.symbol('b'))
union_cases = [
            ('a',True),
            ('b',True),
            ('',False),
            ('ab',False),
            ('aa',False),
            ('bb',False),
        ]

union_many_nfa_1 = NFA.union_many([NFA.symbol('a'),NFA.symbol('b'),NFA.kleene_plus(NFA.symbol('c'))])
union_many_cases_1 = [
            ('a',True),
            ('b',True),
            ('c',True),
            ('ccc',True),
            ('',False),
            ('x',False),
            ('ab',False),
            ('aaa',False),
            ('bbb',False),
            ('abccc',False),
        ]

union_many_nfa_2 = NFA.union_many([NFA.symbol('a')])
union_many_cases_2 = [
            ('a',True),
            ('',False),
            ('b',False),
            ('aa',False),
        ]

union_many_nfa_3 = NFA.union_many([])
union_many_cases_3 = [
            ('',False),
            ('a',False),
        ]

char_set_nfa_1 = NFA.char_set(['a', 'b', 'c'], '[abc]')
char_set_cases_1 = [
            ('a',True),
            ('b',True),
            ('c',True),
            ('',False),
            ('x',False),
            ('aaa',False),
            ('abc',False),
        ]

char_set_nfa_2 = NFA.char_set([], '[]')
char_set_cases_2 = [
            ('',False),
            ('a',False),
        ]

zero_or_one_nfa = NFA.zero_or_one(NFA.symbol('a'))
zero_or_one_cases = [
            ('',True),
            ('a',True),
            ('b',False),
            ('aaa',False),
        ]

# equivalent to 'aa(bb|(cc)*)
complex_nfa_1 = NFA.concat(
        NFA.concat(NFA.symbol('a'),NFA.symbol('a')),
        NFA.union(
            NFA.concat(NFA.symbol('b'),NFA.symbol('b')),
            NFA.kleene(
                NFA.concat(NFA.symbol('c'),NFA.symbol('c'))
                )
            )
        )
complex_cases_1 = [
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

# equivalent to 'a.b'
complex_nfa_2 = NFA.concat(
        NFA.concat(NFA.symbol('a'),NFA.any()),
        NFA.symbol('b')
        )
complex_cases_2 = [
            ('axb',True),
            ('aab',True),
            ('abb',True),
            ('a+b',True),
            ('a1b',True),
            ('',False),
            ('ab',False),
            ('axxb',False),
            ('axc',False),
            ('cxb',False),
        ]

