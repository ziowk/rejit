#encoding: utf8

import pytest

from rejit.dfa import DFA
from rejit.nfa import NFA
import rejit.loadcode as loadcode
import rejit.compiler as compiler
from rejit.compiler import Reg, Scale
from rejit.vmmatcher import VMMatcher
from rejit.jitmatcher import JITMatcher
from rejit.x86encoder import InstructionEncodingError
from tests.helper import accept_test_helper

import tests.automaton_test_cases as auto_cases

class TestVMMatcher:
    def test_empty_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.empty_nfa)), auto_cases.empty_cases)

    def test_symbol_VMMatcher(self):
        for nfa,cases in zip(auto_cases.symbol_nfas, auto_cases.symbol_cases):
            accept_test_helper(VMMatcher(DFA(nfa)), cases)

    def test_any_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.any_nfa)),auto_cases.any_cases)

    def test_none_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.none_nfa)),auto_cases.none_cases)

    def test_kleene_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.kleene_nfa)),auto_cases.kleene_cases)

    def test_kleene_plus_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.kleene_plus_nfa)),auto_cases.kleene_plus_cases)

    def test_concat_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.concat_nfa_1)),auto_cases.concat_cases_1)
        accept_test_helper(VMMatcher(DFA(auto_cases.concat_nfa_2)),auto_cases.concat_cases_2)

    def test_concat_many_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.concat_many_nfa_1)),auto_cases.concat_many_cases_1)
        accept_test_helper(VMMatcher(DFA(auto_cases.concat_many_nfa_2)),auto_cases.concat_many_cases_2)
        accept_test_helper(VMMatcher(DFA(auto_cases.concat_many_nfa_3)),auto_cases.concat_many_cases_3)

    def test_union_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.union_nfa)),auto_cases.union_cases)

    def test_union_many_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.union_many_nfa_1)),auto_cases.union_many_cases_1)
        accept_test_helper(VMMatcher(DFA(auto_cases.union_many_nfa_2)),auto_cases.union_many_cases_2)
        accept_test_helper(VMMatcher(DFA(auto_cases.union_many_nfa_3)),auto_cases.union_many_cases_3)

    def test_char_set_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.char_set_nfa_1)),auto_cases.char_set_cases_1)
        accept_test_helper(VMMatcher(DFA(auto_cases.char_set_nfa_2)),auto_cases.char_set_cases_2)

    def test_zero_or_one_VMMatcher(self):
        vm = VMMatcher(DFA(auto_cases.zero_or_one_nfa))
        print(vm._ir)
        accept_test_helper(VMMatcher(DFA(auto_cases.zero_or_one_nfa)),auto_cases.zero_or_one_cases)

    def test_complex_VMMatcher(self):
        accept_test_helper(VMMatcher(DFA(auto_cases.complex_nfa_1)),auto_cases.complex_cases_1)
        accept_test_helper(VMMatcher(DFA(auto_cases.complex_nfa_2)),auto_cases.complex_cases_2)

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
        with pytest.raises(InstructionEncodingError):
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

    def test_encode_R8_R15_reg_mem_x64(self):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            _, binary = compiler.encode_instruction([0x8B], '64', reg=Reg.EAX, reg_mem=reg, size = 8)
            assert binary == b'\x49\x8B' + (0xC0 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little')

    def test_encode_R8_R15_opcode_reg_x64(self):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            _, binary = compiler.encode_instruction([0x50], '64', opcode_reg=reg)
            assert binary == b'\x41' + (0x50 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little')

    def test_encode_R8_R15_base_x64(self):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            _, binary = compiler.encode_instruction([0x8B], '64', reg=Reg.EAX, base=reg, size = 8)
            if reg == Reg.R12:
                assert binary == b'\x49\x8B\x04\x24' # R12 -> RSP, can't do [R12] without SIB ([R12] means [sib])
            elif reg == Reg.R13:
                assert binary == b'\x49\x8B\x45\x00' # R13 -> RBP, can't do [R13] without disp=0 ([R13] means [RIP] + disp)
            else:
                assert binary == b'\x49\x8B' + (reg & Reg._REG_MASK).to_bytes(1, byteorder='little')

    def test_encode_R8_R15_index_x64(self):
        # R12 -> RSP, can't use RSP as addressing index
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            _, binary = compiler.encode_instruction([0x8B], '64', reg=Reg.EAX, base=Reg.EAX, index=reg, scale=compiler.Scale.MUL_1, size = 8)
            assert binary == b'\x4A\x8B\x04'+ ((reg & Reg._REG_MASK) * 0x8).to_bytes(1, byteorder='little')

    def test_encode_SPL_BPL_SIL_DIL_x64(self):
        low_bytes = [Reg.ESP, Reg.EBP, Reg.ESI, Reg.EDI]
        for reg in low_bytes:
            # mov reg, [rax]
            _, binary = compiler.encode_instruction([0x8A], '64', reg=reg, base=Reg.EAX, size = 1)
            assert binary == b'\x40\x8A'+ ((reg & Reg._REG_MASK) * 0x8).to_bytes(1, byteorder='little')
            # mov al, reg
            _, binary = compiler.encode_instruction([0x8A], '64', reg=Reg.EAX, reg_mem=reg, size = 1)
            assert binary == b'\x40\x8A'+ (0xC0 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little')
            # mov reg, BYTE PTR 1
            _, binary = compiler.encode_instruction([0xB4], '64', opcode_reg=reg, imm=1, size = 1)
            assert binary == b'\x40'+ (0xB4 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little') + b'\x01'

    def test_encode_addr_REG_REGMEM(self):
        # mov al, cl
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.EAX, reg_mem=Reg.ECX)
        assert binary == b'\x8A\xC1'

    def test_encode_addr_REG_DISP(self):
        # mov cl, [0x7FFFFFF0]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x0D\xF0\xFF\xFF\x7F'

        # mov cl, [0x7FFFFFF0]
        _, binary = compiler.encode_instruction([0x8A], '64', reg=Reg.ECX, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x0C\x25\xF0\xFF\xFF\x7F'

    def test_encode_addr_REG_INDEX(self):
        # mov cl, [eax*1 + 0x7FFFFFF0]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, index=Reg.EAX, scale=Scale.MUL_1, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x0C\x05\xF0\xFF\xFF\x7F'

        # mov cl, [eax*2 + 0x70]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, index=Reg.EAX, scale=Scale.MUL_2, disp=0x70)
        assert binary == b'\x8A\x0C\x45\x70\x00\x00\x00'

        # mov cl, [eax*8]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, index=Reg.EAX, scale=Scale.MUL_8)
        assert binary == b'\x8A\x0C\xC5\x00\x00\x00\x00'

    def test_encode_addr_REG_BASE_INDEX(self):
        # mov cl, [ebx + eax*8 + 0x7FFFFFF0]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBX, index=Reg.EAX, scale=Scale.MUL_8, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x8C\xC3\xF0\xFF\xFF\x7F'

        # mov cl, [ebx + eax*4 + 0x70]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBX, index=Reg.EAX, scale=Scale.MUL_4, disp=0x70)
        assert binary == b'\x8A\x4C\x83\x70'

        # mov cl, [ebx + eax*2]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBX, index=Reg.EAX, scale=Scale.MUL_2)
        assert binary == b'\x8A\x0C\x43'

        # mov cl, [ebp + eax*1]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBP, index=Reg.EAX, scale=Scale.MUL_1)
        assert binary == b'\x8A\x4C\x05\x00'

    def test_encode_addr_REG_BASE(self):
        # mov cl, [esp + 0x7FFFFFF0]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.ESP, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x8C\x24\xF0\xFF\xFF\x7F'

        # mov cl, [esp + 0x70]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.ESP, disp=0x70)
        assert binary == b'\x8A\x4C\x24\x70'

        # mov cl, [esp]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.ESP) 
        assert binary == b'\x8A\x0C\x24'

        # mov cl, [ebx + 0x7FFFFFF0]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBX, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x8B\xF0\xFF\xFF\x7F'

        # mov cl, [ebx + 0x70]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBX, disp=0x70)
        assert binary == b'\x8A\x4B\x70'

        # mov cl, [ebx]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBX)
        assert binary == b'\x8A\x0B'

        # mov cl, [ebp]
        _, binary = compiler.encode_instruction([0x8A], '32', reg=Reg.ECX, base=Reg.EBP)
        assert binary == b'\x8A\x4D\x00'

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

class TestJITMatcher:
    # test for bug #84
    def test_accept_return_bool(self):
        matcher = JITMatcher(DFA(NFA.symbol('a')))
        assert isinstance(matcher.accept('a'), bool)
        assert isinstance(matcher.accept('b'), bool)

