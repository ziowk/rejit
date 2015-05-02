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
* [x] convert the NFA to a DFA
* [x] compile the DFA to some intermediate representation
* [x] compile the IR to native code
* [x] pack native code in an easy to call wrapper

## Supported features
### Regular expression features
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

### Available regex matchers
`rejit` provides three types of matchers:
* NFA-based matcher - default, created implicitly when creating a `Regex` object
* DFA-based matcher - a linear time matcher, created with `compile_to_DFA()`
* JIT compiled matcher - a linear time matcher, compiled to x86 machine code.
Created with `compile_to_x86()`

## Usage example
Regular expressions in `rejit` can be used to check if a string looks like a
number. Here's a pretty bad attempt:
```
>>> import rejit.regex as re
>>> regex = re.Regex(r'\-?[0-9]*(\.[0-9]+)?')
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
>>> regex.compile_to_DFA()
# `regex` will now use a DFA-based matcher, which should work faster
>>> regex.accept('-1000.00')
True
>>> regex.compile_to_x86()
# `regex` will now use a JIT compiled matcher, which should work even faster than a DFA one
>>> regex.accept('999.999')
True
>>> regex.accept('0xFF')
False
```

## Installation
`rejit` package is distributed by source. Clone the repository:
```
git clone git@github.com:ziowk/rejit.git
cd rejit
```

Install the package with `setuptools`:
```
python setup.py install
```

Or install the development version with `pip`:
```
pip install -e .[dev]
```

And run tests with `py.test` (installed with the development version):
```
py.test
```

## Requirements
Supports Python 3 only.

JIT compilation available only on 32bit Python running on Windows.
See [#79](https://github.com/ziowk/rejit/issues/79) [#80](https://github.com/ziowk/rejit/issues/80)

No external dependencies.

## Documentation
`rejit`'s classes are documented in docstrings. Automatic documentation
generation isn't set up yet, so no cute html docs to browse. Related issue
[#26](https://github.com/ziowk/rejit/issues/26)

## License
`rejit` is licensed under the terms of the GPLv2 license.

For more information see [LICENSE](LICENSE)

