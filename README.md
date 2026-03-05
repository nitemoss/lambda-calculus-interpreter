# Lambda Calculus Interpreter

An extended untyped lambda calculus interpreter with
beta reduction, arithmetic, booleans, conditionals, let bindings, Church
numerals, and an interactive REPL.

## Usage

### Interactive REPL

```
python main.py
```

```
Lambda Calculus Interpreter  (type :help for usage, :quit to exit)
λ> (\x. x) y
→  y
λ> (\x y. x) true false
→  true
λ> (3 + 4) * 2
→  14
```

### Run a file

```
python main.py program.lc
```

### Run a file with step trace

```
python main.py --trace program.lc
```

## REPL Commands

| Command | Description |
|---|---|
| `<term>` | evaluate an expression |
| `:let name = <term>` | define a named term for reuse |
| `:step <term>` | evaluate one step at a time |
| `:trace <term>` | evaluate and print every intermediate step |
| `:load <file>` | load and run a `.lc` file |
| `:env` | list all defined names |
| `:help` | show help |
| `:quit` | exit |

## Syntax

```
\x. body          lambda abstraction  (also λx. body)
\x y z. body      multiple parameters (sugar for nested lambdas)
f arg             application (left-associative: f a b = (f a) b)
let x = t1 in t2  let binding (sugar for (\x. t2) t1)
if c then t else f conditional
(x + 1)           arithmetic: + - * == <  (wrap in parentheses)
true  false       boolean literals
42                integer literal
#3                Church numeral (expands to λf. λx. f(f(f x)))
```

## Examples

### Beta reduction

```
λ> (\x. x) y
→  y

λ> (\x y. x) true false
→  true

λ> (\x. x x) (\y. y)
→  λy. y
```

### Arithmetic and comparison

```
λ> (2 + 3) * (10 - 4)
→  30

λ> (7 == 7)
→  true

λ> (3 < 10)
→  true
```

### Conditionals

```
λ> if (5 < 10) then 42 else 0
→  42

λ> if true then (if false then 1 else 2) else 3
→  2
```

### Let bindings

```
λ> let double = \n. (n + n) in double 7
→  14

λ> let x = 3 in let y = 4 in (x + y)
→  7
```

### Named definitions in the REPL

```
λ> :let compose = \f g x. f (g x)
Defined: compose
λ> :let inc = \n. (n + 1)
Defined: inc
λ> compose inc inc 5
→  7
```

### Stepwise evaluation

```
λ> :step (\x. (x + 1)) 41
  Start: (\x. (x + 1)) 41
  [Enter for next step, Ctrl-C to stop]
  Step 1: (41 + 1)
  [Enter for next step, Ctrl-C to stop]
  Step 2: 42
  Normal form reached.
```

### Church numerals

```
λ> #0 f x
→  x

λ> #2 f x
→  f (f x)

λ> let add = \m n f x. m f (n f x) in add #2 #3 f x
→  f (f (f (f (f x))))
```

### Diverging term (Ω)

```
λ> (\x. x x) (\x. x x)
Error: Did not reach normal form after 10000 steps. The expression may diverge.
```

## File format

A `.lc` file contains definitions and expressions, one per line:

```
-- this is a comment
add = \m n f x. m f (n f x)
mul = \m n f. m (n f)

add #2 #3 f x
mul #2 #3 f x
```

Definitions (`name = term`) are stored in the environment and available to all
subsequent lines. Expression lines are evaluated and their results printed.

## Project structure

```
main.py           entry point (REPL / file runner)
terms.py          AST dataclasses (Var, Lam, App, Lit, BinOp, If)
reduction.py      free_vars, subst, reduce_step, evaluate
parser.py         tokenizer, Parser, parse, Church numeral builder
environment.py    Environment (named definitions)
repl.py           repl(), run_file(), help text
tests/
  test_parse.py         parser / AST construction
  test_free_vars.py     free variable analysis
  test_substitution.py  capture-avoiding substitution
  test_evaluate.py      full evaluation
  test_files.py         file-based evaluation
  testdata/             .lc input files used by test_files.py
```

## Running tests

```
python -m pytest tests/ -v
```

Tests are split into:

- `tests/test_parse.py` — parser / AST construction
- `tests/test_free_vars.py` — free variable analysis
- `tests/test_substitution.py` — capture-avoiding substitution
- `tests/test_evaluate.py` — full evaluation
- `tests/test_files.py` — file-based evaluation using `tests/testdata/*.lc`
