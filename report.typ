#set document(title: "Extended Lambda Calculus Interpreter", author: "")
#set page(margin: 2.5cm)
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1.")
#set par(justify: true)

#align(center)[
  #text(17pt, weight: "bold")[Extended Lambda Calculus Interpreter]
  #v(0.4em)
  #text(12pt)[Logic and Computation — Task 1]
  #v(0.2em)
  #text(10pt, fill: gray)[#datetime.today().display("[month repr:long] [year]")]
]

#v(1em)
#outline(indent: 1.5em)
#pagebreak()

= Introduction

This report describes the design, implementation, and evaluation of an extended
lambda calculus interpreter written in Python. The interpreter covers the
untyped lambda calculus and adds a set of syntactic and semantic extensions
that make it practical to write and evaluate non-trivial functional expressions
without encoding everything by hand.

The core language is the standard untyped lambda calculus with three term
forms:

$
t ::= x quad | quad lambda x . t quad | quad t space t
$

where $x$ ranges over variable names, $lambda x . t$ is an abstraction
(function), and $t space t$ is application (function call). Reduction is
governed by the $beta$-reduction rule:

$
(lambda x . t_1) space t_2 quad arrow.r_beta quad t_1 [x := t_2]
$

On top of this core the interpreter provides:

- *Let / letrec bindings* as syntactic sugar over lambda abstractions.
- *Built-in integer literals* and *arithmetic operators* (`+`, `-`, `*`, `==`, `<`).
- *Boolean literals* (`true`, `false`) and conditional expressions (`if`/`then`/`else`).
- *Church numeral sugar* — the user can write `#3` to obtain the Church encoding of 3.
- *An interactive REPL* and *file-based batch evaluation*, both printing step-by-step traces.

= Data Structures

== Term Representation

Lambda terms are represented as a recursive algebraic structure. Each node in
the abstract syntax tree (AST) is an instance of one of the following Python
dataclasses:

```python
@dataclass
class Var:
    name: str            # variable reference

@dataclass
class Lam:
    param: str           # bound variable name
    body: Term           # body expression

@dataclass
class App:
    func: Term           # function position
    arg:  Term           # argument position

# Extensions
@dataclass
class Lit:
    value: int | bool    # integer or boolean literal

@dataclass
class BinOp:
    op:    str           # "+", "-", "*", "==", "<"
    left:  Term
    right: Term

@dataclass
class If:
    cond:  Term
    then_: Term
    else_: Term

Term = Var | Lam | App | Lit | BinOp | If
```

This representation is a standard _de Bruijn-free_ named representation. It is
simple to read and print, at the cost of requiring $alpha$-renaming during
substitution to avoid variable capture.


== Name Supply

A global integer counter provides fresh variable names. When $alpha$-renaming
is needed, a new name of the form `x_N` (where `N` is the counter value) is
generated and the counter is incremented. This is sufficient for a single
evaluation session; a more robust implementation would thread the supply
through a state monad or use a proper gensym table.

== Substitution

Capture-avoiding substitution $t[x := s]$ follows the standard rules:

$
x[x := s] &= s \
y[x := s] &= y quad (y eq.not x) \
(lambda x . t)[x := s] &= lambda x . t \
(lambda y . t)[x := s] &= lambda y . (t[x := s]) quad y in.not "fv"(s) \
(lambda y . t)[x := s] &= lambda y' . (t[y := y'][x := s]) quad y in "fv"(s)
$

