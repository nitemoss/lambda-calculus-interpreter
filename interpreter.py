"""
Extended Lambda Calculus Interpreter
=====================================
Lambda calculus is the simplest possible programming language.
Every program is built from just three things:
  - a variable:            x
  - a function definition: λx. body   (read: "a function that takes x and returns body")
  - a function call:       f arg       (read: "apply f to arg")

Running a program means repeatedly applying one rule:
  (λx. body) arg  →  body with every x replaced by arg

That rule is called beta-reduction. We keep reducing until nothing changes.

This interpreter also supports arithmetic, booleans, let-bindings, and
recursive definitions as convenient shorthand on top of the pure calculus.
"""

from __future__ import annotations
from dataclasses import dataclass
import sys
import readline  # enables arrow-key history in the REPL


# ---------------------------------------------------------------------------
# PART 1 — THE TERM TREE
# ---------------------------------------------------------------------------
# A lambda calculus expression is a tree. Each node is one of the types below.
# We use Python dataclasses so that printing and equality come for free.

@dataclass
class Var:
    """A variable — just a name that refers to something defined elsewhere.

    Example:  x
    """
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass
class Lam:
    """A function definition (lambda abstraction).

    Example:  λx. x           — the identity function
              λx. λy. x       — a function returning its first argument
    The 'param' is the name given to the input; 'body' is the expression
    that will be evaluated once the input is supplied.
    """
    param: str
    body: Term

    def __str__(self) -> str:
        # Flatten nested lambdas: λx. λy. t  →  λx y. t
        params, body = [self.param], self.body
        while isinstance(body, Lam):
            params.append(body.param)
            body = body.body
        return f"λ{' '.join(params)}. {body}"


@dataclass
class App:
    """A function call (application).

    Example:  f x             — call f with argument x
              (λx. x) y       — call the identity function with y
    'func' is the thing being called; 'arg' is the argument passed to it.
    """
    func: Term
    arg: Term

    def __str__(self) -> str:
        # Add parentheses only where needed to avoid ambiguity
        func_str = f"({self.func})" if isinstance(self.func, Lam) else str(self.func)
        arg_str = str(self.arg)
        if isinstance(self.arg, (App, Lam)):
            arg_str = f"({arg_str})"
        return f"{func_str} {arg_str}"


@dataclass
class Lit:
    """A literal value — a plain integer or boolean.

    These are built-in conveniences; in pure lambda calculus you would
    encode numbers and booleans using functions (Church encodings).

    Examples:  42   true   false
    """
    value: int | bool

    def __str__(self) -> str:
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        return str(self.value)


@dataclass
class BinOp:
    """A binary arithmetic or comparison operation.

    Examples:  x + 1     n * (n - 1)     n == 0     n < 10
    """
    op: str   # one of: + - * == <
    left: Term
    right: Term

    def __str__(self) -> str:
        return f"({self.left} {self.op} {self.right})"


@dataclass
class If:
    """A conditional expression.

    Example:  if n == 0 then 1 else n * fact (n - 1)

    Unlike an if-statement, this always produces a value (like a ternary).
    """
    cond: Term
    then_: Term
    else_: Term

    def __str__(self) -> str:
        return f"if {self.cond} then {self.then_} else {self.else_}"


# A type alias so we can write 'Term' anywhere we mean "any of the above"
Term = Var | Lam | App | Lit | BinOp | If


# ---------------------------------------------------------------------------
# PART 2 — FREE VARIABLES
# ---------------------------------------------------------------------------
# A variable is "free" in an expression if it is not bound by any surrounding
# lambda. For example, in  λx. x y,  'x' is bound but 'y' is free.
# We need to track free variables to avoid accidentally capturing them
# during substitution (explained below).

def free_vars(term: Term) -> set[str]:
    """Return the set of variable names that appear free in 'term'."""
    match term:
        case Var(name):
            return {name}
        case Lam(param, body):
            # The lambda binds 'param', so remove it from the body's free vars
            return free_vars(body) - {param}
        case App(func, arg):
            return free_vars(func) | free_vars(arg)
        case Lit():
            return set()
        case BinOp(_, left, right):
            return free_vars(left) | free_vars(right)
        case If(cond, then_, else_):
            return free_vars(cond) | free_vars(then_) | free_vars(else_)


# ---------------------------------------------------------------------------
# PART 3 — FRESH NAME SUPPLY
# ---------------------------------------------------------------------------
# When we rename a variable to avoid a clash, we need a name that is not
# already used anywhere. We generate names like  x_1, x_2, x_3, …

_fresh_counter = 0

def fresh(base: str) -> str:
    """Return a new variable name derived from 'base' that has never been used."""
    global _fresh_counter
    _fresh_counter += 1
    return f"{base}_{_fresh_counter}"


# ---------------------------------------------------------------------------
# PART 4 — SUBSTITUTION
# ---------------------------------------------------------------------------
# Substitution replaces every free occurrence of a variable with a new term.
# Written  term[var := replacement].
# Example of the problem:
#   (λy. x)[x := y]   should give  λz. y  (rename binder to avoid clash)
#   Without renaming we'd get  λy. y  where the substituted 'y' is now
#   captured by the binder — that changes the meaning entirely.

def subst(term: Term, var: str, replacement: Term) -> Term:
    """Return 'term' with every free occurrence of 'var' replaced by 'replacement'."""
    match term:
        case Var(name):
            # If this variable IS the one we are replacing, swap it out
            return replacement if name == var else term

        case Lam(param, body):
            if param == var:
                # The lambda re-binds 'var', so 'var' is not free in the body.
                # Nothing to substitute inside.
                return term
            if param in free_vars(replacement):
                # The lambda's parameter clashes with a free variable in the
                # replacement. Rename the parameter to avoid capture.
                new_param = fresh(param)
                body = subst(body, param, Var(new_param))
                param = new_param
            return Lam(param, subst(body, var, replacement))

        case App(func, arg):
            return App(subst(func, var, replacement),
                       subst(arg,  var, replacement))

        case Lit():
            return term  # literals contain no variables

        case BinOp(op, left, right):
            return BinOp(op, subst(left, var, replacement),
                             subst(right, var, replacement))

        case If(cond, then_, else_):
            return If(subst(cond,  var, replacement),
                      subst(then_, var, replacement),
                      subst(else_, var, replacement))

