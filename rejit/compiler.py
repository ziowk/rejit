#encoding: utf8

from enum import IntEnum
import struct

import rejit.common

class VMError(rejit.common.RejitError): pass

class CompilationError(rejit.common.RejitError): pass

class Compiler:
    def __init__(self):
        self._ir = []

    def compile_to_ir(self, dfa, rewrite_state_names=False):
        # change state names better readability
        if rewrite_state_names:
            state_label = dict(zip(dfa._states_edges, map(str,range(len(dfa._states_edges)))))
            states_edges = {
                    state_label[st] : {char: state_label[st2] for char, st2 in c2s.items()}
                        for st, c2s in dfa._states_edges.items()
                        }
            start = state_label[dfa._start]
            end_states = {state_label[st] for st in dfa._end_states}
        else:
            states_edges = dfa._states_edges
            start = dfa._start
            end_states = dfa._end_states

        self._ir = []
        # actual code
        self._emit_set_var('i',-1)
        self._state_code(start, states_edges[start], end_states)
        for st,edges in filter(lambda x: x[0] != start, states_edges.items()):
            self._state_code(st, edges, end_states)
        return self._ir

    def compile_to_x86_32(self, ir, args):
        # registers available for variables
        # can't access ESI EDI lowest byte in 32bit mode
        reg_list = [Reg.EAX, Reg.ECX, Reg.EDX, Reg.EBX] 

        # registers saved by calle
        calle_saved = [Reg.EBX, Reg.ESI, Reg.EDI, Reg.EBP]

        # find variables referenced by IR instructions
        names_read, names_written = Compiler._find_vars(ir)

        # probably could skip instructions which only use write-only vars...
        # and do: vars_to_allocate = names_read
        vars_to_allocate = names_read | names_written

        # currently variables can be stored in registers only
        var_regs, used_regs = Compiler._allocate_vars(vars_to_allocate, reg_list)

        # find registers which have to be restored
        to_restore = list(used_regs & set(calle_saved))

        # `args` is a JITted function's signature in format (name, size)
        # Names are converted to registers which store them
        # or None if they aren't used.
        reg_args = [(var_regs[arg],size) if arg in var_regs else (None,size) 
                        for arg, size in args]

        # offset from [ebp] to arguments (return address, old ebp)
        # warning: different in 64bit code
        args_offset = 8

    @staticmethod
    def _find_vars(ir):
        names_read = set()
        names_written = set()
        for inst in ir:
            if inst[0] == 'cmp name':
                names_read.add(inst[1])
                names_read.add(inst[2])
            elif inst[0] == 'cmp value':
                names_read.add(inst[1])
            elif inst[0] == 'set':
                names_written.add(inst[1])
            elif inst[0] == 'inc':
                names_read.add(inst[1])
            elif inst[0] == 'move':
                names_written.add(inst[1])
                names_read.add(inst[2])
            elif inst[0] == 'move indexed':
                names_written.add(inst[1])
                names_read.add(inst[2])
                names_read.add(inst[3])
        return names_read, names_written

    @staticmethod
    def _allocate_vars(vars_to_allocate, reg_list):
        if len(reg_list) < len(vars_to_allocate):
            raise CompilationError('not enough registers')
        var_regs = dict(zip(vars_to_allocate, reg_list))
        used_regs = set(var_regs.values())
        return var_regs, used_regs

    @staticmethod
    def _calle_reg_save(to_restore):
        ir_1 = []
        _, binary = encode_instruction([0x50+Reg.EBP])
        ir_1.append((('push', Reg.EBP),binary))
        _, binary = encode_instruction([0x8B], reg=Reg.EBP,reg_mem=Reg.ESP)
        ir_1.append((('mov',Reg.EBP,Reg.ESP), binary))
        for reg in to_restore:
            _, binary = encode_instruction([0x50+reg])
            ir_1.append((('push', reg),binary))
        return ir_1

    def _state_code(self, state, edges, end_states):
        self._emit_label(state)
        self._load_next(state, state in end_states, bool(edges)) # bool() to be more explicit
        for char,st in filter(lambda x: x[0] != 'any', edges.items()):
            self._emit_cmp_value('char', char)
            self._emit_jump_eq(st)
        if 'any' in edges:
            self._emit_jump(edges['any'])
        self._emit_ret(False)

    def _load_next(self,label,accepting,load_next_needed):
        self._emit_inc_var('i')
        self._emit_cmp_name('i', 'length')
        self._emit_jump_ne('load_' + label)
        if accepting:
            self._emit_ret(True)
        else:
            self._emit_ret(False)
        self._emit_label('load_' + label)
        if load_next_needed:
            self._emit_move_indexed('char', 'string', 'i')

    def _emit_label(self, label):
        self._ir.append(('label', label))

    def _emit_jump(self, label):
        self._ir.append(('jump', label))

    def _emit_jump_eq(self, label):
        self._ir.append(('jump eq', label))

    def _emit_jump_ne(self, label):
        self._ir.append(('jump ne', label))

    def _emit_inc_var(self, var_name):
        self._ir.append(('inc', var_name))

    def _emit_set_var(self, var_name, value):
        self._ir.append(('set', var_name, value))

    def _emit_move(self, to_name, from_name):
        self._ir.append(('move', to_name, from_name))

    def _emit_move_indexed(self, to_name, from_name, index_name):
        self._ir.append(('move indexed', to_name, from_name, index_name))

    def _emit_cmp_value(self, name, value):
        self._ir.append(('cmp value', name, value))

    def _emit_cmp_name(self, name1, name2):
        self._ir.append(('cmp name', name1, name2))

    def _emit_ret(self, value):
        self._ir.append(('ret', value))

