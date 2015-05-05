#encoding: utf8

import struct

import rejit.compiler as compiler
import rejit.loadcode as loadcode

class JITMatcher:
    def __init__(self, dfa):
        cc = compiler.Compiler()
        self._ir, self._variables = cc.compile_to_ir(dfa)
        self._ir_transformed = None

        # function call arguments
        args = ('string','length')
        # 64bit Python
        if struct.calcsize("P") == 8:
            self._x86_binary, compilation_data = cc.compile_to_x86_64(self._ir, args, self._variables)
        else:
            self._x86_binary, compilation_data = cc.compile_to_x86_32(self._ir, args, self._variables)

        self._description = dfa.description
        self._jit_func = loadcode.load(self._x86_binary)

    @property
    def description(self):
        return self._description

    def accept(self, s):
        return bool(loadcode.call(self._jit_func,s,len(s)))

