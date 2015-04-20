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

    def _state_code(self, state, edges, end_states):
        self._emit_label(state)
        self._load_next(state, state in end_states)
        for char,st in filter(lambda x: x[0] != 'any', edges.items()):
            self._emit_cmp_value('char', char)
            self._emit_jump_eq(st)
        if 'any' in edges:
            self._emit_jump(edges['any'])
        self._emit_ret(False)

    def _load_next(self,label,accepting):
        self._emit_inc_var('i')
        self._emit_cmp_name('i', 'length')
        self._emit_jump_ne('load_' + label)
        if accepting:
            self._emit_ret(True)
        else:
            self._emit_ret(False)
        self._emit_label('load_' + label)
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
        self.reg(value)

    @property
    def byte(self):
        return self._byte

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
        imm = None):

    instruction = []

    # add prefices
    if prefix_list:
        instruction += prefix_list

    # add opcodes
    instruction += opcode_list

    # add operands or opcode extension
    if reg or reg_mem or base or index or scale or disp:
        instruction = add_reg_mem_opex(instruction, reg=reg, opex=opex, reg_mem=reg_mem, base=base, index=index, scale=scale, disp=disp)

    # add immediate value
    if imm is not None:
        instruction.append(imm)

    return tuple(instruction)

def add_reg_mem_opex(instruction,*,reg=None,opex=None,reg_mem=None,base=None,index=None,scale=None,disp=None):
    # can't use ESP/R12 as scale: [base + scale * ESP/R12 + disp] not allowed
    assert index != Reg.ESP

    modrm = ModRMByte()

    # register or opcode extension
    if reg is not None:
        modrm.reg = reg 
    if opex is not None:
        modrm.reg = opex

    # r/m address is a register, not memory
    if reg_mem is not None:
        modrm.mod = Mod.REG
        modrm.rm = reg_mem
        return instruction + [modrm]

    # [disp32] on 32bit, [RIP/EIP + disp32] on 64bit
    if base is None and index is None: #[disp]
        modrm.mod = Mod.MEM
        modrm.rm = Reg._DISP32_ONLY
        return instruction + [modrm, disp]

    if index != None: # [xxx + s * yyy + zzz]
        modrm.rm = Reg._USE_SIB
        sib = SIBByte()
        sib.scale = scale
        sib.index = index

        # rare. Have to use Mod.MEM and disp32
        if base is None: # [scale * index + disp]
            modrm.mod = Mod._SIB_BASE_NONE
            sib.base = Reg._SIB_BASE_NONE
            return instruction + [modrm, sib, disp]
        else: # [base + scale * index + disp]
            sib.base = base
            # can't do [EBP/R13 + scale*index] have to use [EBP/R13 + scale*index + 0]
            if disp == 0 and base != Reg.EBP: 
                modrm.mod = Mod.MEM
                return instruction + [modrm, sib, disp]
            elif -128 <= disp <= 127:
                modrm.mod = Mod.MEM_DISP8
                return instruction + [modrm, sib, disp]
            else:
                modrm.mod = Mod.MEM_DISP32
                return instruction + [modrm, sib, disp]
    else: # [base + disp]
        # can't do [ESP/R12 + disp] without SIB, because ESP/R12 means SIB in modRM
        if base == Reg.ESP: # [ESP/R12 + disp]
            modrm.rm = Reg._USE_SIB
            sib = SIBByte()
            # sib.scale = # any will work
            sib.index = Reg._SIB_INDEX_NONE
            if disp == 0:
                modrm.mod = Mod.MEM
                return instruction + [modrm, sib]
            elif -128 <= disp <= 127:
                modrm.mod = Mod.MEM_DISP8
                return instruction + [modrm, sib, disp]
            else:
                modrm.mod = Mod.MEM_DISP32
                return instruction + [modrm, sib, disp]
        else: # [non-ESP + disp]
            modrm.rm = base
            if disp == 0 and base != Reg.EBP:
                modrm.mod = Mod.MEM
                return instruction + [modrm]
            elif -128 <= disp <= 127:
                modrm.mod = Mod.MEM_DISP8
                return instruction + [modrm, disp]
            else:
                modrm.mod = Mod.MEM_DISP32
                return instruction + [modrm, disp]
    
def add_int32(binary, int32):
    binary += struct.pack('@i',int32)