class VMRegex:
    def __init__(self, dfa):
        self._description = dfa.description
        self._ir = Compiler().compile_to_ir(dfa,True)
        self._runtime_limit = 10000
    
    def accept(self, string):
        ret_val, info = self._simulate({'string':string, 'length':len(string)})
        return ret_val

    @property
    def description(self):
        return self._description

    def _simulate(self, input_vars):
        label2ip = dict(map(
            lambda x: (x[0][1],x[1]), 
            filter(
                lambda inst: inst[0][0] == 'label',
                zip(self._ir,range(len(self._ir)))
                )
            ))
        var = dict()
        var.update(input_vars)
        eq_reg = False
        ret_val = None
        ip = 0
        icounter = 0
        while True:
            inst = self._ir[ip]
            print('ip: {}, instruction: {}'.format(ip, inst))
            # switch on instruction type
            if inst[0] == 'set':
                var[inst[1]] = inst[2]
            elif inst[0] == 'inc':
                var[inst[1]] += 1
            elif inst[0] == 'move':
                to = inst[1]
                from_ = inst[2]
                var[to] = var[from_]
            elif inst[0] == 'move indexed':
                to = inst[1]
                from_ = inst[2]
                index = var[inst[3]]
                var[to] = var[from_][index]
            elif inst[0] == 'cmp name':
                eq_reg = var[inst[1]] == var[inst[2]]
            elif inst[0] == 'cmp value':
                eq_reg = var[inst[1]] == inst[2]
            elif inst[0] == 'jump':
                ip = label2ip[inst[1]]
            elif inst[0] == 'jump eq':
                if eq_reg:
                    ip = label2ip[inst[1]]
            elif inst[0] == 'jump ne':
                if not eq_reg:
                    ip = label2ip[inst[1]]
            elif inst[0] == 'ret':
                ret_val = inst[1]
                break
            elif inst[0] == 'label':
                raise VMError('Tried to execute label: {}'.format(inst))
            else:
                raise VMError('Unknown instruction {}'.format(inst))
            # advance ip
            ip += 1
            # and skip consecutive labels
            while self._ir[ip][0] == 'label': ip += 1
            # count executed instructions
            icounter += 1
            if icounter > self._runtime_limit:
                raise VMError('Too long runtime. Infinite loop?')
        info = {'var': var, 'result': ret_val, 'icounter': icounter}
        return ret_val, info

class Reg(IntEnum):
    EAX = 0b000
    ECX = 0b001
    EDX = 0b010
    EBX = 0b011
    ESP = 0b100
    EBP = 0b101
    ESI = 0b110
    EDI = 0b111
    _SIB_BASE_NONE = 0b101
    _DISP32_ONLY = 0b101
    _USE_SIB = 0b100
    _SIB_INDEX_NONE = 0b100
    R8 = 0b000
    R9 = 0b001
    R10 = 0b010
    R11 = 0b011
    R12 = 0b100
    R13 = 0b101
    R14 = 0b110
    R15 = 0b111

class Mod(IntEnum):
    MEM = 0b00
    MEM_DISP8 = 0b01
    MEM_DISP32 = 0b10
    REG = 0b11
    _SIB_BASE_NONE = 0b00

class Scale(IntEnum):
    MUL_1 = 0b00
    MUL_2 = 0b01
    MUL_4 = 0b10
    MUL_8 = 0b11

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
    def __init__(self, base=0, index=0, scale=0):
        assert 0 <= base <= 0b111
        assert 0 <= index <= 0b11
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

def encode_instruction(opcode_list, *,
        prefix_list = None,
        reg = None,
        opex = None,
        reg_mem = None,
        base = None,
        index = None,
        scale = None,
        disp = None,
        imm = None,
        imm_size = None):

    instruction = []
    binary = bytearray()

    # add prefices
    if prefix_list:
        instruction += prefix_list
        for prefix in prefix_list:
            binary.append(prefix)

    # add opcodes
    instruction += opcode_list
    for opcode in opcode_list:
        binary.append(opcode)

    # add operands or opcode extension
    if reg is not None or reg_mem is not None or base is not None or index is not None or disp is not None or opex is not None:
        add_reg_mem_opex(instruction, binary, reg=reg, opex=opex, reg_mem=reg_mem, base=base, index=index, scale=scale, disp=disp)

    # add immediate value
    if imm is not None:
        instruction.append(imm)
        if imm_size == 1:
            binary += int8bin(imm)
        elif imm_size == 4:
            binary += int32bin(imm)
        else:
            raise CompilationError("can't use {} immediate value of size {}".format(imm,imm_size))

    return (tuple(instruction), binary)

def add_reg_mem_opex(instruction, binary, *,
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

    # [disp32] on 32bit, [RIP/EIP + disp32] on 64bit
    if base is None and index is None:
        modrm.mod = Mod.MEM
        modrm.rm = Reg._DISP32_ONLY

        instruction += [modrm, disp]
        binary += modrm.binary + int32bin(disp)
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

# see also int.to_bytes(len,order)
def int8bin(int8):
    return struct.pack('@b', int8)

def uint8bin(int8):
    return struct.pack('@B', int8)

def int32bin(int32):
    return struct.pack('@i',int32)


