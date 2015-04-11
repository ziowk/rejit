#encoding: utf8

import functools
import string
import copy
import collections

try:
    import graphviz
except ImportError:
    pass

class RegexError(Exception): pass

class RegexParseError(RegexError): pass

class RegexCompilationError(RegexError): pass

class NFAInvalidError(RegexError): pass

class NFAArgumentError(RegexError): pass

class State:
    """State class for internal use of NFA objects.

    A `State` object represents a state in an automation, which is essentially
    a graph. The state is connected to other states with edges. All edges in
    the automaton form a transition function.
    
    An edge is a tuple which represents a single transition. The first element
    of the tuple is a string label which is the requirement for the transition.
    The second element is a state to which the transition points.

    Transition's requirement label can be:
    * a single character
    * an empty string for an epsilon edge
    * a special string for a special edge type

    Currently only special edge type is 'any', which allows transition for any
    character.

    Attributes:
    _edges (list of tuples(str, State)): a list of edges from the state to
        other states.
    _state_num (int): a unique id number for each state which should be human
    readable.
    """

    _state_counter = 0
    """_state_counter allows assigning State objects unique readable ids during
    creation or copying."""

    def __init__(self):
        """Create an empty state without edges.

        Returns:
        A new state without edges.
        """
        self._edges = [] # Edge = ('char', State)
        self._state_num = State._state_counter # for printing purposes only
        State._state_counter += 1

    def add(self,label,state):
        """Add a new edge from this state to other state.

        Transition's requirement label can be:
        * a single character
        * an empty string for an epsilon edge
        * a special string for a special edge type

        For more information about edges see `State` class' documentation.

        Args:
        label (str): A label, requirement for transition to the other state.
        state (State): Other state, to which the edge points.
        """
        self._edges.append((label,state))

    def __repr__(self):
        return '<State: {num}, id: {ident}, edges: {e}>'.format(num=str(self._state_num), ident=str(id(self)),
                                                                e=list(map(lambda x: (x[0],x[1]._state_num), self._edges)))
    def __deepcopy__(self, memo):
        """Return a deep copy of the State.

        Standard implementation of `__deepcopy__` was overriden to ensure
        that each state has globally unique `_state_num`.

        Args:
        memo (dict): mandatory __deepcopy__ dictionary parameter, for keeping
            track of copied objects.
        """
        st = State()
        st._edges = copy.deepcopy(self._edges, memo)
        return st

