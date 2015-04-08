# rejit
`rejit` is a simple regular expression just-in-time compiler for Python. The
project is intended for educational and experimental purposes.

## Description
`rejit` supports regular expressions, which describe regular languages, as in
[formal language theory](https://en.wikipedia.org/wiki/Regular_expression#Formal_language_theory).
This means that `rejit` lacks advanced regexp features like backreferences,
because of too low expressive power. The upside of this is that `rejit` can use
[deterministic finite automata](https://en.wikipedia.org/wiki/Deterministic_finite_automaton),
which can accept input in linear time.

Rough plan to JIT compile regular expressions:
* [x] parse regexp string to an AST
* [x] transform the AST (optimization, simplification)
* [x] construct a [nondeterministic finite automaton](http://en.wikipedia.org/wiki/Nondeterministic_finite_automaton) from the AST
* [ ] convert the NFA to a DFA
* [ ] compile the DFA to some intermediate representation
* [ ] compile the IR to native code
* [ ] pack native code in an easy to call wrapper

## Supported features
`rejit` supports the following regexp features:
* union - `abc|def`
* concatenation - `abcd`
* Kleene star - `a*`
* Kleene plus - `b+`
* question mark operator - `c?`
* grouping - `(a|b)c`
* any character - `.`
* character set (including character ranges) - `[a-zXYZ]`
* escaped special characters - `\.`

Currently `rejit` can only decide whether a string exactly matches a regexp.
There is no search support.

## Usage example
Regular expressions in `rejit` can be used to check if a string looks like a
number. Here's a pretty bad attempt:
```
>>> import rejit.regex as re
>>> regex = re.Regex(r'(\-?[0-9]*(\.[0-9]+)?')
>>> regex.accept('not a number')
False
>>> regex.accept('42')
True
>>> regex.accept('-1.0')
True
>>> regex.accept('.999')
True
>>> regex.accept('-.')
False
>>> regex.accept('-')
True
# ugh, a lone minus is accepted, but that's actually the regex' fault, not a bug
```

## Documentation
`rejit`'s classes are documented in docstrings. Automatic documentation
generation isn't set up yet, so no cute html docs to browse. Related issue
[#26](https://github.com/ziowk/rejit/issues/26)

