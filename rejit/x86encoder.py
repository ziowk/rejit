#encoding: utf8

import struct
from enum import IntEnum

import rejit.common

class InstructionEncodingError(rejit.common.RejitError): pass

class Reg(IntEnum):
    EAX = 0b0000
    ECX = 0b0001
    EDX = 0b0010
    EBX = 0b0011
    ESP = 0b0100
    EBP = 0b0101
    ESI = 0b0110
    EDI = 0b0111
    R8  = 0b1000
    R9  = 0b1001
    R10 = 0b1010
    R11 = 0b1011
    R12 = 0b1100
    R13 = 0b1101
    R14 = 0b1110
    R15 = 0b1111
    _SIB_BASE_NONE = 0b101
    _DISP32_ONLY_32_RM = 0b101
    _DISP32_ONLY_64_RM = 0b100
    _DISP32_ONLY_64_BASE = 0b101
    _DISP32_ONLY_64_INDEX = 0b100
    _USE_SIB = 0b100
    _SIB_INDEX_NONE = 0b100
    _EXTENDED_MASK = 0b1000 # bit marks registers allowed only in 64-bit mode
    _REG_MASK = 0b111 # bits relevant for ModR/M and SIB bytes

class OPcode(IntEnum):
    OVERRIDE_ADDRESSING = 0x67
    OVERRIDE_SIZE = 0x66

class Mod(IntEnum):
    MEM = 0b00
    MEM_DISP8 = 0b01
    MEM_DISP32 = 0b10
    REG = 0b11
    _SIB_BASE_NONE = 0b00
    _DISP32_ONLY_32_MOD = 0b00
    _DISP32_ONLY_64_MOD = 0b00

class Scale(IntEnum):
    MUL_1 = 0b00
    MUL_2 = 0b01
    MUL_4 = 0b10
    MUL_8 = 0b11
    _DISP32_ONLY_64_SCALE = 0b00

class REXByte:
    def __init__(self, *, w=0, r=0, x=0, b=0):
        assert 0 <= w <= 0b1
        assert 0 <= r <= 0b1
        assert 0 <= x <= 0b1
        assert 0 <= b <= 0b1
        self._byte = 0b01000000 | w << 3 | r << 2 | x << 1 | b

    @property
    def w(self):
        return (self._byte & 0b00001000) >> 3

    @w.setter
    def w(self, value):
        assert 0 <= value <= 0b1
        self._byte &= 0b11110111
        self._byte |= value << 3

    @property
    def r(self):
        return (self._byte & 0b00000100) >> 2

    @r.setter
    def r(self, value):
        assert 0 <= value <= 0b1
        self._byte &= 0b11111011
        self._byte |= value << 2

    @property
    def x(self):
        return (self._byte & 0b00000010) >> 1

    @x.setter
    def x(self, value):
        assert 0 <= value <= 0b1
        self._byte &= 0b11111101
        self._byte |= value << 1

    @property
    def b(self):
        return (self._byte & 0b00000001)

    @b.setter
    def b(self, value):
        assert 0 <= value <= 0b1
        self._byte &= 0b11111110
        self._byte |= value

    @property
    def byte(self):
        return self._byte

    @property
    def binary(self):
        return uint8bin(self._byte)

    def __str__(self):
        return '<REXByte: {byte:08b}, w={w:01b}, r={r:01b}, x={x:01b}, b={b:01b}>'.format(
                byte = self.byte,
                w = self.w,
                r = self.r,
                x = self.x,
                b = self.b,
                )

