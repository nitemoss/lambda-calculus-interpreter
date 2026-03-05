#set document(title: "Extended Lambda Calculus Interpreter", author: "")
#set page(margin: 2.5cm)
#set text(font: "New Computer Modern", size: 11pt)
#set heading(numbering: "1.1.")
#set par(justify: true)

// Diagonal (solidus) fraction: N⁄x with N top-left, x bottom-right
#let sfrac(num, den) = $attach(slash, tl: num, br: den)$

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
M ::= x | lambda x.M | M N
$

where $x$ is a variable, $lambda x.M$ is an abstraction (a function that takes
$x$ and returns $M$), and $M N$ is application (the function $M$ applied to
argument $N$). Reduction is governed by the $beta$-reduction rule:

$
(lambda x.M) N ->_beta M[sfrac(N,x)]
$

On top of this core the interpreter provides:

- *Let bindings* as syntactic sugar over lambda abstractions.
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

This representation uses named variables. It
is simple to read and print, at the cost of requiring $alpha$-renaming during
substitution to avoid variable capture.


== Name Supply

A global integer counter provides fresh variable names. When $alpha$-renaming
is needed, a new name of the form `x_N` (where `N` is the counter value) is
generated and the counter is incremented.

= Algorithms

== Free Variables

The set of free variables of a term is computed recursively:

$
"fv"(x) = {x} \
"fv"(lambda x.M) = "fv"(M) - {x} \
"fv"(M N) = "fv"(M) union "fv"(N)
$

For extension nodes (`BinOp`, `If`, `Lit`), free variables are the union of
free variables in all sub-terms.

== Substitution

Capture-avoiding substitution $M[sfrac(N,x)]$ (replace all free occurrences of $x$ in
$M$ by $N$) follows the standard rules:

$
x[sfrac(N,x)] = N \
y[sfrac(N,x)] = y, quad y != x \
(lambda x.M)[sfrac(N,x)] = lambda x.M \
(lambda y.M)[sfrac(N,x)] = lambda y.(M[sfrac(N,x)]), quad y in.not "fv"(N) \
(lambda y.M)[sfrac(N,x)] = lambda y'.(M[sfrac(y',y)][sfrac(N,x)]), quad y in "fv"(N)
$

where $y'$ is a fresh name. The last rule performs $alpha$-renaming to prevent
the free variable $y$ in $N$ from becoming bound.

== Reduction Strategy

The interpreter implements *normal-order* (outermost-leftmost) reduction. This
strategy reduces the leftmost, outermost redex first and is guaranteed to find
a normal form whenever one exists. It is defined by the following priority:

1. If the term is a $beta$-redex $(lambda x.M) N$, fire it immediately.
2. Otherwise, try to reduce the function position of an application.
3. Otherwise, try to reduce the argument position of an application.
4. Otherwise, try to reduce under the lambda binder.

A single call to `reduce(term)` returns either `(reduced_term, True)` (one
step was taken) or `(term, False)` (the term is in normal form). The full
evaluator loops until no step fires or a configurable step limit is reached
(default 10 000 steps), at which point it raises a `NonTerminatingError`.

Built-in arithmetic and conditionals are handled as _delta reductions_: when
both operands of a `BinOp` are `Lit` nodes, the operation is computed directly
in Python and the node is replaced by the resulting `Lit`. Similarly, `If`
reduces to `then_` or `else_` as soon as `cond` is a boolean literal.

= Syntactic Sugar

The parser accepts a richer surface language and desugars it to core terms
before evaluation.

== Let Bindings

```
let x = t1 in t2      -->   (\x. t2) t1
```

This is pure syntactic sugar: the parser rewrites it to a lambda application
before evaluation.

== Church Numeral Sugar

Writing `#n` for a non-negative integer $n$ desugars to the Church numeral:

$
c_n = lambda f.lambda x. f^n(x)
$

So `#0` = $lambda f.lambda x.x$, `#1` = $lambda f.lambda x.(f x)$, `#2` = $lambda f.lambda x.f(f x)$, and so on.

== Multi-Argument Lambdas

The parser accepts `λx y z. t` as sugar for `λx. λy. λz. t` (currying).

= User Interface

== REPL

Running `python interpreter.py` starts an interactive read-eval-print loop:

