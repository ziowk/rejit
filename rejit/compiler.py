#encoding: utf8

class Compiler:
    def __init__(self):
        self._ir = []

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

