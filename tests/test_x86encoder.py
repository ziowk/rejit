#encoding: utf8

import pytest

from rejit.x86encoder import InstructionEncodingError, Reg, Scale, Encoder, Encoder32, Encoder64, Opcode

@pytest.fixture(scope="module")
def encoder32():
    return Encoder32()

@pytest.fixture(scope="module")
def encoder64():
    return Encoder64()

class TestInstructionEncoding:
    def test_add_reg_mem_modrm_test(self, encoder32):
        # test for a bug fixed in 639968d
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, reg_mem=Reg.EAX)
        assert binary == b'\x8B\xC0' 

    def test_encode_16bit_move(self, encoder32):
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, base=Reg.ECX, size=2)
        assert binary == b'\x66\x8B\x01'

    def test_encode_16bit_addressing(self, encoder32):
        with pytest.raises(InstructionEncodingError):
            binary = encoder32.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, base=Reg.EBX, address_size=2)

    def test_encode_16bit_move_x64(self, encoder64):
        binary = encoder64.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, base=Reg.ECX, size=2)
        assert binary == b'\x66\x8B\x01'

    def test_encode_32bit_addr_x64(self, encoder64):
        binary = encoder64.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, base=Reg.ECX, address_size = 4)
        assert binary == b'\x67\x8B\x01'

    def test_encode_64bit_move_x64(self, encoder64):
        binary = encoder64.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, base=Reg.ECX, size = 8)
        assert binary == b'\x48\x8B\x01'

    def test_encode_R8_R15_reg_x64(self, encoder64):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            binary = encoder64.encode_instruction([Opcode.MOV_R_RM], reg=reg, base=Reg.ECX, size = 8)
            assert binary == b'\x4C\x8B' + ((reg & Reg._REG_MASK) * 0x8 + 0x1).to_bytes(1, byteorder='little')

    def test_encode_R8_R15_reg_mem_x64(self, encoder64):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            binary = encoder64.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, reg_mem=reg, size = 8)
            assert binary == b'\x49\x8B' + (0xC0 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little')

    def test_encode_R8_R15_opcode_reg_x64(self, encoder64):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            binary = encoder64.encode_instruction([Opcode.PUSH_R], opcode_reg=reg)
            assert binary == b'\x41' + (0x50 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little')

    def test_encode_R8_R15_base_x64(self, encoder64):
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R12, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            binary = encoder64.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, base=reg, size = 8)
            if reg == Reg.R12:
                assert binary == b'\x49\x8B\x04\x24' # R12 -> RSP, can't do [R12] without SIB ([R12] means [sib])
            elif reg == Reg.R13:
                assert binary == b'\x49\x8B\x45\x00' # R13 -> RBP, can't do [R13] without disp=0 ([R13] means [RIP] + disp)
            else:
                assert binary == b'\x49\x8B' + (reg & Reg._REG_MASK).to_bytes(1, byteorder='little')

    def test_encode_R8_R15_index_x64(self, encoder64):
        # R12 -> RSP, can't use RSP as addressing index
        ext_regs = [Reg.R8, Reg.R9, Reg.R10, Reg.R11, Reg.R13, Reg.R14, Reg.R15] 
        for reg in ext_regs:
            binary = encoder64.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EAX, base=Reg.EAX, index=reg, scale=Scale.MUL_1, size = 8)
            assert binary == b'\x4A\x8B\x04'+ ((reg & Reg._REG_MASK) * 0x8).to_bytes(1, byteorder='little')

    def test_encode_SPL_BPL_SIL_DIL_x64(self, encoder64):
        low_bytes = [Reg.ESP, Reg.EBP, Reg.ESI, Reg.EDI]
        for reg in low_bytes:
            # mov reg, [rax]
            binary = encoder64.encode_instruction([Opcode.MOV_R_RM_8], reg=reg, base=Reg.EAX, size = 1)
            assert binary == b'\x40\x8A'+ ((reg & Reg._REG_MASK) * 0x8).to_bytes(1, byteorder='little')
            # mov al, reg
            binary = encoder64.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.EAX, reg_mem=reg, size = 1)
            assert binary == b'\x40\x8A'+ (0xC0 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little')
            # mov reg, BYTE PTR 1
            binary = encoder64.encode_instruction([Opcode.MOV_R_IMM_8], opcode_reg=reg, imm=1, size = 1)
            assert binary == b'\x40'+ (0xB0 + (reg & Reg._REG_MASK)).to_bytes(1, byteorder='little') + b'\x01'

    def test_encode_addr_REG_REGMEM(self, encoder32):
        # mov al, cl
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.EAX, reg_mem=Reg.ECX)
        assert binary == b'\x8A\xC1'

    def test_encode_addr_REG_DISP(self, encoder32, encoder64):
        # mov cl, [0x7FFFFFF0]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x0D\xF0\xFF\xFF\x7F'

        # mov cl, [0x7FFFFFF0]
        binary = encoder64.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x0C\x25\xF0\xFF\xFF\x7F'

    def test_encode_addr_REG_INDEX(self, encoder32):
        # mov cl, [eax*1 + 0x7FFFFFF0]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, index=Reg.EAX, scale=Scale.MUL_1, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x0C\x05\xF0\xFF\xFF\x7F'

        # mov cl, [eax*2 + 0x70]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, index=Reg.EAX, scale=Scale.MUL_2, disp=0x70)
        assert binary == b'\x8A\x0C\x45\x70\x00\x00\x00'

        # mov cl, [eax*8]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, index=Reg.EAX, scale=Scale.MUL_8)
        assert binary == b'\x8A\x0C\xC5\x00\x00\x00\x00'

    def test_encode_addr_REG_BASE_INDEX(self, encoder32):
        # mov cl, [ebx + eax*8 + 0x7FFFFFF0]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBX, index=Reg.EAX, scale=Scale.MUL_8, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x8C\xC3\xF0\xFF\xFF\x7F'

        # mov cl, [ebx + eax*4 + 0x70]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBX, index=Reg.EAX, scale=Scale.MUL_4, disp=0x70)
        assert binary == b'\x8A\x4C\x83\x70'

        # mov cl, [ebx + eax*2]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBX, index=Reg.EAX, scale=Scale.MUL_2)
        assert binary == b'\x8A\x0C\x43'

        # mov cl, [ebp + eax*1]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBP, index=Reg.EAX, scale=Scale.MUL_1)
        assert binary == b'\x8A\x4C\x05\x00'

    def test_encode_addr_REG_BASE(self, encoder32):
        # mov cl, [esp + 0x7FFFFFF0]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.ESP, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x8C\x24\xF0\xFF\xFF\x7F'

        # mov cl, [esp + 0x70]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.ESP, disp=0x70)
        assert binary == b'\x8A\x4C\x24\x70'

        # mov cl, [esp]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.ESP) 
        assert binary == b'\x8A\x0C\x24'

        # mov cl, [ebx + 0x7FFFFFF0]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBX, disp=0x7FFFFFF0)
        assert binary == b'\x8A\x8B\xF0\xFF\xFF\x7F'

        # mov cl, [ebx + 0x70]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBX, disp=0x70)
        assert binary == b'\x8A\x4B\x70'

        # mov cl, [ebx]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBX)
        assert binary == b'\x8A\x0B'

        # mov cl, [ebp]
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBP)
        assert binary == b'\x8A\x4D\x00'

def test_index_ESP_R12_check(encoder32, encoder64):
    # mov cl, [ebp+esp*4]
    with pytest.raises(InstructionEncodingError):
        binary = encoder32.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBP, index=Reg.ESP, scale=Scale.MUL_4)
    # mov cl, [rbp+R12*4]
    with pytest.raises(InstructionEncodingError):
        binary = encoder64.encode_instruction([Opcode.MOV_R_RM_8], reg=Reg.ECX, base=Reg.EBP, index=Reg.R12, scale=Scale.MUL_4)

def test_arch_check():
    assert Encoder('32')
    assert Encoder('64')
    with pytest.raises(InstructionEncodingError):
        Encoder('MIPS')