class NFA:
    """Nondeterministic finite automaton for accepting regular languages.

    A NFA is essentially a graph, made of states connected by edges. All edges
    in the automaton form a transition function. There are two special states
    in the NFA: `_start` state from which the automaton starts, and `_end`
    state, which is the accepting state. For details regarding states and edges
    see `State` class docs.

    A NFA object can be used to determine if a string belongs to the NFA's
    accepted language. The NFA's accepted language is equivalent to a regular
    expression, which means that the NFA can be used for matching them.

    NFA objects should only be created with NFA generation methods or
    combined using NFA combination methods. NFA generation methods create new
    basic NFA objects. NFA combination methods transform input NFA objects
    to create complex ones out of them.

    NFA class uses a concept of object validity. Only a valid object can
    be used to `accept` strings, or be passed to NFA's combination methods.
    
    Valid objects are ones created with NFA's generation methods or returned
    from NFA's combination methods.

    Invalid objects are ones passed to NFA's combination methods. If user wants
    to use a NFA object after it was passed to a NFA's combining method, user
    should create a copy of the NFA using `deepcopy` method from standard
    library's `copy` module.

    Attributes:
    description (str): read-only property containing regular expression
        equivalent of the NFA
    valid (bool): indicates if the NFA object is valid for use
    _start (State): NFA's starting state
    _end (State): NFA's finishing state
    _description (str): internal variable for `description` property
    """

    def __init__(self,start,end):
        """Construct an empty NFA object with starting and finishing states

        Warning:
        User probably should never directly create NFAs. Use NFA's generation
        methods such as `empty`, `none`, `any`, `symbol`, `char_set` and
        combine them using NFA's combination methods `union`, `concat`,
        `kleene`, `kleene_plus`, `union_many`, `concat_many`, `zero_or_one`.

        Args:
        start (State): NFA's starting state
        end (State): NFA's finishing state

        Returns:
        An empty NFA object with provided starting and finishing states
            and empty description.
        """
        self._start = start
        self._end = end
        self._description = ''

    @property
    def description(self):
        return self._description

    @property
    def valid(self):
        return self._start is not None

    def accept(self,s):
        """Check if a string belongs to the NFA's accepted language.

        In other words, this checks if the string exactly matches the NFA's
        regular expression equivalent.
        
        This method can only be called on a valid NFA object.
        
        Raises:
        NFAInvalidError: if called on an invalid NFA object

        Args:
        s (str): the string which is tested for a match

        Returns:
        A bool which indicates if the string is accepted by the NFA.
        """
        if not self.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        states = {self._start}
        while states:
            states = NFA._moveEpsilon(states)
            if not s:
                break
            states = NFA._moveChar(states,s[0])
            s = s[1:]
        return self._end in states and s == ''

    def __str__(self):
        return '<NFA id: {ident}, regex: {desc}>'.format(ident=id(self), desc=self.description)

    def _view_graph(self):
        """Generate a graph from the NFA, save to a file and view it

        `_view_graph` creates a graph representation of the NFA, which can
        be useful during development and debugging. The graph consists of
        states and edges rechable from the `_start` state. States are labelled
        with their individual identifiers - `_state_num` numbers. Edges are 
        labelled with their transition requirements. The graph is labeled with
        the NFA's description. The graph is saved to two files, textual and
        graphical (.png), and shown on screen.

        Files are saved in the `graphs` directory, with a filename created
        from the pattern `NFA_` + `id(self)`. This means that files in the
        `graphs` directory can be overwritten. All files in the `graphs`
        are considered temporary.

        This method depends on `graphviz` python package. Additionally, to
        render the graph `dot` executable from Graphviz program must be on
        system's path.
        """
        g = graphviz.Digraph(self.description, format='png', filename='graphs/NFA_'+str(id(self)))
        g.attr('node', shape='circle')
        states = NFA._get_all_reachable_states(self._start)
        for st in states:
            g.node(str(st._state_num))
            for e in st._edges:
                g.edge(str(st._state_num), str(e[1]._state_num), label=e[0] if e[0] else 'ε')
        g.body.append(r'label = "\n\n{}"'.format(self.description))
        g.body.append('fontsize=20')
        g.view()

    def _invalidate(self):
        """Invalidate a NFA object making it not suitable for any use.
        
        Any use of an invalid NFA object will result in raising
        an NFAInvalidError.
        """
        self._start = None
        self._end = None
        self._description = None

    @staticmethod
    def _get_all_reachable_states(state):
        """Return a set of states which are reachable from `state`

        Args:
        state (State): the state from which the search is performed

        Returns:
        A set of states connected to the state by any path.
        """
        states = set()
        temp = {state}
        while temp:
            st = temp.pop()
            states.add(st)
            temp |= set(map(lambda e: e[1], filter(lambda e: e[1] not in states, st._edges)))
        return states

    @staticmethod
    def _get_char_states(state, char):
        """Return a set of states connected to a `state` by an immediate edge
        labeled exactly with `char` string.

        Args:
        state (State): the state from which the search is performed
        char (str): the edge's label which filters the search

        Returns:
        A set of states connected to a `state` by an immediate edge labeled
        exactly with `char` string.
        """
        return set(map(lambda edge: edge[1], filter(lambda edge: edge[0]==char, state._edges)))

    @staticmethod
    def _moveEpsilon(in_to_check):
        """Return a set of states which are reachable from the input
        set of states by using epsilon-moves only.

        Note:
        Returned set includes also `in_to_check` states, which are reachable
        a priori.

        Args:
        in_to_check (set of States): the set of states from which the search
            is performed

        Returns:
        A set of states rechable from the input set by using epsilon-moves only.
        """
        to_check = in_to_check.copy()
        checked = set()
        while to_check:
            st = to_check.pop()
            checked.add(st)
            new = NFA._get_char_states(st,'')
            to_check = (to_check | new) - checked
        assert in_to_check <= checked
        return checked

    @staticmethod
    def _moveChar(in_to_check, char):
        """Return a set of states which are reachable from the input set
        of states by consuming `char` character without eplison-moves.

        Args:
        in_to_check (set of States): the set of states from which the search
            is performed
        char (str): a character to be consumed by the move

        Returns:
        A set of states which are reachable from the input set of states
        by consuming `char` character without eplison-moves.
        """
        return functools.reduce(
                lambda x, st: x | NFA._get_char_states(st,char) | NFA._get_char_states(st,'any'),
                in_to_check,
                set())

    @staticmethod
    def empty():
        """Return `empty` NFA which accepts only an empty string.

        `empty` NFA is described as regular expression `\E`, which imitates
        epsilon letter, unavailable on Windows' console.

        Returned NFA object is valid.

        Returns:
        A valid NFA which accepts only an empty string.
        """
        n = NFA(State(),State())
        n._start.add('',n._end)
        n._description = r'\E'
        return n

    @staticmethod
    def symbol(a):
        """Return a NFA which accepts only literal character from parameter `a`.

        `symbol` NFA is described as regular expression by its character `a`,
        but the character in the description might be escaped using backslash
        `\\` if it is one of the special characters.
        (see rejit.regex.special_chars)

        Returned NFA object is valid.

        Args:
        a (str): A literal character which will be the only accepted one.

        Returns:
        A valid NFA which accepts only literal character from parameter `a`.
        """
        n = NFA(State(),State())
        n._start.add(a,n._end)
        n._description = escape_symbol(a)
        return n

    @staticmethod
    def any():
        """Return a NFA which accepts any single character.

        `any` NFA is described as regular expression `.` (period).

        Returned NFA object is valid.

        Returns:
        A valid NFA which accepts any single character.
        """
        n = NFA(State(),State())
        n._start.add('any',n._end)
        n._description = '.'
        return n

    @staticmethod
    def none():
        """Return a NFA which accepts empty set.

        `none` NFA doesn't accept any input, it returns `False` for every
        possible string passed to `accept`. `none` NFA is described as regular
        expression `[]` which means empty set of characters.

        Returned NFA object is valid.

        Returns:
        A valid NFA which accepts empty set.
        """
        n = NFA(State(),State()) 
        n._description = '[]'
        return n

    @staticmethod
    def char_set(char_list, description):
        """Return a NFA which accepts one character from a set.

        `char_set` NFA accepts a string which comprises exactly one character
        from a set of character literals. Character set is passed by a
        `char_list` - list of str, which allows duplicates. Duplicates don't
        change the behavior of the NFA, but result in creation of unnecessary
        states and edges in the NFA, and thus it is discouraged.

        `char_list` can be empty. Returned NFA is equivalent to `none` NFA.

        `char_set` is also passed a `description` parameter, which is used
        as a description of the NFA. The external description is used because
        any description created knowing only `char_list` could be misleading.
        Example: for a regular expression `[a-e]` user passes a list
        `['a','b','c','d','e']`, but `char_set` doesn't know whether user had
        `[a-e]` or `[abcde]` in mind. Therefore user has to pass the expected
        description.

        Returned NFA object is valid.

        Warning:
        This method is likely to change in future versions.

        Args:
        char_list (list of str): A list of character literals one of which
            should be accepted. Allows duplicates. Can be empty.
        description (str): A regular expression description for the NFA.
            Due to its limitations, `char_set` can't reconstruct the expected
            description from `char_list` only.

        Returns:
        A NFA which accepts one character from a set.
        """
        # Empty set results in `none` NFA, as in `union_many`
        n = NFA.union_many(list(map(NFA.symbol, char_list)))
        n._description = description
        return n

    @staticmethod
    def union(s,t):
        """Combine NFAs into one which accepts a sum of both languages        
        
        `union` constructs a new NFA object from `s` and `t` parameters. NFA's
        accepted language is a sum of accepted languages of `s` and `t`. In terms
        of regular expressions the NFA represents a union of regular expressions 
        represented by `s` and `t`, what would be written as `s|t`.

        Both arguments should be different valid NFA objects. Both are invalidated
        if the method successfully completes. No NFA is modified if an exception
        was raised.

        Returned NFA object is valid.

        Raises:
        NFAInvalidError: if either `s` or `t` is invalid. The valid one is
            not modified.
        NFAArgumentError: if `s` and `t` are the same object. The object is not
            modified.

        Args:
        s (NFA): a part of the union. Invalidated on success.
        t (NFA): a part of the union. Invalidated on success.

        Returns:
        A valid NFA which accepts a sum of `s` and `t` languages
        """
        if not s.valid or not t.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        if s is t:
            raise NFAArgumentError("Can't use the same object for both parameters")
        n = NFA(State(),State())
        n._start.add('',s._start)
        n._start.add('',t._start)
        s._end.add('',n._end)
        t._end.add('',n._end)
        n._description = '('+s._description+'|'+t._description+')'
        s._invalidate()
        t._invalidate()
        return n

    @staticmethod
    def concat(s,t):
        """Combine NFAs into one which accepts a concatenation of both languages

        `concat` constructs a new NFA object from `s` and `t` parameters. NFA's
        accepted language is a concatenation of accepted languages of `s` and
        `t`. A concatenation of languages contains concatenations of every
        possible pair of words, where the first word in the pair is from `s`
        language and the second word is from `t` language. In terms of regular
        expressions the NFA represents a concatenation of regular expressions 
        represented by `s` and `t`, what would be written as `st`.

        Both arguments should be different valid NFA objects. Both are invalidated
        if the method successfully completes. No NFA is modified if an exception
        was raised.

        Returned NFA object is valid.

        Raises:
        NFAInvalidError: if either `s` or `t` is invalid. The valid one is
            not modified.
        NFAArgumentError: if `s` and `t` are the same object. The object is not
            modified.

        Args:
        s (NFA): a part of the concatenation. Invalidated on success.
        t (NFA): a part of the concatenation. Invalidated on success.

        Returns:
        A valid NFA which accepts a concatenation of `s` and `t` languages
        """
        if not s.valid or not t.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        if s is t:
            raise NFAArgumentError("Can't use the same object for both parameters")
        n = NFA(s._start,t._end)
        s._end.add('',t._start)
        n._description = s._description+t._description
        s._invalidate()
        t._invalidate()
        return n

    @staticmethod
    def kleene(s):
        """Construct a NFA which accepts a Kleene star of a language

        `kleene` constructs a new NFA object from `s` parameter. NFA's accepted
        language is a Kleene star of accepted language of `s`. A Kleene star of
        a language contains every number of concatenations of any word from the
        language. Each word can be different, and concatenation of zero words
        is also allowed. In terms of regular expressions the NFA represents
        a Kleene star of regular expression represented by `s`, what whould be
        written as `s*`.

        `kleene` argument should be a valid NFA object. The NFA is invalidated
        if the method successfully completes. The NFA is not modified if an 
        exception is raised.

        Returned NFA object is valid.

        Raises:
        NFAInvalidError: if `s` is invalid.

        Args:
        s (NFA): NFA which Kleene star is constructed. Invalidated on success.

        Returns:
        A valid NFA which accepts a Kleene star of `s` language
        """
        if not s.valid:
            raise NFAInvalidError('Trying to use invalid NFA object')
        q = State()
        f = State()
        q.add('',s._start)
        q.add('',f)
        s._end.add('',s._start)
        s._end.add('',f)
        n = NFA(q,f)
        n._description = '('+s._description+')*'
        s._invalidate()
        return n

    @staticmethod
    def kleene_plus(s):
        """Construct a NFA which accepts a Kleene plus of a language

        `kleene_plus` constructs a new NFA object from `s` parameter. NFA's
        accepted language is a Kleene plus of accepted language of `s`. A
        Kleene plus of a language contains one or more concatenations of any
        word from the language. Each word can be different. In terms of
        regular expressions the NFA represents a Kleene plus of regular
        expression represented by `s`, what whould be written as `s+`.

        `kleene_plus` argument should be a valid NFA object. The NFA is
        invalidated if the method successfully completes. The NFA is not
        modified if an exception is raised.

        Returned NFA object is valid.

        Raises:
        NFAInvalidError: if `s` is invalid.

        Args:
        s (NFA): NFA which Kleene plus is constructed. Invalidated on success.

        Returns:
        A valid NFA which accepts a Kleene plus of `s` language
        """
        # validation and invalidation of `s` is performed inside `concat`
        s_copy = copy.deepcopy(s)
        s_description = s._description
        n = NFA.concat(s,NFA.kleene(s_copy))
        n._description = '('+s_description+')+'
        return n

    @staticmethod
    def zero_or_one(s):
        """Construct a NFA which accepts a union of a language and an empty one

        `zero_or_one` constructs a new NFA object from `s` parameter. NFA's
        accepted language is a union of accepted language of `s` and an empty
        language. This means that the NFA will accept every word from `s`
        language or an empty string. In terms of regular expressions the NFA
        represents `s?`, where `s` is a regular expression representing
        `s` NFA.

        `zero_or_one` argument should be a valid NFA object. The NFA is
        invalidated if the method successfully completes. The NFA is not
        modified if an exception is raised.

        Returned NFA object is valid.

        Raises:
        NFAInvalidError: if `s` is invalid.

        Args:
        s (NFA): NFA which union with empty language is constructed.
            Invalidated on success.

        Returns:
        A valid NFA which accepts a union of `s` language and an empty language
        """
        # validation and invalidation of `s` is performed inside `union`
        s_description = s._description
        n = NFA.union(s,NFA.empty())
        n._description = '('+s_description+')?'
        return n
    
    @staticmethod
    def concat_many(concat_list):
        """Combine NFAs into one which accepts a concatenation of a list of
        languages

        `concat_many` constructs a new NFA object from all the objects in the
        list. NFA's accepted language is a concatenation of all languages.
        A concatenation of many languages contains concatenations of every
        possible tuple of words, where there is a word from every language and
        the words are in the same order as languages in the list. In terms of
        regular expressions the NFA represents a concatenation of regular
        expressions from the list [a,b,c, ... ,z], what would be written as
        `abc...z`.

        The list can be empty. Concatenation of zero languages is an empty
        string language, which contains only an empty string. Equivalent of
        `empty`.

        All arguments should be different valid NFA objects. All NFAs are
        invalidated if the method successfully completes. No NFA is modified if
        an exception was raised.

        Returned NFA object is valid.

        Note:
        Using this method is almost equivalent to chaining calls to `concat`. 
        This method serves only as a better interface. It also invalidates all
        objects in a list or none of them.

        Raises:
        NFAInvalidError: if any NFA in `concat_list` is invalid. Valid ones are
            not modifed.
        NFAArgumentError: if there are two or more duplicate NFA references in 
            `concat_list`. The objects are not modified.

        Args:
        concat_list (list of NFA): a list of concatenated NFAs. All are
            invalidated on success.

        Returns:
        A valid NFA which accepts a concatenation of languages in a list.
        """
        # Validation of elements of `concat_list` is performed also outside of
        # `concat`, because `concat_many` shouldn't invalidate part of
        # `concat_list` before reaching an invalid NFA.
        # Invalidation of elements of `concat_list` is performed inside
        # `concat`. This algorithm sets good description without intervention. 
        if not concat_list:
            return NFA.empty()
        if not all(map(lambda x: x.valid, concat_list)):
            raise NFAInvalidError('Trying to use invalid NFA object')
        if len(set(concat_list)) != len(concat_list):
            raise NFAArgumentError("Can't use the same object more than once in the concat_list")
        return functools.reduce(
                lambda acc, x: NFA.concat(acc,x),
                concat_list
            )

    @staticmethod
    def union_many(union_list):
        """Combine NFAs into one which accepts a union of a list of languages

        `union_many` constructs a new NFA object from all the objects in the
        list. NFA's accepted language is a sum of all languages. A sum of all
        languages contains every word from these languages. In terms of regular
        expressions the NFA represents a union of regular expressions from the
        list [a,b,c ... ,z], what would be written as `a|b|c| ... |z`.

        The list can be empty. Union of zero languages is an empty set language,
        which doesn't contain any string. Equivalent of `none`.

        All arguments should be different valid NFA objects. All NFAs are
        invalidated if the method successfully completes. No NFA is modified if
        an exception was raised.

        Returned NFA object is valid.

        Note:
        Using this method is preferred over chaining calls to `union`, because
        it results in a better NFA's description and a leaner NFA object, which
        uses less states and edges internally.

        Raises:
        NFAInvalidError: if any NFA in `union_list` is invalid. Valid ones are
            not modifed.
        NFAArgumentError: if there are two or more duplicate NFA references in 
            `union_list`. The objects are not modified.

        Args:
        union_list (list of NFA): a list of parts of the union. All are
            invalidated on success.

        Returns:
        A valid NFA which accepts a union of languages in a list.
        """
        if not union_list:
            return NFA.none()
        if not all(map(lambda x: x.valid, union_list)):
            raise NFAInvalidError('Trying to use invalid NFA object')
        if len(set(union_list)) != len(union_list):
            raise NFAArgumentError("Can't use the same object more than once in the union_list")
        n = NFA(State(),State())
        for u in union_list:
            n._start.add('',u._start)
            u._end.add('',n._end)
        n._description = '(' + functools.reduce(lambda acc, x: acc+"|"+x.description,union_list[1:],union_list[0].description) + ')'
        for x in union_list:
            x._invalidate()
        return n

