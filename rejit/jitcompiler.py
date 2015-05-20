#encoding: utf8

import struct
import functools
import os

import rejit.common
import rejit.x86encoder
from rejit.x86encoder import int32bin, Scale, Reg, Opcode

class CompilationError(rejit.common.RejitError): pass

class JITCompiler:
    def __init__(self):
        pass

    def compile_to_x86_32(self, ir, args, var_sizes, save_hex_file=None):
        # used to relay information between passes (other than transformed IR)
        compilation_data = {'args': args, 'var_sizes':var_sizes}
        compilation_data['encoder'] = rejit.x86encoder.Encoder32()

        # apply compilation passes in this order
        ir_transformed, compilation_data = functools.reduce(lambda ir_data, ir_pass: ir_pass(ir_data), 
                [ 
                    JITCompiler._find_vars_pass,
                    JITCompiler._allocate_vars_pass,
                    JITCompiler._add_function_prologue_pass,
                    JITCompiler._replace_vars_pass,
                    JITCompiler._replace_values_pass,
                    JITCompiler._impl_cmp_pass,
                    JITCompiler._impl_mov_pass,
                    JITCompiler._impl_inc_pass,
                    JITCompiler._impl_set_pass,
                    JITCompiler._impl_ret_pass,
                    JITCompiler._find_labels_pass,
                    JITCompiler._impl_jmps_ins_placeholder_pass,
                    JITCompiler._impl_jmps_pass,
                    JITCompiler._purge_labels_pass,
                ],
                (ir, compilation_data))

        # merge generated x86 instructions to create final binary
        x86_code = JITCompiler._merge_binary_instructions(ir_transformed)

        if save_hex_file:
            with open(save_hex_file, 'wt') as output:
                for b in x86_code:
                    output.write('{:02x} '.format(b))

        return x86_code, compilation_data

    def compile_to_x86_64(self, ir, args, var_sizes, save_hex_file=None):
        # used to relay information between passes (other than transformed IR)
        compilation_data = {'args': args, 'var_sizes':var_sizes}
        compilation_data['encoder'] = rejit.x86encoder.Encoder64()

        # apply compilation passes in this order
        ir_transformed, compilation_data = functools.reduce(lambda ir_data, ir_pass: ir_pass(ir_data), 
                [ 
                    JITCompiler._find_vars_pass,
                    JITCompiler._allocate_vars_pass_64,
                    JITCompiler._add_function_prologue_pass_64,
                    JITCompiler._replace_vars_pass,
                    JITCompiler._replace_values_pass,
                    JITCompiler._impl_cmp_pass,
                    JITCompiler._impl_mov_pass,
                    JITCompiler._impl_inc_pass_64,
                    JITCompiler._impl_set_pass,
                    JITCompiler._impl_ret_pass,
                    JITCompiler._find_labels_pass,
                    JITCompiler._impl_jmps_ins_placeholder_pass,
                    JITCompiler._impl_jmps_pass,
                    JITCompiler._purge_labels_pass,
                ],
                (ir, compilation_data))

        # merge generated x86 instructions to create final binary
        x86_code = JITCompiler._merge_binary_instructions(ir_transformed)

        if save_hex_file:
            with open(save_hex_file, 'wt') as output:
                for b in x86_code:
                    output.write('{:02x} '.format(b))

        return x86_code, compilation_data

    @staticmethod
    def _find_vars_pass(ir_data):
        ir, data = ir_data
        names_read = set()
        names_written = set()
        # find variables referenced by IR instructions
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
        # probably could skip instructions which only use write-only vars...
        # and do: vars_to_allocate = set(names_read)
        vars_to_allocate = names_read | names_written

        data['names_read'] = names_read
        data['names_written'] = names_written
        data['vars_to_allocate'] = vars_to_allocate
        return ir_data

    @staticmethod
    def _allocate_vars_pass(ir_data):
        ir, data = ir_data
        vars_to_allocate  = data['vars_to_allocate']

        # registers available for variables
        # can't access ESI EDI lowest byte in 32bit mode
        reg_list = [Reg.EAX, Reg.ECX, Reg.EDX, Reg.EBX] 

        # currently variables can be stored in registers only
        if len(reg_list) < len(vars_to_allocate):
            raise CompilationError('Not enough registers')
        var_regs = dict(zip(vars_to_allocate, reg_list))
        used_regs = set(var_regs.values())

        # calle-saved registers
        calle_saved = [Reg.EBX, Reg.ESI, Reg.EDI, Reg.EBP]

        # find registers which have to be restored
        regs_to_restore = list(used_regs & set(calle_saved))

        data['var_regs'] = var_regs
        data['used_regs'] = used_regs
        data['regs_to_restore'] = regs_to_restore
        return ir_data

    @staticmethod
    def _allocate_vars_pass_64(ir_data):
        ir, data = ir_data
        args = data['args']
        vars_to_allocate = data['vars_to_allocate']

        if os.name == 'nt':
            # first arguments are passed in registers (and we don't support more)
            arg_regs = [Reg.ECX, Reg.EDX, Reg.R8, Reg.R9] 
            # caller-saved registers - no need to restore them
            scratch_regs = [Reg.EAX, Reg.ECX, Reg.EDX, Reg.R8, Reg.R9, Reg.R10, Reg.R11]
        elif os.name == 'posix':
            arg_regs = [Reg.EDI, Reg.ESI, Reg.EDX, Reg.ECX, Reg.R8, Reg.R9] 
            scratch_regs = [Reg.EAX, Reg.ECX, Reg.EDX, Reg.ESI, Reg.EDI, Reg.R8, Reg.R9, Reg.R10, Reg.R11]
        else:
            raise CompilationError('Not supported system: {}'.format(os.name))

        if len(args) > len(arg_regs):
            raise CompilationError('More than {} args currently not supported on this platform'.format(len(args)))

        # arguments are allocated to their registers
        var_regs = dict(zip(args, arg_regs))

        # registers which are available for variables which aren't arguments
        reg_list = set(scratch_regs) - set(var_regs.values())

        not_allocated = vars_to_allocate - set(args)

        # currently variables can be stored in registers only
        if len(reg_list) < len(not_allocated):
            raise CompilationError('not enough registers')
        var_regs.update(dict(zip(not_allocated, reg_list)))
        used_regs = set(var_regs.values())

        # no need for using calle saved registers in 64bit mode
        regs_to_restore = []

        data['var_regs'] = var_regs
        data['used_regs'] = used_regs
        data['regs_to_restore'] = regs_to_restore
        return ir_data

    @staticmethod
    def _add_function_prologue_pass(ir_data):
        ir, data = ir_data
        args = data['args']
        encoder = data['encoder']
        var_regs = data['var_regs']
        var_sizes = data['var_sizes']
        regs_to_restore = data['regs_to_restore']

        ir_new_stack_frame = JITCompiler._new_stack_frame(encoder)
        ir_calle_reg_save = JITCompiler._calle_reg_save(regs_to_restore, encoder)
        ir_load_args = JITCompiler._load_args(args, var_regs, var_sizes, encoder)

        return (ir_new_stack_frame + ir_calle_reg_save + ir_load_args + ir, data)

    @staticmethod
    def _add_function_prologue_pass_64(ir_data):
        ir, data = ir_data
        encoder = data['encoder']

        ir_new_stack_frame = JITCompiler._new_stack_frame(encoder)

        return (ir_new_stack_frame + ir, data)

    @staticmethod
    def _load_args(args, var_regs, var_sizes, encoder):
        # offset from [ebp] to arguments (return address, old ebp)
        # warning: different in 64bit code
        args_offset = 8

        ir_1 = []
        total = args_offset
        for arg in args:
            if arg in var_regs:
                binary = encoder.encode_instruction([Opcode.MOV_R_RM], reg=var_regs[arg], base=Reg.EBP, disp=total, size=var_sizes[arg])
                ir_1.append((('mov',var_regs[arg],'=[',Reg.ESP,'+',total,']'), binary))
            total += encoder.type2size(var_sizes[arg])
        return ir_1

    @staticmethod
    def _new_stack_frame(encoder):
        ir_1 = []
        binary = encoder.enc_push(Reg.EBP)
        ir_1.append((('push', Reg.EBP),binary))
        binary = encoder.encode_instruction([Opcode.MOV_R_RM], reg=Reg.EBP,reg_mem=Reg.ESP, size='long')
        ir_1.append((('mov',Reg.EBP,Reg.ESP), binary))
        return ir_1

    @staticmethod
    def _calle_reg_save(regs_to_restore, encoder):
        ir_1 = []
        for reg in regs_to_restore:
            binary = encoder.enc_push(reg)
            ir_1.append((('push', reg),binary))
        return ir_1

    @staticmethod
    def _replace_vars_pass(ir_data):
        ir, data = ir_data
        var_regs = data['var_regs']
        var_sizes = data['var_sizes']
        encoder = data['encoder']

        ir_1 = []
        for inst in ir:
            if inst[0] in { 'cmp name',  'cmp value', 'set', 'inc', 'move', 'move indexed'}:
                if inst[0] == 'cmp name':
                    assert encoder.type2size(var_sizes[inst[1]]) == encoder.type2size(var_sizes[inst[2]])
                    ir_1.append((inst[0], var_regs[inst[1]],  var_regs[inst[2]], var_sizes[inst[1]]))
                elif inst[0] == 'cmp value':
                    ir_1.append((inst[0], var_regs[inst[1]], inst[2], var_sizes[inst[1]]))
                elif inst[0] == 'set':
                    ir_1.append((inst[0], var_regs[inst[1]], inst[2], var_sizes[inst[1]]))
                elif inst[0] == 'inc':
                    ir_1.append((inst[0], var_regs[inst[1]], var_sizes[inst[1]]))
                elif inst[0] == 'move':
                    assert var_sizes[inst[1]] == var_sizes[inst[2]]
                    ir_1.append((inst[0], var_regs[inst[1]], var_regs[inst[2]], var_sizes[inst[1]]))
                elif inst[0] == 'move indexed':
                    assert encoder.type2size(var_sizes[inst[2]]) == encoder.type2size(var_sizes[inst[3]])
                    ir_1.append((inst[0], var_regs[inst[1]], var_regs[inst[2]], var_regs[inst[3]],
                        var_sizes[inst[1]], var_sizes[inst[2]]))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _replace_values_pass(ir_data):
        ir, data = ir_data

        ir_1 = []
        for inst in ir:
            if inst[0] == 'cmp value':
                ir_1.append((inst[0], inst[1], ord(inst[2]), inst[3]))
            elif inst[0] == 'set':
                ir_1.append((inst[0], inst[1], inst[2], inst[3]))
            elif inst[0] == 'ret':
                ir_1.append((inst[0], 1 if inst[1] else 0))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _impl_cmp_pass(ir_data):
        ir, data = ir_data
        encoder = data['encoder']

        ir_1 = []
        for inst in ir:
            if inst[0] == 'cmp value':
                binary = encoder.encode_instruction([Opcode.CMP_RM_IMM_8], opex=Opcode.CMP_RM_IMM_8_EX, reg_mem=inst[1], imm=inst[2], size=inst[3])
                ir_1.append((('cmp',inst[1],inst[2]), binary))
            elif inst[0] == 'cmp name':
                binary = encoder.encode_instruction([Opcode.CMP_RM_R], reg=inst[1], reg_mem=inst[2], size=inst[3])
                ir_1.append((('cmp',inst[1],inst[2]), binary))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _impl_mov_pass(ir_data):
        ir, data = ir_data
        encoder = data['encoder']

        ir_1 = []
        for inst in ir:
            if inst[0] == 'move indexed':
                binary = encoder.encode_instruction([Opcode.MOV_R_RM_8], reg=inst[1],base=inst[2],index=inst[3],scale=Scale.MUL_1,size=inst[4], address_size=inst[5])
                ir_1.append((('mov',inst[1],'=[',inst[2],'+',inst[3],']'), binary))
            elif inst[0] == 'move':
                binary = encoder.encode_instruction([Opcode.MOV_R_RM], reg=inst[1],reg_mem=inst[2],size=inst[3])
                ir_1.append((inst, binary))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _impl_inc_pass(ir_data):
        ir, data = ir_data
        encoder = data['encoder']

        ir_1 = []
        for inst in ir:
            if inst[0] == 'inc':
                binary = encoder.encode_instruction([Opcode.INC_R_32], opcode_reg=inst[1], size=inst[2])
                ir_1.append((inst, binary))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _impl_inc_pass_64(ir_data):
        ir, data = ir_data
        encoder = data['encoder']

        ir_1 = []
        for inst in ir:
            if inst[0] == 'inc':
                binary = encoder.encode_instruction([Opcode.INC_RM_64], opex=Opcode.INC_RM_64_EX, reg_mem=inst[1], size=inst[2])
                ir_1.append((inst, binary))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _impl_set_pass(ir_data):
        ir, data = ir_data
        encoder = data['encoder']

        ir_1 = []
        for inst in ir:
            if inst[0] == 'set':
                binary = encoder.encode_instruction([Opcode.MOV_R_IMM], opcode_reg=inst[1], imm=inst[2], size=inst[3])
                ir_1.append((('mov',inst[1], inst[2]), binary))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _impl_ret_pass(ir_data):
        ir, data = ir_data
        regs_to_restore = data['regs_to_restore']
        encoder = data['encoder']

        ir_1 = []
        for inst in ir:
            if inst[0] == 'ret':
                binary = encoder.encode_instruction([Opcode.MOV_R_IMM], opcode_reg=Reg.EAX, imm=1 if inst[1] else 0,size='int')
                ir_1.append((('mov', Reg.EAX, inst[1]),binary))
                ir_1.append(('jump','return'))
            else:
                ir_1.append(inst)
        ir_1.append(('label', 'return'))
        for reg in reversed(regs_to_restore):
            binary = encoder.enc_pop(reg)
            ir_1.append((('pop', reg),binary))
        binary = encoder.enc_pop(Reg.EBP)
        ir_1.append((('pop', Reg.EBP),binary))
        binary = encoder.enc_ret()
        ir_1.append((('ret',),binary))

        return (ir_1, data)

    @staticmethod
    def _find_labels_pass(ir_data):
        ir, data = ir_data

        labels = dict()
        for num,inst in enumerate(ir):
            if inst[0] == 'label':
                if inst[1] in labels:
                    raise CompilationError('label "{}" already defined'.format(inst[1]))
                labels[inst[1]] = num

        data['labels'] = labels
        return ir_data

    @staticmethod
    def _impl_jmps_ins_placeholder_pass(ir_data):
        ir, data = ir_data
        labels = data['labels']
        encoder = data['encoder']

        labels_set = set(labels)
        ir_1 = []
        jmp_targets = set()
        jmp_map = {'jump':'jmp', 'jump eq':'je', 'jump ne':'jne'}
        for num,inst in enumerate(ir):
            if inst[0] in {'jump', 'jump eq', 'jump ne'}:
                if inst[1] not in labels_set:
                    raise CompilationError('label "{}" not found'.format(inst[1]))
                jmp_targets.add(inst[1])
                if inst[0] == 'jump':
                    binary = encoder.enc_jmp_near(0)
                elif inst[0] == 'jump eq':
                    binary = encoder.encode_instruction([Opcode.JE_REL_A, Opcode.JE_REL_B], imm=0,size=4)
                elif inst[0] == 'jump ne':
                    binary = encoder.encode_instruction([Opcode.JNE_REL_A, Opcode.JNE_REL_B], imm=0,size=4)
                ir_1.append(((jmp_map[inst[0]], inst[1]), binary))
            else:
                ir_1.append(inst)

        data['jmp_targets'] = jmp_targets
        return (ir_1, data)

    @staticmethod
    def _impl_jmps_pass(ir_data):
        ir, data = ir_data
        labels = data['labels']

        ir_1 = []
        for num,inst in enumerate(ir):
            if inst[0][0] in {'jmp', 'je', 'jne'}:
                # calculate jump offset
                target_num = labels[inst[0][1]]
                if target_num > num:
                    no_label = filter(lambda x: x[0]!='label', ir[num+1:target_num])
                    jump_length = functools.reduce(lambda acc,x: acc + len(x[1]), no_label, 0)
                else: 
                    no_label = filter(lambda x: x[0]!='label', ir[target_num:num+1])
                    jump_length = functools.reduce(lambda acc,x: acc - len(x[1]), no_label, 0)
                new_bin = inst[1][:-4] + int32bin(jump_length)
                ir_1.append((inst[0], new_bin))
            else:
                ir_1.append(inst)

        return (ir_1, data)

    @staticmethod
    def _purge_labels_pass(ir_data):
        ir, data = ir_data
        return (list(filter(lambda x: x[0]!='label', ir)), data)

    @staticmethod
    def _merge_binary_instructions(ir):
        return functools.reduce(lambda acc, x: acc+x, map(lambda x: x[1], ir))