class ModRMByte:
    def __init__(self, *, mod=0, reg=0, rm=0, opex=0):
        # reg and opex are mutually exclusive!
        # they occupy the same bits in modrm byte
        assert reg == 0 or opex == 0
        # check size
        assert 0 <= mod <= 0b11
        assert 0 <= reg <= 0b111
        assert 0 <= rm <= 0b111
        assert 0 <= opex <= 0b111
        self._byte = mod << 6 | reg << 3 | opex << 3 | rm

    @property
    def mod(self):
        return (self._byte & 0b11000000) >> 6

    @mod.setter
    def mod(self, value):
        assert 0 <= value <= 0b11
        # clear mod bits
        self._byte &= 0b00111111
        # set mod in byte
        self._byte |= value << 6

    @property
    def reg(self):
        return (self._byte & 0b00111000) >> 3

    @reg.setter
    def reg(self, value):
        assert 0 <= value <= 0b111
        # clear reg bits
        self._byte &= 0b11000111
        # set reg in byte
        self._byte |= value << 3

    @property
    def rm(self):
        return (self._byte & 0b00000111)

    @rm.setter
    def rm(self, value):
        assert 0 <= value <= 0b111
        # clear rm bits
        self._byte &= 0b11111000
        # set rm in byte
        self._byte |= value

    @property
    def opex(self):
        return self.reg

    @opex.setter
    def opex(self, value):
        self.reg = value

    @property
    def byte(self):
        return self._byte

    @property
    def binary(self):
        return uint8bin(self._byte)

    def __str__(self):
        return '<ModRMByte: {byte:08b}, mod={mod:02b}, reg/opex={reg:03b}, rm={rm:03b}>'.format(
                byte = self.byte,
                mod = self.mod,
                reg = self.reg,
                rm = self.rm,
                )

class SIBByte:
    def __init__(self, *, base=0, index=0, scale=0):
        assert 0 <= base <= 0b111
        assert 0 <= index <= 0b111
        assert 0 <= scale <= 0b11
        self._byte = scale << 6 | index << 3 | base

    @property
    def scale(self):
        return (self._byte & 0b11000000) >> 6

    @scale.setter
    def scale(self, value):
        assert 0 <= value <= 0b11
        # clear scale bits
        self._byte &= 0b00111111
        # set scale in byte
        self._byte |= value << 6

    @property
    def index(self):
        return (self._byte & 0b00111000) >> 3

    @index.setter
    def index(self, value):
        assert 0 <= value <= 0b111
        # clear index bits
        self._byte &= 0b11000111
        # set index in byte
        self._byte |= value << 3

    @property
    def base(self):
        return (self._byte & 0b00000111)

    @base.setter
    def base(self, value):
        assert 0 <= value <= 0b111
        # clear base bits
        self._byte &= 0b11111000
        # set base in byte
        self._byte |= value

    @property
    def byte(self):
        return self._byte

    @property
    def binary(self):
        return uint8bin(self._byte)

    def __str__(self):
        return '<SIBByte: {byte:08b}, scale={scale:02b}, index={index:03b}, base={base:03b}>'.format(
                byte = self.byte,
                scale = self.scale,
                index = self.index,
                base = self.base,
                )

