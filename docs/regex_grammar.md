# Regular expression grammar

## Description

This file describes regular expression grammar for all features which are to be supported.

Features:
* union - `abc|def`
* concatenation - `abcd`
* Kleene star - `a*`
* Kleene plus - `b+`
* question mark operator - `c?`
* grouping - `(a|b)c`
* any character - `.`
* character set (including character ranges) - `[a-zXYZ]`
* negative character set - `[^abc]`

Grammar is written in Backus–Naur Form.

## Grammar
```
<unionRE> ::= <concatRE> "|" <unionRE> | <concatRE>
<concatRE> ::= <kleeneRE> <concatRE> | <kleeneRE>
<kleeneRE> ::= <elementaryRE> "*" | <elementaryRE> "+" | <elementaryRE> "?" | <elementaryRE>
<elementaryRE> ::= <group> | <any> | <char> | <set>
<group> ::= "(" <unionRE> ")"
<any> ::= "."
<char> ::= "a" | "b" | ... | "z" | "A" | "B" | ... | "Z" | "0" | "1" | ... | "9"
<set> ::= <positive-set> | <negative-set>
<positive-set> ::= "[" <set-items> "]"
<negtive-set> ::= "[^" <set-items> "]"
<set-items> ::= <set-item> | <set-item> <set-items>
<set-item> ::= <range> | <char>
<range> ::= <char> "-" <char>
```