class DFA:
    def __init__(self, nfa):
        # all nfa's states reachable from the start state
        nfa_states = frozenset(NFA._get_all_reachable_states(nfa._start))

        # nfa described without use of epsilon edges.
        # nfa_state_edges is constructed as {state_num: {char: {state_num}}}
        # which maps state_num to dictionaries which map each char to 
        # a set of state_nums which are reachable from the state using that char
        nfa_state_edges = {
                st._state_num: DFA._nfa_char2statenum_set(st)
                for st in nfa_states
            }

        # newstates is an early representation of the constructed DFA
        # newstates is constructed as {multiname: {char: {state_num}}} where
        # multiname key is a string which describes a set of states from the nfa
        # and it points to a dictionary which map each char to a set of 
        # state_nums which are reachable from the set of states using that char.
        # newstates is initialized with multistates which correspond to 
        # the nfa's states.
        newstates = {DFA._multistate_name({num}): c2s for num,c2s in nfa_state_edges.items()}

        # m2ss dict maps multiname to a corresponding state_num set
        m2ss = {DFA._multistate_name({num}): {num} for num in nfa_state_edges}

        # toadd contains sets of state_nums which are multistates to be added to newstates
        toadd = [s for st,d in nfa_state_edges.items() for char,s in d.items()]

        while toadd:
            states = toadd.pop()
            name = DFA._multistate_name(states)
            # check if they are already added, if not create a multistate by merging singlestates
            if name not in newstates:
                _, c2s = DFA._merge_states(states,nfa_state_edges)
                newstates[name] = c2s
                m2ss[name] = states
                # merging multistate could create new multistates to add 
                for char,s in c2s.items():
                    toadd.append(s)

        # convert newstates to {multiname:{char:multiname}} dict
        for st,c2s in newstates.items():
            for c,s in c2s.items():
                c2s[c] = DFA._multistate_name(s)

        # end states are multistates which contain nfa._end state ...
        end_states = set(filter(lambda st: nfa._end._state_num in m2ss[st], newstates))
        # ... and singlestates from nfa which can reach nfa._end with epsilon-moves
        end_states |= set(map(
            lambda st: DFA._multistate_name({st._state_num}), 
            filter(lambda st: nfa._end in NFA._moveEpsilon({st}), nfa_states)))

        # save relevant data
        # start state
        self._start = DFA._multistate_name({nfa._start._state_num})
        # DFA state/edge dict
        self._states_edges = newstates
        # set of accepting states
        self._end_states = frozenset(end_states)

    def accept(self,s):
        state = self._start
        while s:
            # check for char edge from current state
            if s[0] in self._states_edges[state]:
                state = self._states_edges[state][s[0]]
                s = s[1:]
            # check also for `any` edge, but only after char edges
            elif 'any' in self._states_edges[state]:
                state = self._states_edges[state]['any']
                s = s[1:]
            # rejecting state - no edge could match s[0]
            else:
                return False
        return state in self._end_states

    @staticmethod
    def _nfa_reachable_noneps_edges(state):
        return filter(lambda e: e[0], functools.reduce(lambda x,y: x+y,[s._edges for s in NFA._moveEpsilon({state})]))

    @staticmethod
    def _nfa_char2statenum_set(st):
        char2statenum_set = collections.defaultdict(lambda: set())
        # gather all non-epsilon edges reachable from `st`
        # for each char in edges find all states reachable using that char
        for e in DFA._nfa_reachable_noneps_edges(st):
            char2statenum_set[e[0]] |= {e[1]._state_num} | set(map(lambda x: x._state_num, NFA._moveEpsilon({e[1]})))
        # if `any` edge reachable, than all other chars can use it too
        if 'any' in char2statenum_set:
            for char in char2statenum_set:
                char2statenum_set[char] |= char2statenum_set['any']
        return char2statenum_set

    @staticmethod
    def _multistate_name(states):
        return functools.reduce(lambda acc, x: acc + ',' + x, sorted(map(str,states)))

    @staticmethod
    def _merge_states(merged_states,nfa_states_edges):
        name = DFA._multistate_name(merged_states)
        char2statenum_set = collections.defaultdict(lambda: set())
        for st in merged_states:
            merged_c2s = nfa_states_edges[st]
            for c in merged_c2s:
                char2statenum_set[c] |= merged_c2s[c]
            if 'any' in char2statenum_set:
                for char in char2statenum_set:
                    char2statenum_set[char] |= char2statenum_set['any']
        return name, char2statenum_set

