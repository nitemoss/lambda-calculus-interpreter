"""
Reduction engine — free variables, substitution, and beta reduction.

The three core operations:
  free_vars(term)              — variables not bound by any enclosing lambda
  subst(term, var, replacement)— capture-avoiding substitution term[replacement/var]
  reduce_step(term)            — one normal-order beta/delta reduction step
  evaluate(term)               — reduce to normal form
"""

from __future__ import annotations
from terms import Var, Lam, App, Lit, BinOp, If, Term


# ---------------------------------------------------------------------------
# Free variables
# ---------------------------------------------------------------------------
# A variable is "free" if it is not bound by any surrounding lambda.
# Example: in  λx. x y,  'x' is bound but 'y' is free.

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
# Fresh name supply
# ---------------------------------------------------------------------------
# When alpha-renaming to avoid capture, we need a name not used anywhere.
# We generate names like  x_1, x_2, x_3, …

_fresh_counter = 0

def fresh(base: str) -> str:
    """Return a new variable name derived from 'base' that has never been used."""
    global _fresh_counter
    _fresh_counter += 1
    return f"{base}_{_fresh_counter}"


# ---------------------------------------------------------------------------
# Capture-avoiding substitution
# ---------------------------------------------------------------------------
# subst(term, var, replacement) rewrites term[replacement/var]:
# replace every free occurrence of 'var' with 'replacement'.
#
# The tricky case: if a lambda's parameter clashes with a free variable in
# 'replacement', we alpha-rename the parameter first to prevent capture.
#
# Example:  (λy. x)[y/x]  must rename the binder → λy'. y
#           Without renaming we'd get  λy. y  — wrong meaning entirely.

def subst(term: Term, var: str, replacement: Term) -> Term:
    """Return 'term' with every free occurrence of 'var' replaced by 'replacement'."""
    match term:
        case Var(name):
            return replacement if name == var else term

        case Lam(param, body):
            if param == var:
                # Lambda re-binds 'var'; nothing to substitute inside.
                return term
            if param in free_vars(replacement):
                # Parameter clashes with a free variable in replacement.
                # Alpha-rename the parameter to avoid capture.
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


# ---------------------------------------------------------------------------
# One-step reduction
# ---------------------------------------------------------------------------
# Normal-order strategy: always reduce the outermost, leftmost redex first.
# This guarantees finding a normal form whenever one exists.
#
# Beta reduction:   (λx. body) arg  →  body[arg/x]
# Delta reductions: (3 + 4) → 7,  (if true …) → then-branch

def reduce_step(term: Term) -> tuple[Term, bool]:
    """Try to perform one reduction step on 'term'.

    Returns (new_term, True)  if a step was taken,
            (term,     False) if the term is already in normal form.
    """
    match term:

        # Beta reduction: (λx. body) arg  →  body[arg/x]
        case App(Lam(param, body), arg):
            return subst(body, param, arg), True

        # Application: reduce function first, then argument
        case App(func, arg):
            reduced_func, changed = reduce_step(func)
            if changed:
                return App(reduced_func, arg), True
            reduced_arg, changed = reduce_step(arg)
            return App(func, reduced_arg), changed

        # Lambda: reduce inside the body
        case Lam(param, body):
            reduced_body, changed = reduce_step(body)
            return Lam(param, reduced_body), changed

        # Delta reduction: arithmetic (only when both sides are literals)
        case BinOp(op, Lit(l), Lit(r)):
            match op:
                case "+":  result = l + r
                case "-":  result = l - r
                case "*":  result = l * r
                case "==": result = (l == r)
                case "<":  result = (l < r)
                case _:    raise ValueError(f"Unknown operator: {op}")
            return Lit(result), True

        # BinOp: reduce operands first
        case BinOp(op, left, right):
            reduced_left, changed = reduce_step(left)
            if changed:
                return BinOp(op, reduced_left, right), True
            reduced_right, changed = reduce_step(right)
            return BinOp(op, left, reduced_right), changed

        # Delta reduction: conditional
        case If(Lit(True), then_, _):
            return then_, True
        case If(Lit(False), _, else_):
            return else_, True

        # If: reduce condition first
        case If(cond, then_, else_):
            reduced_cond, changed = reduce_step(cond)
            return If(reduced_cond, then_, else_), changed

        # Variable or literal: nothing to reduce
        case _:
            return term, False


# ---------------------------------------------------------------------------
# Full evaluation
# ---------------------------------------------------------------------------

class NonTerminatingError(Exception):
    pass


def evaluate(term: Term, max_steps: int = 10_000, trace: bool = False) -> Term:
    """Fully reduce 'term' to normal form using repeated one-step reductions.

    If 'trace' is True, print each intermediate step.
    Raises NonTerminatingError if the step limit is reached.
    """
    step = 0
    if trace:
        print(f"  Step {step:>4}: {term}")

    while True:
        term, changed = reduce_step(term)
        if not changed:
            return term
        step += 1
        if trace:
            print(f"  Step {step:>4}: {term}")
        if step >= max_steps:
            raise NonTerminatingError(
                f"Did not reach normal form after {max_steps} steps. "
                "The expression may diverge (e.g. infinite loop)."
            )