```
λ> (\x. x x) (\x. x)
Step 1: (\x. x x) (\x. x)
Step 2: (\x. x) (\x. x)
Step 3: \x. x
Result: \x. x
```

Special REPL commands:
- `:step <term>` — evaluate one step at a time, waiting for Enter.
- `:let <name> = <term>` — bind a name in the REPL environment.
- `:load <file>` — load and execute a `.lc` file.
- `:quit` — exit.

== File Mode

```
python interpreter.py program.lc
```

Reads definitions and expressions from the file and prints results to stdout.
Definitions have the form `name = term` and are available to all subsequent
expressions in the file.

= Evaluation Examples

== Identity Function

```
(\x. x) y
```

$(lambda x.x) y ->_beta y$

One step to normal form.

== Self-Application

```
(\x. x x) (\y. y)
```

$(lambda x.x x)(lambda y.y) ->_beta (lambda y.y)(lambda y.y) ->_beta lambda y.y$

Two steps. The second step fires because the outermost redex is now $(lambda y.y)(lambda y.y)$.

== Constant Function

```
(\x. \y. x) true false
```

$(lambda x.lambda y.x) "true" "false" ->_beta (lambda y."true") "false" ->_beta "true"$

Two steps. The outer lambda binds `x` to `true`, then the inner lambda discards `y` and returns `true`.

== Boolean AND via Conditionals

```
if true then (if false then true else false) else false
```

$->_beta$ `if false then true else false` $->_beta$ `false`

The outer `if` selects the `then` branch, which itself reduces to `false`.

== Arithmetic

```
(2 + 3) * (10 - 4)
```

$(2+3)*(10-4) ->_beta 5*(10-4) ->_beta 5*6 ->_beta 30$

Each `BinOp` fires as a delta reduction once both operands are literals.

== Let Binding

```
let double = \n. n + n in double 7
```

Desugars to `(\double. double 7) (\n. n + n)`, then:

$(lambda n.n+n) 7 ->_beta 7+7 ->_beta 14$

== Comparison and Conditional

```
let x = 5 in if x < 10 then x * 2 else x
```

After substituting `x = 5`:
`if 5 < 10 then 5 * 2 else 5` $->_beta$ `if true then 5 * 2 else 5` $->_beta 5*2 ->_beta 10$

== Church Numeral Addition

Using the standard `add` combinator and Church numerals:

```
let add = \m. \n. \f. \x. m f (n f x) in
add #2 #3
```

Evaluates in normal order to the Church numeral $c_5 = lambda f.lambda x.f(f(f(f(f x))))$.

= Future Work

To grow the interpreter into a practical functional programming environment,
the following extensions are most important:

+ *Recursive definitions via the Y combinator* — the current `let` binding is non-recursive. Adding `letrec` desugared to a Y-combinator application ($Y = lambda f.(lambda x.f(x x))(lambda x.f(x x))$) would allow writing recursive functions such as factorial directly in the surface language.

+ *Type inference* — adding Hindley-Milner type inference would catch type errors before runtime and enable typed polymorphism, the foundation of languages like Haskell and OCaml.

+ *Algebraic data types and pattern matching* — user-defined `data` types with constructor and destructor syntax would replace Church encodings with native structures.

+ *Lazy evaluation with sharing (call-by-need)* — the current normal-order strategy re-evaluates arguments each time they are used. Sharing via a thunk graph would make recursion and infinite data structures efficient.

+ *A module system* — named top-level definitions, imports, and a standard prelude (lists, pairs, natural numbers) would allow programs of realistic size to be written.

+ *Proper tail-call optimisation* — Python's call stack limits deeply recursive evaluations. Trampolining or continuation-passing style would remove this constraint.

+ *A garbage-collected term graph* — replacing the tree-based AST with a shared graph representation would enable efficient reduction of terms with large shared sub-expressions.

+ *Syntax extensions* — list literals, string literals, do-notation, and operator sections would make the surface language substantially more readable.

= Conclusion

The interpreter demonstrates the core mechanics of lambda calculus reduction —
free-variable analysis, capture-avoiding substitution, and normal-order
evaluation — in approximately 500 lines of well-commented Python. The
extensions (arithmetic, booleans, let bindings, Church numerals) show how a
minimal formal calculus can be grown into a usable evaluator. The future work
outlined above maps a clear path from this prototype toward a full functional
language implementation.
