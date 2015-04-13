#encoding: utf8

import pytest
import pprint
import rejit.common
from rejit.nfa import NFA
from rejit.regex import Regex

from tests.helper import accept_test_helper

ppast = pprint.PrettyPrinter(indent=4)

def assert_regex_parse_error(pattern):
    with pytest.raises(rejit.regex.RegexParseError):
        re = Regex(pattern)
        print('Did not raise RegexParseError')
        print('ast: {}'.format(re._ast))
        print('description: {}'.format(re.get_matcher_description()))

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
        for char in rejit.common.supported_chars:
            pattern = char
            expected_AST = ('symbol',char)
            expected_final_AST = expected_AST
            expected_NFA_description = char
            assert_regex_AST(pattern,expected_AST)
            assert_regex_transform(expected_AST,expected_final_AST)
            assert_regex_description(expected_final_AST,expected_NFA_description)
        for char in rejit.common.special_chars:
            pattern = "\\" + char
            expected_AST = ('symbol',char)
            expected_final_AST = expected_AST
            expected_NFA_description = "\\" + char
            assert_regex_AST(pattern,expected_AST)
            assert_regex_transform(expected_AST,expected_final_AST)
            assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_union_regex(self):
        pattern = 'a|b'
        expected_AST = ('union',[('symbol','a'),('symbol','b')])
        expected_final_AST = expected_AST
        expected_NFA_description = '(a|b)'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        # test for bug #35
        pattern = 'a|b|c'
        expected_AST = ('union',[('symbol','a'),('union',[('symbol','b'),('symbol','c')])])
        expected_final_AST = ('union',[('symbol','a'),('symbol','b'),('symbol','c')])
        expected_NFA_description = '(a|b|c)'
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

        pattern = ('(a*)*')
        expected_AST = ('kleene-star',('kleene-star',('symbol','a')))
        expected_final_AST = expected_AST
        expected_NFA_description = '((a)*)*'
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
                        ('union',[('concat',[('symbol','b'),('symbol','b')]),
                            ('kleene-star',('concat',[('symbol','c'),('symbol','c')]))
                            ])
                        ])
                    ])
        expected_final_AST = ('concat', [
                                    ('symbol','a'),('symbol','a'),
                                    ('union',[('concat',[('symbol','b'),('symbol','b')]),
                                        ('kleene-star',('concat',[('symbol','c'),('symbol','c')]))])
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
                                        ('zero-or-one',('union',[('symbol','a'),('symbol','b')])
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
                    ('zero-or-one',('union',[('symbol','a'),('symbol','b')])),
            ])
        expected_NFA_description = 'aa(.)*bb(.)?((a|b))?'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = 'aa[x-z]*bb[0-0]+cc[]?'
        expected_AST = ('concat',[('symbol','a'),
                    ('concat',[('symbol','a'),
                        ('concat',[('kleene-star',('set',['x','y','z'],'[x-z]')),
                            ('concat',[('symbol','b'),
                                ('concat',[('symbol','b'),
                                    ('concat',[('kleene-plus',('set',['0'],'[0-0]')),
                                        ('concat',[('symbol','c'),
                                            ('concat',[('symbol','c'),
                                                ('zero-or-one',('set',[],'[]'))
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
                    ('kleene-star',('set',['x','y','z'],'[x-z]')),
                    ('symbol','b'),
                    ('symbol','b'),
                    ('kleene-plus',('set',['0'],'[0-0]')),
                    ('symbol','c'),
                    ('symbol','c'),
                    ('zero-or-one',('set',[],'[]')),
            ])
        expected_NFA_description = 'aa([x-z])*bb([0-0])+cc([])?'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_one_or_zero_mult_regex(self):
        pattern = 'a?'
        expected_AST = ('zero-or-one',('symbol','a'))
        expected_final_AST = expected_AST
        expected_NFA_description = r'(a)?'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_charset_regex(self):
        pattern = '[abc]'
        expected_AST = ('set',['a','b','c'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[Xa-cY0-2Z]'
        expected_AST = ('set',['X','a','b','c','Y','0','1','2','Z'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[aa-bb]'
        expected_AST = ('set',['a','a','b','b'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[c-c]'
        expected_AST = ('set',['c'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[cc]'
        expected_AST = ('set',['c','c'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[z-a]'
        expected_AST = ('set',[],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[*+.<-?]'
        expected_AST = ('set',['*','+','.','<','=','>','?'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[[-]]'
        expected_AST = ('set',['[','\\',']'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '[---]'
        expected_AST = ('set',['-'],pattern)
        expected_final_AST = expected_AST
        expected_NFA_description = pattern
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
        expected_NFA_description = '(a)+'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_grouping_regex(self):
        pattern = '(aa|bb)cc'
        expected_AST = ('concat',[
                ('union',[
                    ('concat',[('symbol','a'),('symbol','a')]),
                    ('concat',[('symbol','b'),('symbol','b')])]),
                ('concat',[('symbol','c'),('symbol','c')])]
            )
        expected_final_AST = ('concat',[
                ('union',[
                    ('concat',[('symbol','a'),('symbol','a')]),
                    ('concat',[('symbol','b'),('symbol','b')])]),
                ('symbol','c'),
                ('symbol','c'),
                ])
        expected_NFA_description = '(aa|bb)cc'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '(((a)))'
        expected_AST = ('symbol','a')
        expected_final_AST = expected_AST
        expected_NFA_description = 'a'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

        pattern = '(((a)((b))))'
        expected_AST = ('concat',[('symbol','a'),('symbol','b')])
        expected_final_AST = expected_AST
        expected_NFA_description = 'ab'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_invalid_use_of_special_char_regex(self):
        for char in rejit.common.special_chars.replace('.',''):
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
        expected_AST = ('set',[],'[]')
        expected_final_AST = expected_AST
        expected_NFA_description = '[]'
        assert_regex_AST(pattern,expected_AST)
        assert_regex_transform(expected_AST,expected_final_AST)
        assert_regex_description(expected_final_AST,expected_NFA_description)

    def test_empty_group_regex(self):
        assert_regex_parse_error('()')

    def test_ast_flatten_transform(self):
        re = Regex()
        x = re._parse('a')
        xinline = re._flatten_nodes('concat',x) 
        assert xinline == ('symbol','a')

        x = re._parse('ab')
        xinline = re._flatten_nodes('concat',x) 
        assert xinline == ('concat',[('symbol','a'),('symbol','b')])

        x = re._parse('abc')
        xinline = re._flatten_nodes('concat',x) 
        assert xinline == ('concat',[('symbol','a'),('symbol','b'),('symbol','c')])

        x = re._parse('a*b+c?')
        xinline = re._flatten_nodes('concat',x) 
        assert xinline == ('concat',[
            ('kleene-star',('symbol','a')),
            ('kleene-plus',('symbol','b')),
            ('zero-or-one',('symbol','c'))
            ])

        x = re._parse('a(bbb)+d')
        xinline = re._flatten_nodes('concat',x) 
        assert xinline == ('concat',[('symbol','a'),('kleene-plus',('concat',[('symbol','b'),('symbol','b'),('symbol','b')])),('symbol','d')])

        x = re._parse('a|b|c')
        xinline = re._flatten_nodes('union',x) 
        assert xinline == ('union', [('symbol','a'),('symbol','b'),('symbol','c')])

        x = re._parse('a|(b|c|d)|(ef|gh)')
        xinline = re._flatten_nodes('union',x) 
        assert xinline == ('union', [
            ('symbol','a'),
            ('symbol','b'),
            ('symbol','c'),
            ('symbol','d'),
            ('concat',[('symbol','e'),('symbol','f')]),
            ('concat',[('symbol','g'),('symbol','h')]),
            ])
        nfa1 = re._compile(x)
        nfa2 = re._compile(xinline)
        assert nfa1.description == '(a|((b|(c|d))|(ef|gh)))'
        assert nfa2.description == '(a|b|c|d|ef|gh)'

        x = re._parse('a|x(b|c|d)|(ef|gh)')
        xinline = re._flatten_nodes('union',x) 
        assert xinline == ('union', [
            ('symbol','a'),
            ('concat', [
                ('symbol', 'x'),
                ('union',[('symbol','b'),('symbol','c'),('symbol','d')]),
                ]),
            ('concat',[('symbol','e'),('symbol','f')]),
            ('concat',[('symbol','g'),('symbol','h')]),
            ])

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
        xinline = re._flatten_nodes('concat',x)
        ppast.pprint(x)
        ppast.pprint(xinline)
        assert xinline == ('concat', [ ('symbol','a'), ('symbol','b'), ('symbol','c'), ('symbol','d'), ('symbol','e'), ('symbol','f') ])

        # test for bug #44
        x = ('xxxxx', [('symbol', 'a'), ('empty',)])
        xinline = re._flatten_nodes('concat',x)
        ppast.pprint(x)
        ppast.pprint(xinline)
        assert xinline == x
        # test for bug #44
        x = ('xxxxx', [('yyy', [('xxxxx',[])]), ('symbol', 'b')])
        xinline = re._flatten_nodes('concat',x)
        ppast.pprint(x)
        ppast.pprint(xinline)
        assert xinline == x

    def test_empty_regex_checks(self):
        # test for but #63
        re = Regex()
        assert re.pattern is None
        with pytest.raises(rejit.regex.RegexMatcherError):
            re.accept('')
        with pytest.raises(rejit.regex.RegexMatcherError):
            re.get_matcher_description()

    def test_DFA_compilation(self):
        re = Regex('a|b*')
        cases = [
                    ('a', True),
                    ('a', True),
                    ('', True),
                    ('b', True),
                    ('bbb', True),
                    ('x', False),
                    ('aaa', False),
                    ('abb', False),
                ]
        accept_test_helper(re,cases)

        re.compile_to_DFA()
        accept_test_helper(re,cases)
        assert re._matcher_type == 'DFA'

        re = Regex()
        with pytest.raises(rejit.regex.RegexCompilationError):
            re.compile_to_DFA()

