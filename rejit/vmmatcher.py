#encoding: utf8

import rejit.common
import rejit.ir_compiler as ir_compiler

class VMError(rejit.common.RejitError): pass

class VMMatcher:
    def __init__(self, dfa):
        self._description = dfa.description
        self._ir, self._variables = ir_compiler.IRCompiler().compile_to_ir(dfa,True)
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

