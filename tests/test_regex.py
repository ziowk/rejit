#encoding: utf8

import pytest
import copy
import rejit.regex
from rejit.regex import State
from rejit.regex import NFA
from rejit.regex import Regex

@pytest.fixture(scope='module')
def symbol_list():
    return rejit.regex.supported_chars

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

    def test_symbol_NFA(self, symbol_list):
        for char in symbol_list:
            nfa = NFA.symbol(char)
            cases = zip(symbol_list,map(lambda c: c == char,symbol_list)) 
            accept_test_helper(nfa,cases)

    def test_any_NFA(self, symbol_list):
        special_chars = '^*()-+[]|?.'
        unsupported_chars = '`~!@#$%&=_{}\\:;"\'<>,/'
        all_chars = symbol_list + special_chars + unsupported_chars
        nfa = NFA.any()
        cases = zip(all_chars,[True]*len(all_chars))
        accept_test_helper(nfa,cases)

    def test_none_NFA(self, symbol_list):
        special_chars = '^*()-+[]|?.'
        unsupported_chars = '`~!@#$%&=_{}\\:;"\'<>,/'
        all_chars = symbol_list + special_chars + unsupported_chars
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
        assert id(nfa) != id(nfc)
        assert id(nfa._start) != id(nfc._start)
        assert id(nfa._end) != id(nfc._end)

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

class TestRegexParsing:
    def test_empty_regex(self):
        pattern = ''
        re = Regex(pattern)
        assert re.get_parsed_description() == '\\E'

    def test_symbol_regex(self, symbol_list):
        for char in symbol_list:
            re = Regex(char)
            assert re.get_parsed_description() == char

    def test_union_regex(self):
        pattern = 'a|b'
        re = Regex(pattern)
        assert re.get_parsed_description() == '(a|b)'

    def test_kleene_star_regex(self):
        pattern = 'a*'
        re = Regex(pattern)
        assert re.get_parsed_description() == '(a)*'

    def test_concat_regex(self):
        pattern = 'abcdef'
        re = Regex(pattern)
        assert re.get_parsed_description() == 'abcdef'

    def test_complex_regex(self):
        pattern = 'aa(bb|(cc)*)'
        re = Regex(pattern)
        assert re.get_parsed_description() == 'aa(bb|(cc)*)'
        pattern = 'aa.*bb.?(a|b)?'
        re = Regex(pattern)
        assert re.get_parsed_description() == 'aa(.)*bb(.|\\E)((a|b)|\\E)'
        pattern = 'aa[x-z]*bb[0-0]+cc[]?'
        re = Regex(pattern)
        assert re.get_parsed_description() == 'aa(((x|y)|z))*bb0(0)*cc([]|\\E)'

    def test_one_or_zero_mult_regex(self):
        pattern = 'a?'
        re = Regex(pattern)
        assert re.get_parsed_description() == '(a|\\E)'

    def test_charset_regex(self):
        pattern = '[abc]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '((a|b)|c)'
        pattern = '[Xa-cY0-2Z]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '((((((((X|a)|b)|c)|Y)|0)|1)|2)|Z)'
        pattern = '[aa-bb]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '(((a|a)|b)|b)'
        pattern = '[c-c]'
        re = Regex(pattern)
        assert re.get_parsed_description() == 'c'
        pattern = '[cc]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '(c|c)'
        pattern = '[z-a]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '[]'
        pattern = '[*+.<-?]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '((((((*|+)|.)|<)|=)|>)|?)'
        pattern = '[a-]'
        with pytest.raises(rejit.regex.RegexParseError):
            re = Regex(pattern)
        pattern = '[[-]]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '(([|\\)|])'

    def test_negative_charset_regex(self):
        pattern = '[^abc]'
        with pytest.raises(rejit.regex.RegexParseError):
            re = Regex(pattern)

    def test_period_wildcard_regex(self):
        pattern = '.'
        re = Regex(pattern)
        assert re.get_parsed_description() == '.'

    def test_kleene_plus_regex(self):
        pattern = 'a+'
        re = Regex(pattern)
        assert re.get_parsed_description() == 'a(a)*'

    def test_grouping_regex(self):
        pattern = '(aa|bb)cc'
        re = Regex(pattern)
        assert re.get_parsed_description() == '(aa|bb)cc'

    def test_unsupported_char_regex(self):
        unsupported_chars = '`~!@#$%&=_{}\\:;"\'<>,/'
        for char in unsupported_chars:
            with pytest.raises(rejit.regex.RegexParseError):
                re = Regex(char)

    def test_invalid_use_of_special_char_regex(self):
        special_chars = '^*()-+]|?' # '[' now raises NotImplementedError
        for char in special_chars:
            with pytest.raises(rejit.regex.RegexParseError):
                re = Regex(char)

    def test_empty_set_regex(self):
        pattern = '[]'
        re = Regex(pattern)
        assert re.get_parsed_description() == '[]'

    def test_empty_group_regex(self):
        pattern = '()'
        with pytest.raises(rejit.regex.RegexParseError):
            re = Regex(pattern)