class Regex:
    def __init__(self, pattern=None):
        if pattern is not None:
            self.pattern = pattern
            self._ast = self._parse(pattern)
            self._final_ast = self._transform(self._ast)
            self._matcher = self._compile(self._final_ast)

    def accept(self, s):
        return self._matcher.accept(s)

    def get_NFA_description(self):
        return self._matcher.description

    def _getchar(self):
        if self._input:
            self._last_char = self._input[0]
            self._input = self._input[1:]
        else:
            self._last_char = ''

    def _parse(self, pattern):
        self._input = pattern
        self._last_char = ''
        self._getchar()
        if not self._last_char:
            return ('empty',)
        else:
            ast = self._unionRE()
            if self._last_char == ')':
                raise RegexParseError('Unmatched parentheses')
            return ast

    def _compile(self, ast):
        if ast[0] == 'concat':
            return NFA.concat_many(list(map(self._compile, ast[1])))
        elif ast[0] == 'union':
            return NFA.union_many(list(map(self._compile, ast[1])))
        elif ast[0] == 'kleene-star':
            return NFA.kleene(self._compile(ast[1]))
        elif ast[0] == 'kleene-plus':
            return NFA.kleene_plus(self._compile(ast[1]))
        elif ast[0] == 'zero-or-one':
            return NFA.zero_or_one(self._compile(ast[1]))
        elif ast[0] == 'any':
            return NFA.any()
        elif ast[0] == 'empty':
            return NFA.empty()
        elif ast[0] == 'symbol':
            return NFA.symbol(ast[1])
        elif ast[0] == 'set':
            return NFA.char_set(ast[1],ast[2])
        raise RegexCompilationError("Unknown AST node: {node}".format(node=ast))

    def _transform(self, input_ast):
        return functools.reduce(
            lambda ast, transform: transform(ast),
            [
                functools.partial(self._flatten_nodes,'concat'),
                functools.partial(self._flatten_nodes,'union'),
            ],
            input_ast)

    def _flatten_nodes(self, node_type, ast):
        # for a list of nodes return a list of transformed nodes
        if isinstance(ast, list):
            return list(map(functools.partial(self._flatten_nodes,node_type), ast))
        # for leaf nodes return a copy 
        if ast[0] in ['any','empty','symbol','set']:
            return copy.deepcopy(ast)
        # for nodes with children return node with its children transformed by `_flatten_nodes`
            # for tuple based node ast[1:] are children
            # ('type', _flatten(child1), _flatten(child2))
            # for list based node ast[1] is a list of children
            # ('type', [ _flatten(child1), _flatten(child2)]
        if ast[0] != node_type:
            return tuple([ast[0]] + list(map(functools.partial(self._flatten_nodes,node_type), ast[1:])))
        # for `concat` node transform children with `flatten_nodes`
        left = self._flatten_nodes(node_type,ast[1][0])
        right = self._flatten_nodes(node_type,ast[1][1])
        # `concat` node list is created from lists extracted from children `concat` nodes, or by simply inserting other nodes
        node_list = (left[1] if left[0] == node_type else [left]) + (right[1] if right[0] == node_type else [right])
        return (node_type , node_list)

    def _unionRE(self):
        ast1 = self._concatRE()
        if self._last_char == '|':
            self._getchar() # '|'
            ast2 = self._unionRE()
            return ('union',[ast1,ast2])
        return ast1

    def _concatRE(self):
        ast1 = self._kleeneRE()
        if self._last_char and self._last_char not in '|)':
            ast2 = self._concatRE()
            return ('concat', [ast1, ast2])
        return ast1

    def _kleeneRE(self):
        ast = self._elementaryRE()
        if self._last_char == '*':
            self._getchar() # '*'
            return ('kleene-star', ast)
        elif self._last_char == '+':
            self._getchar() # '+'
            return ('kleene-plus', ast)
        elif self._last_char == '?':
            self._getchar() # '?'
            return ('zero-or-one', ast)
        else:
            return ast

    def _elementaryRE(self):
        if self._last_char == '(':
            self._getchar()
            ast_paren = self._unionRE()
            if self._last_char != ')':
                raise RegexParseError('Expected ")", got {}'.format(self._last_char))
            self._getchar() # ')'
            return ast_paren
        elif self._last_char == '.':
            self._getchar() # '.'
            return ('any',)
        elif self._last_char == '[':
            return self._parse_charset()
        elif self._last_char == '':
            raise RegexParseError('Unexpected end of the pattern')
        else:
            return self._symbolRE()

    def _symbolRE(self):
        if self._last_char in special_chars and self._last_char != '\\':
            raise RegexParseError('Unescaped special character "{}" can\'t be used here'.format(self._last_char))
        if self._last_char == "\\":
            self._getchar() # '\'
        if not self._last_char:
            raise RegexParseError('Unexpected end of the pattern after an escape character "\\"')
        ast = ('symbol', self._last_char)
        self._getchar()
        return ast

    def _parse_charset(self):
        self._getchar() # '['
        symbol_list = []
        charset_desc = '['
        if self._last_char == '^':
            raise RegexParseError('Negative character set not supported')
        while self._last_char and self._last_char != ']':
            symbol1 = self._last_char
            self._getchar()
            if self._last_char == '-':
                self._getchar() # '-'
                if self._last_char:
                    charset_desc += symbol1 + '-'
                    symbol_list += list(Regex.char_range(symbol1,self._last_char))
                    charset_desc += self._last_char
                    self._getchar()
                else:
                    raise RegexParseError('Expected a symbol after "-" but the end of the pattern reached')
            else:
                charset_desc += symbol1
                symbol_list.append(symbol1)
        if self._last_char != ']':
            raise RegexParseError('Expected "]" but end of the pattern reached'.format(self._last_char))
        self._getchar() # ']'
        charset_desc += ']'
        ast = ('set',symbol_list,charset_desc)
        return ast

    @staticmethod
    def char_range(c1, c2):
        """Generates the characters from `c1` to `c2`, inclusive."""
        for c in range(ord(c1), ord(c2)+1):
            yield chr(c)

def escape_symbol(symbol):
    return "\\" + symbol if symbol in special_chars else symbol

supported_chars = string.ascii_letters + string.digits + '`~!@#$%&=_{}:;"\'<>,/'
special_chars = '\\^*()-+[]|?.'

