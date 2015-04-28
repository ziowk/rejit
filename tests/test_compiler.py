#encoding: utf8

import pytest

from rejit.dfa import DFA
import rejit.loadcode as loadcode
import rejit.compiler as compiler
from rejit.compiler import Reg
from rejit.compiler import VMRegex
from rejit.compiler import JITMatcher
from tests.helper import accept_test_helper

import tests.automaton_test_cases as auto_cases

class TestVMRegex:
    def test_empty_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.empty_nfa)), auto_cases.empty_cases)

    def test_symbol_VMRegex(self):
        for nfa,cases in zip(auto_cases.symbol_nfas, auto_cases.symbol_cases):
            accept_test_helper(VMRegex(DFA(nfa)), cases)

    def test_any_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.any_nfa)),auto_cases.any_cases)

    def test_none_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.none_nfa)),auto_cases.none_cases)

    def test_kleene_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.kleene_nfa)),auto_cases.kleene_cases)

    def test_kleene_plus_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.kleene_plus_nfa)),auto_cases.kleene_plus_cases)

    def test_concat_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.concat_nfa_1)),auto_cases.concat_cases_1)
        accept_test_helper(VMRegex(DFA(auto_cases.concat_nfa_2)),auto_cases.concat_cases_2)

    def test_concat_many_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.concat_many_nfa_1)),auto_cases.concat_many_cases_1)
        accept_test_helper(VMRegex(DFA(auto_cases.concat_many_nfa_2)),auto_cases.concat_many_cases_2)
        accept_test_helper(VMRegex(DFA(auto_cases.concat_many_nfa_3)),auto_cases.concat_many_cases_3)

    def test_union_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.union_nfa)),auto_cases.union_cases)

    def test_union_many_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.union_many_nfa_1)),auto_cases.union_many_cases_1)
        accept_test_helper(VMRegex(DFA(auto_cases.union_many_nfa_2)),auto_cases.union_many_cases_2)
        accept_test_helper(VMRegex(DFA(auto_cases.union_many_nfa_3)),auto_cases.union_many_cases_3)

    def test_char_set_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.char_set_nfa_1)),auto_cases.char_set_cases_1)
        accept_test_helper(VMRegex(DFA(auto_cases.char_set_nfa_2)),auto_cases.char_set_cases_2)

    def test_zero_or_one_VMRegex(self):
        vm = VMRegex(DFA(auto_cases.zero_or_one_nfa))
        print(vm._ir)
        accept_test_helper(VMRegex(DFA(auto_cases.zero_or_one_nfa)),auto_cases.zero_or_one_cases)

    def test_complex_VMRegex(self):
        accept_test_helper(VMRegex(DFA(auto_cases.complex_nfa_1)),auto_cases.complex_cases_1)
        accept_test_helper(VMRegex(DFA(auto_cases.complex_nfa_2)),auto_cases.complex_cases_2)

class TestCodeGen:
    def test_dynamic_code_loading(self):
        # mov eax, dword ptr 7
        # ret
        binary = b'\xb8\x07\x00\x00\x00\xc3'
        code = loadcode.load(binary)
        assert(loadcode.call(code, "elo", 3) == 7)

    def test_add_reg_mem_modrm_test(self):
        # test for a bug fixed in 639968d
        _, binary = compiler.encode_instruction([0x8B], '32', reg=compiler.Reg.EAX, reg_mem=compiler.Reg.EAX)
        assert binary == b'\x8B\xC0' 

    def test_encode_16bit_move(self):
        _, binary = compiler.encode_instruction([0x8B], '32', reg=compiler.Reg.EAX, base=compiler.Reg.ECX, size=2)
        assert binary == b'\x66\x8B\x01'

    def test_encode_16bit_addressing(self):
        with pytest.raises(compiler.CompilationError):
            _, binary = compiler.encode_instruction([0x8B], '32', reg=compiler.Reg.EAX, base=compiler.Reg.EBX, address_size=2)

    def test_encode_16bit_move_x64(self):
        _, binary = compiler.encode_instruction([0x8B], '64', reg=compiler.Reg.EAX, base=compiler.Reg.ECX, size=2)
        assert binary == b'\x66\x8B\x01'

    def test_encode_32bit_addr_x64(self):
        _, binary = compiler.encode_instruction([0x8B], '64', reg=compiler.Reg.EAX, base=compiler.Reg.ECX, address_size = 4)
        assert binary == b'\x67\x8B\x01'

    def test_encode_64bit_move_x64(self):
        _, binary = compiler.encode_instruction([0x8B], '64', reg=compiler.Reg.EAX, base=compiler.Reg.ECX, size = 8)
        assert binary == b'\x48\x8B\x01'

    def test_encode_R8_R15_reg_x64(self):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            _, binary = compiler.encode_instruction([0x8B], '64', reg=reg, base=compiler.Reg.ECX, size = 8)
            assert binary == b'\x4C\x8B' + ((reg & Reg._REG_MASK) * 0x8 + 0x1).to_bytes(1, byteorder='little')

class Testx86accept:
    def test_empty_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.empty_nfa)), auto_cases.empty_cases)

    def test_symbol_JITMatcher(self):
        for nfa,cases in zip(auto_cases.symbol_nfas, auto_cases.symbol_cases):
            accept_test_helper(JITMatcher(DFA(nfa)), cases)

    def test_any_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.any_nfa)),auto_cases.any_cases)

    def test_none_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.none_nfa)),auto_cases.none_cases)

    def test_kleene_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.kleene_nfa)),auto_cases.kleene_cases)

    def test_kleene_plus_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.kleene_plus_nfa)),auto_cases.kleene_plus_cases)

    def test_concat_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.concat_nfa_1)),auto_cases.concat_cases_1)
        accept_test_helper(JITMatcher(DFA(auto_cases.concat_nfa_2)),auto_cases.concat_cases_2)

    def test_concat_many_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.concat_many_nfa_1)),auto_cases.concat_many_cases_1)
        accept_test_helper(JITMatcher(DFA(auto_cases.concat_many_nfa_2)),auto_cases.concat_many_cases_2)
        accept_test_helper(JITMatcher(DFA(auto_cases.concat_many_nfa_3)),auto_cases.concat_many_cases_3)

    def test_union_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.union_nfa)),auto_cases.union_cases)

    def test_union_many_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.union_many_nfa_1)),auto_cases.union_many_cases_1)
        accept_test_helper(JITMatcher(DFA(auto_cases.union_many_nfa_2)),auto_cases.union_many_cases_2)
        accept_test_helper(JITMatcher(DFA(auto_cases.union_many_nfa_3)),auto_cases.union_many_cases_3)

    def test_char_set_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.char_set_nfa_1)),auto_cases.char_set_cases_1)
        accept_test_helper(JITMatcher(DFA(auto_cases.char_set_nfa_2)),auto_cases.char_set_cases_2)

    def test_zero_or_one_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.zero_or_one_nfa)),auto_cases.zero_or_one_cases)

    def test_complex_JITMatcher(self):
        accept_test_helper(JITMatcher(DFA(auto_cases.complex_nfa_1)),auto_cases.complex_cases_1)
        accept_test_helper(JITMatcher(DFA(auto_cases.complex_nfa_2)),auto_cases.complex_cases_2)

