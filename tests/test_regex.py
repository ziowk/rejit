#encoding: utf8

import pytest
import copy
import rejit.regex
import pprint
from rejit.regex import State
from rejit.regex import NFA
from rejit.regex import Regex

def accept_test_helper(regex,cases):
    for s,expected in cases:
        result = regex.accept(s) 
        print("regex:{regex}, string:{s}, result:{result}, expected:{expected}, {ok}".format(
            regex=regex.description,
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

    def test_symbol_NFA(self):
        char_list = rejit.regex.supported_chars + rejit.regex.special_chars
        for char in char_list:
            nfa = NFA.symbol(char)
            cases = zip(char_list,map(lambda c: c == char,char_list)) 
            accept_test_helper(nfa,cases)

    def test_any_NFA(self):
        all_chars = rejit.regex.supported_chars + rejit.regex.special_chars
        nfa = NFA.any()
        cases = zip(all_chars,[True]*len(all_chars))
        accept_test_helper(nfa,cases)

    def test_none_NFA(self):
        all_chars = rejit.regex.supported_chars + rejit.regex.special_chars
        nfa = NFA.none()
        cases = zip(all_chars,[False]*len(all_chars))
        accept_test_helper(nfa,cases)
        cases = [('',False)]
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

        # equivalent to 'a.b'
        nfa = NFA.concat(
                NFA.concat(NFA.symbol('a'),NFA.any()),
                NFA.symbol('b')
                )
        cases = [
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
        accept_test_helper(nfa,cases)

    def test_validation(self):
        nfa = NFA.symbol('a')
        nfak = NFA.kleene(nfa)
        assert not nfa.valid
        assert nfak.valid
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfa.accept('a')
        assert nfak.accept('aaa') == True
        assert nfak.accept('aab') == False

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfac = NFA.concat(nfa,nfab)
        assert not nfa.valid
        assert not nfab.valid
        assert nfac.valid
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfa.accept('a')
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfab.accept('b')
        assert nfac.accept('ab') == True
        assert nfac.accept('a') == False

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfau = NFA.union(nfa,nfab)
        assert not nfa.valid
        assert not nfab.valid
        assert nfau.valid
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfa.accept('a')
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfab.accept('b')
        assert nfau.accept('a') == True
        assert nfau.accept('b') == True
        assert nfau.accept('ab') == False

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfau = NFA.union(nfa,nfab)
        assert nfab.accept('b') == True
        assert nfab.accept('c') == False
        assert nfak.accept('aaa') == True
        assert nfak.accept('aax') == False

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfab)
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfau = NFA.union(nfa,nfab)
        assert nfa.accept('a') == True
        assert nfa.accept('c') == False
        assert nfak.accept('bbb') == True
        assert nfak.accept('bbx') == False

        nfa = NFA.symbol('a')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfakk = NFA.kleene(nfa)

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfa)
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfac = NFA.concat(nfa,nfab)
        assert nfab.accept('b') == True
        assert nfab.accept('c') == False
        assert nfak.accept('aaa') == True
        assert nfak.accept('aax') == False

        nfa = NFA.symbol('a')
        nfab = NFA.symbol('b')
        nfak = NFA.kleene(nfab)
        with pytest.raises(rejit.regex.NFAInvalidError):
            nfac = NFA.concat(nfa,nfab)
        assert nfa.accept('a') == True
        assert nfa.accept('c') == False
        assert nfak.accept('bbb') == True
        assert nfak.accept('bbx') == False

        nfa = NFA.symbol('a')
        with pytest.raises(rejit.regex.NFAArgumentError):
            nfaa = NFA.concat(nfa,nfa)
        with pytest.raises(rejit.regex.NFAArgumentError):
            nfaa = NFA.union(nfa,nfa)

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

def assert_regex_parse_error(pattern):
    with pytest.raises(rejit.regex.RegexParseError):
        re = Regex(pattern)
        print('Did not raise RegexParseError')
        print('ast: {}'.format(re._ast))
        print('description: {}'.format(re.get_NFA_description()))

ppast = pprint.PrettyPrinter(indent=4)

def assert_regex_description(ast, expected_description):
    result_description = Regex()._compile(ast).description
    print("ast:")
    ppast.pprint(ast)
    print("description:{description}, expected:{expected}, {ok}".format(
        description=result_description,
        expected=expected_description,
        ok='OK' if result_description == expected_description else 'FAILED'))
    assert result_description == expected_description

def assert_regex_AST(pattern, expected_ast):
    result_ast = Regex()._parse(pattern)
    print("pattern:",pattern)
    print("result ast:")
    ppast.pprint(result_ast)
    print("expected ast:")
    ppast.pprint(expected_ast)
    print('OK' if result_ast == expected_ast else 'FAILED')
    assert result_ast == expected_ast

def assert_regex_transform(ast, expected_trans_ast):
    trans_ast = Regex()._transform(ast)
    print("input ast:")
    ppast.pprint(ast)
    print("transformed ast:")
    ppast.pprint(trans_ast)
    print("expected ast:")
    ppast.pprint(expected_trans_ast)
    print('OK' if trans_ast == expected_trans_ast else 'FAILED')
    assert trans_ast == expected_trans_ast 

class TestRegexParsing:
    def test_empty_regex(self):
        pattern = ''
        expected_AST = ('empty',)
        expected_final_AST = expected_AST
        expected_NFA_description = '\\E'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_symbol_regex(self):
        for char in rejit.regex.supported_chars:
            pattern = char
            expected_AST = ('symbol',char)
            expected_final_AST = expected_AST
            expected_NFA_description = char
            assert_regex_AST(pattern,expected_AST)
            assert_regex_transform(expected_AST,expected_final_AST)
            assert_regex_description(expected_final_AST,expected_NFA_description)
        for char in rejit.regex.special_chars:
            pattern = "\\" + char
            expected_AST = ('symbol',char)
            expected_final_AST = expected_AST
            expected_NFA_description = "\\" + char
            assert_regex_AST(pattern,expected_AST)
            assert_regex_transform(expected_AST,expected_final_AST)
            assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_union_regex(self):
        pattern = 'a|b'
        expected_AST = ('union',('symbol','a'),('symbol','b'))
        expected_final_AST = expected_AST
        expected_NFA_description = '(a|b)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        # test for bug #35
        pattern = 'a|b|c'
        expected_AST = ('union',('symbol','a'),('union',('symbol','b'),('symbol','c')))
        expected_final_AST = expected_AST
        expected_NFA_description = '(a|(b|c))'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_kleene_star_regex(self):
        pattern = 'a*'
        expected_AST = ('kleene-star',('symbol','a'))
        expected_final_AST = expected_AST
        expected_NFA_description = '(a)*'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_concat_regex(self):
        pattern = 'abcdef'
        expected_AST = ('concat',[('symbol','a'),
                ('concat',[('symbol','b'),
                    ('concat',[('symbol','c'),
                        ('concat',[('symbol','d'),
                            ('concat',[('symbol','e'),('symbol','f')])
                            ])
                        ])
                    ])
                ])
        expected_final_AST = ('concat', [('symbol','a'), ('symbol','b'), ('symbol','c'), ('symbol','d'), ('symbol','e'),('symbol','f') ])
        expected_NFA_description = 'abcdef'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_complex_regex(self):
        pattern = 'aa(bb|(cc)*)'
        expected_AST = ('concat',[('symbol','a'),
                    ('concat',[('symbol','a'),
                        ('union',('concat',[('symbol','b'),('symbol','b')]),
                            ('kleene-star',('concat',[('symbol','c'),('symbol','c')]))
                            )
                        ])
                    ])
        expected_final_AST = ('concat', [
                                    ('symbol','a'),('symbol','a'),
                                    ('union',('concat',[('symbol','b'),('symbol','b')]),
                                        ('kleene-star',('concat',[('symbol','c'),('symbol','c')])))
                                    ])
        expected_NFA_description =  'aa(bb|(cc)*)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)
        
        pattern = 'aa.*bb.?(a|b)?'
        expected_AST = ('concat',[('symbol','a'),
                    ('concat',[('symbol','a'),
                        ('concat',[('kleene-star',('any',)),
                            ('concat',[('symbol','b'),
                                ('concat',[('symbol','b'),
                                    ('concat',[('zero-or-one',('any',)),
                                        ('zero-or-one',('union',('symbol','a'),('symbol','b'))
                                            )
                                        ])
                                    ])
                                ])
                            ])
                        ])
                    ])
        expected_final_AST = ('concat', [
                    ('symbol','a'),
                    ('symbol','a'),
                    ('kleene-star',('any',)),
                    ('symbol','b'),
                    ('symbol','b'),
                    ('zero-or-one',('any',)),
                    ('zero-or-one',('union',('symbol','a'),('symbol','b'))),
            ])
        expected_NFA_description = 'aa(.)*bb(.|\\E)((a|b)|\\E)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = 'aa[x-z]*bb[0-0]+cc[]?'
        expected_AST = ('concat',[('symbol','a'),
                    ('concat',[('symbol','a'),
                        ('concat',[('kleene-star',('set',['x','y','z'])),
                            ('concat',[('symbol','b'),
                                ('concat',[('symbol','b'),
                                    ('concat',[('kleene-plus',('set',['0'])),
                                        ('concat',[('symbol','c'),
                                            ('concat',[('symbol','c'),
                                                ('zero-or-one',('set',[]))
                                                ])
                                            ])
                                        ])
                                    ])
                                ])
                            ])
                        ])
                    ])
        expected_final_AST = ('concat', [
                    ('symbol','a'),
                    ('symbol','a'),
                    ('kleene-star',('set',['x','y','z'])),
                    ('symbol','b'),
                    ('symbol','b'),
                    ('kleene-plus',('set',['0'])),
                    ('symbol','c'),
                    ('symbol','c'),
                    ('zero-or-one',('set',[])),
            ])
        expected_NFA_description = 'aa(((x|y)|z))*bb0(0)*cc([]|\\E)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_one_or_zero_mult_regex(self):
        pattern = 'a?'
        expected_AST = ('zero-or-one',('symbol','a'))
        expected_final_AST = expected_AST
        expected_NFA_description = r'(a|\E)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_charset_regex(self):
        pattern = '[abc]'
        expected_AST = ('set',['a','b','c'])
        expected_final_AST = expected_AST
        expected_NFA_description = '((a|b)|c)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[Xa-cY0-2Z]'
        expected_AST = ('set',['X','a','b','c','Y','0','1','2','Z'])
        expected_final_AST = expected_AST
        expected_NFA_description = '((((((((X|a)|b)|c)|Y)|0)|1)|2)|Z)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[aa-bb]'
        expected_AST = ('set',['a','a','b','b'])
        expected_final_AST = expected_AST
        expected_NFA_description = '(((a|a)|b)|b)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[c-c]'
        expected_AST = ('set',['c'])
        expected_final_AST = expected_AST
        expected_NFA_description = 'c'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[cc]'
        expected_AST = ('set',['c','c'])
        expected_final_AST = expected_AST
        expected_NFA_description = '(c|c)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[z-a]'
        expected_AST = ('set',[])
        expected_final_AST = expected_AST
        expected_NFA_description = '[]'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[*+.<-?]'
        expected_AST = ('set',['*','+','.','<','=','>','?'])
        expected_final_AST = expected_AST
        expected_NFA_description = r'((((((\*|\+)|\.)|<)|=)|>)|\?)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[[-]]'
        expected_AST = ('set',['[','\\',']'])
        expected_final_AST = expected_AST
        expected_NFA_description = r'((\[|\\)|\])'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[---]'
        expected_AST = ('set',['-'])
        expected_final_AST = expected_AST
        expected_NFA_description = r'\-'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        assert_regex_parse_error('[a-]')
        assert_regex_parse_error('[a-')
        assert_regex_parse_error('[abc')

    def test_negative_charset_regex(self):
        assert_regex_parse_error('[^abc]')

    def test_period_wildcard_regex(self):
        pattern = '.'
        expected_AST = ('any',)
        expected_final_AST = expected_AST
        expected_NFA_description = '.'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_kleene_plus_regex(self):
        pattern = 'a+'
        expected_AST = ('kleene-plus',('symbol','a'))
        expected_final_AST = expected_AST
        expected_NFA_description = 'a(a)*'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_grouping_regex(self):
        pattern = '(aa|bb)cc'
        expected_AST = ('concat',[
                ('union',
                    ('concat',[('symbol','a'),('symbol','a')]),
                    ('concat',[('symbol','b'),('symbol','b')])),
                ('concat',[('symbol','c'),('symbol','c')])]
            )
        expected_final_AST = ('concat',[
                ('union',
                    ('concat',[('symbol','a'),('symbol','a')]),
                    ('concat',[('symbol','b'),('symbol','b')])),
                ('symbol','c'),
                ('symbol','c'),
                ])
        expected_NFA_description = '(aa|bb)cc'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_invalid_use_of_special_char_regex(self):
        for char in rejit.regex.special_chars.replace('.',''):
            assert_regex_parse_error(char)

        # test for bug #36
        assert_regex_parse_error('a|b|')

        assert_regex_parse_error('abc\\')

        assert_regex_parse_error('a*?')
        assert_regex_parse_error('a**')
        assert_regex_parse_error('a*+')
        assert_regex_parse_error('(*a)')
        assert_regex_parse_error('(+a)')
        assert_regex_parse_error('(?a)')
        assert_regex_parse_error('a|*b')
        assert_regex_parse_error('a|+b')
        assert_regex_parse_error('a|?b')

        assert_regex_parse_error('|abc')
        assert_regex_parse_error('abc|')
        assert_regex_parse_error('a||b')
        assert_regex_parse_error('(|abc)')
        assert_regex_parse_error('(a||b)')
        assert_regex_parse_error('(abc|)')

        # test for bug #39
        assert_regex_parse_error('a)')
        assert_regex_parse_error('a)aaa')
        assert_regex_parse_error('a)*?+[\\')
        assert_regex_parse_error('(a))')
        assert_regex_parse_error('(a)a)')
        assert_regex_parse_error('(a)a)a')

        assert_regex_parse_error('(a')
        assert_regex_parse_error('aaa(a')
        assert_regex_parse_error('((((')
        assert_regex_parse_error('((((aaaa')
        assert_regex_parse_error('a(a(a)a')
        assert_regex_parse_error('(abc|cde')

    def test_empty_set_regex(self):
        pattern = '[]'
        expected_AST = ('set',[])
        expected_final_AST = expected_AST
        expected_NFA_description = '[]'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_empty_group_regex(self):
        assert_regex_parse_error('()')

    def test_concat_compile(self):
        re = Regex()

        concat2 = ('concat', [('symbol','a'),('symbol','b')])
        nfa2 = re._compile(concat2)
        assert nfa2.description == 'ab'
        assert nfa2.accept('ab')
        assert not nfa2.accept('')
        assert not nfa2.accept('a')
        assert not nfa2.accept('ba')
        assert not nfa2.accept('abc')

        concat5 = ('concat', [('symbol','a'),('symbol','b'),('symbol','c'),('symbol','d'),('symbol','e')])
        nfa5 = re._compile(concat5)
        assert nfa5.description == 'abcde'
        assert nfa5.accept('abcde')
        assert not nfa5.accept('')
        assert not nfa5.accept('a')
        assert not nfa5.accept('ab')
        assert not nfa5.accept('bacde')
        assert not nfa5.accept('abcdef')

    def test_ast_concat_transform(self):
        re = Regex()
        x = re._parse('a')
        xinline = re._flatten_concat(x) 
        assert xinline == ('symbol','a')

        x = re._parse('ab')
        xinline = re._flatten_concat(x) 
        assert xinline == ('concat',[('symbol','a'),('symbol','b')])

        x = re._parse('abc')
        xinline = re._flatten_concat(x) 
        assert xinline == ('concat',[('symbol','a'),('symbol','b'),('symbol','c')])

        x = re._parse('a*b+c?')
        xinline = re._flatten_concat(x) 
        assert xinline == ('concat',[
            ('kleene-star',('symbol','a')),
            ('kleene-plus',('symbol','b')),
            ('zero-or-one',('symbol','c'))
            ])

        x = re._parse('a(bbb)+d')
        xinline = re._flatten_concat(x) 
        assert xinline == ('concat',[('symbol','a'),('kleene-plus',('concat',[('symbol','b'),('symbol','b'),('symbol','b')])),('symbol','d')])

        # really abstract syntax tree
        x = ('concat', [
                ('concat', [
                    ('symbol','a'),
                    ('concat',[ ('symbol','b'),('symbol','c')])
                    ]),
                ('concat', [
                    ('concat',[('symbol','d'),('symbol','e')]),
                    ('symbol','f')])
                ])
        xinline = re._flatten_concat(x)
        ppast.pprint(x)
        ppast.pprint(xinline)
        assert xinline == ('concat', [ ('symbol','a'), ('symbol','b'), ('symbol','c'), ('symbol','d'), ('symbol','e'), ('symbol','f') ])

