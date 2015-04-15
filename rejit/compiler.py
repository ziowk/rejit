#encoding: utf8

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