class Encoder:
    def __init__(self, arch):
        if arch == '64':
            pass # set x86_32 specific methods here
        elif arch == '32':
            pass # set x86_64 specific methods here
        else:
            raise InstructionEncodingError('Architecture {} not supported'.format(arch))
        self._arch = arch

    def encode_instruction(self, opcode_list, arch, *,
            prefix_list = None,
            reg = None,
            opex = None,
            reg_mem = None,
            base = None,
            index = None,
            scale = None,
            disp = None,
            imm = None,
            size = None,
            address_size = None,
            opcode_reg = None):

        instruction = []
        binary = bytearray()

        if prefix_list is None:
            prefix_list = []

        if isinstance(size,str):
            size = type2size(size,arch)

        if arch == '32':
            # 0x66 -> override operand size to 16bit 
            # 0x67 -> override addressing to 16bit
            if size == 2:
                prefix_list.append(OPcode.OVERRIDE_SIZE)
            if address_size == 2:
                raise InstructionEncodingError('16bit addressing not supported')
                #prefix_list.append(OPcode.OVERRIDE_ADDRESSING)
        elif arch == '64':
            # 0x66 -> override operand size to 16bit 
            # 0x67 -> override addressing to 32bit
            if size == 2:
                prefix_list.append(OPcode.OVERRIDE_SIZE)
            if address_size == 4:
                prefix_list.append(OPcode.OVERRIDE_ADDRESSING)
            # This code is tricky because we have to distinguish valid 0 values for
            # rex byte components from absence of a value - None, because it is
            # desirable to omit rex byte if it is not needed.
            # REX.W = 1 -> override operand size to non-default (32->64)
            # REX.R = 1 -> modrm REG to R8-R15
            # REX.X = 1 -> sib INDEX to R8-R15
            # REX.B = 1 -> modrm R/M, sib BASE, opcode REG to R8-R15
            w, r, x, b = None, None, None, None
            if size == 8:
                w = 1
            if match_mask(reg, Reg._EXTENDED_MASK):
                reg = extract_reg(reg)
                r = 1
            if match_mask(index, Reg._EXTENDED_MASK):
                index = extract_reg(index)
                x = 1
            if match_mask(reg_mem, Reg._EXTENDED_MASK) or match_mask(base, Reg._EXTENDED_MASK) or match_mask(opcode_reg, Reg._EXTENDED_MASK):
                reg_mem = extract_reg(reg_mem)
                base = extract_reg(base)
                opcode_reg = extract_reg(opcode_reg)
                b = 1
            if any(map(lambda v: v is not None, (w, r, x, b))):
                w, r, x, b = map(lambda v: 0 if v is None else v, [w, r, x, b])
                rex = REXByte(w=w,r=r,x=x,b=b)
                prefix_list += [rex.byte]
            # if no rex byte and accessing SPL BPL SIL DIL
            elif any(map(lambda x: x in [Reg.ESP, Reg.EBP, Reg.ESI, Reg.EDI], [reg, reg_mem, opcode_reg])) and size == 1:
                rex = REXByte()
                prefix_list += [rex.byte]
        else:
            raise InstructionEncodingError('Architecture {} not supported'.format(arch))

        # add prefices
        if prefix_list:
            instruction += prefix_list
            for prefix in prefix_list:
                binary.append(prefix)

        # opcode_reg -> register in the opcode
        if opcode_reg is not None:
            opcode_list[0] += opcode_reg

        # add opcodes
        instruction += opcode_list
        for opcode in opcode_list:
            binary.append(opcode)

        # add operands or opcode extension
        if reg is not None or reg_mem is not None or base is not None or index is not None or disp is not None or opex is not None:
            self.add_reg_mem_opex(instruction, binary, arch, reg=reg, opex=opex, reg_mem=reg_mem, base=base, index=index, scale=scale, disp=disp)

        # add immediate value
        if imm is not None:
            instruction.append(imm)
            if size == 1:
                binary += int8bin(imm)
            elif size == 2:
                binary += int16bin(imm)
            elif size == 4:
                binary += int32bin(imm)
            elif size == 8:
                binary += int64bin(imm)
            else:
                raise InstructionEncodingError("can't use {} immediate value of size {}".format(imm,size))

        return (tuple(instruction), binary)

    def add_reg_mem_opex(self, instruction, binary, arch, *,
            reg = None, 
            opex = None, 
            reg_mem = None, 
            base = None, 
            index = None, 
            scale = None, 
            disp = None):

        # can't use ESP/R12 as an index
        # [base + scale * ESP/R12 + disp] is not allowed
        assert index != Reg.ESP

        modrm = ModRMByte()

        # register or opcode extension
        if reg is not None:
            modrm.reg = reg 
        if opex is not None:
            modrm.opex = opex

        # r/m address is a register, not memory
        if reg_mem is not None:
            modrm.mod = Mod.REG
            modrm.rm = reg_mem

            instruction += [modrm]
            binary += modrm.binary
            return

        # [disp32] on 32bit is encoded with modrm mod=00 rm=101
        # [disp32] on 64bit is encoded with modrm and sib, because
        # on 64bit mod=00 rm=101 means [RIP/EIP + disp32]
        # so modrm mod=00 rm=100, sib base=101 index=100 scale=any
        if base is None and index is None:
            if arch == '32':
                modrm.mod = Mod._DISP32_ONLY_32_MOD
                modrm.rm = Reg._DISP32_ONLY_32_RM

                instruction += [modrm, disp]
                binary += modrm.binary + int32bin(disp)
            elif arch == '64':
                modrm.mod = Mod._DISP32_ONLY_64_MOD
                modrm.rm = Reg._DISP32_ONLY_64_RM
                sib = SIBByte(base  = Reg._DISP32_ONLY_64_BASE, 
                              index = Reg._DISP32_ONLY_64_INDEX, 
                              scale = Scale._DISP32_ONLY_64_SCALE)

                instruction += [modrm, sib, disp]
                binary += modrm.binary + sib.binary + int32bin(disp)
            return

        # supplement a displacment for memory addressing
        if disp is None:
            disp = 0

        if index is not None:
            modrm.rm = Reg._USE_SIB
            sib = SIBByte()
            sib.scale = scale
            sib.index = index

            # [scale * index + disp]
            # Addressing without a base, rare.
            # Have to use Mod.MEM and disp32
            if base is None: 
                modrm.mod = Mod._SIB_BASE_NONE
                sib.base = Reg._SIB_BASE_NONE

                instruction += [modrm, sib, disp]
                binary += modrm.binary + sib.binary + int32bin(disp)
                return 
            # [base + scale * index + disp]
            else: 
                sib.base = base
                # Can't do [EBP/R13 + scale*index] (Mod.MEM)
                # Have to use [EBP/R13 + scale*index + 0] (Mod.MEM_DISP8)
                # Therefore test `base` != Reg.EBP 
                # Reg.EBP will be handled in the next case
                if disp == 0 and base != Reg.EBP: 
                    modrm.mod = Mod.MEM

                    instruction += [modrm, sib]
                    binary += modrm.binary + sib.binary
                    return
                elif -128 <= disp <= 127:
                    modrm.mod = Mod.MEM_DISP8

                    instruction += [modrm, sib, disp]
                    binary += modrm.binary + sib.binary + int8bin(disp)
                    return 
                else:
                    modrm.mod = Mod.MEM_DISP32

                    instruction += [modrm, sib, disp]
                    binary += modrm.binary + sib.binary + int32bin(disp)
                    return
        # [base + disp]
        else: 
            # can't do [ESP/R12 + disp] without a SIB byte
            # because ESP/R12 R/M means SIB in modRM
            if base == Reg.ESP: # [ESP/R12 + disp]
                modrm.rm = Reg._USE_SIB
                sib = SIBByte()
                sib.base = Reg.ESP
                # Any scale will work, because index is none
                sib.scale = Scale.MUL_1 
                sib.index = Reg._SIB_INDEX_NONE
                if disp == 0:
                    modrm.mod = Mod.MEM

                    instruction += [modrm, sib]
                    binary += modrm.binary + sib.binary
                    return
                elif -128 <= disp <= 127:
                    modrm.mod = Mod.MEM_DISP8

                    instruction += [modrm, sib, disp]
                    binary += modrm.binary + sib.binary + int8bin(disp)
                    return 
                else:
                    modrm.mod = Mod.MEM_DISP32

                    instruction += [modrm, sib, disp]
                    binary += modrm.binary + sib.binary + int32bin(disp)
                    return
            # [non-ESP + disp]
            else: 
                modrm.rm = base
                if disp == 0 and base != Reg.EBP:
                    modrm.mod = Mod.MEM

                    instruction += [modrm]
                    binary += modrm.binary
                    return
                elif -128 <= disp <= 127:
                    modrm.mod = Mod.MEM_DISP8

                    instruction += [modrm, disp]
                    binary += modrm.binary + int8bin(disp)
                    return 
                else:
                    modrm.mod = Mod.MEM_DISP32

                    instruction += [modrm, disp]
                    binary += modrm.binary + int32bin(disp)
                    return 

def match_mask(reg, mask):
    if reg is None:
        return False
    return bool(reg & mask)

def extract_reg(reg):
    if reg is None:
        return None
    return reg & Reg._REG_MASK

def type2size(type, arch):
    if arch == '32':
        if type == 'pointer':
            return 4
        elif type == 'long':
            return 4
        elif type == 'int':
            return 4
        elif type == 'short':
            return 2
        elif type == 'byte':
            return 1
        else:
            raise InstructionEncodingError('Unknown variable type {} in architecture {}'.format(type,arch))
    elif arch == '64':
        if type == 'pointer':
            return 8
        elif type == 'long':
            return 8
        elif type == 'int':
            return 4
        elif type == 'short':
            return 2
        elif type == 'byte':
            return 1
        else:
            raise InstructionEncodingError('Unknown variable type {} in architecture {}'.format(type,arch))
    else:
        raise InstructionEncodingError('Uknown architecture {}'.format(arch))

def int8bin(int8):
    return struct.pack('@b', int8)

def uint8bin(int8):
    return struct.pack('@B', int8)

def int16bin(int16):
    return struct.pack('@h',int16)

def int32bin(int32):
    return struct.pack('@i',int32)

def int64bin(int64):
    return struct.pack('@q',int64)

