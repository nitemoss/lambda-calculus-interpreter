"""Tests for full evaluation — parse a string and check the normal form."""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser import parse
from reduction import evaluate, NonTerminatingError
from terms import Lit, Lam, Var, App


def run(expr: str):
    """Helper: parse and fully evaluate an expression string."""
    return evaluate(parse(expr))


# ── Beta reduction ────────────────────────────────────────────────────────────

def test_identity():
    # (λx. x) y  →  y
    assert run(r"(\x. x) y") == Var("y")


def test_constant_function():
    # (λx. λy. x) true false  →  true
    assert run(r"(\x y. x) true false") == Lit(True)


def test_self_application():
    # (λx. x x) (λy. y)  →  λy. y
    assert run(r"(\x. x x) (\y. y)") == Lam("y", Var("y"))


def test_application_left_associative():
    # (λx. λy. x) 1 2  →  1
    assert run(r"(\x y. x) 1 2") == Lit(1)


# ── Arithmetic ────────────────────────────────────────────────────────────────

def test_addition():
    assert run("(3 + 4)") == Lit(7)


def test_subtraction():
    assert run("(10 - 3)") == Lit(7)


def test_multiplication():
    assert run("(3 * 4)") == Lit(12)


def test_chained_arithmetic():
    assert run("(2 + 3) * (10 - 4)") == Lit(30)


def test_equality_true():
    assert run("(5 == 5)") == Lit(True)


def test_equality_false():
    assert run("(5 == 6)") == Lit(False)


def test_less_than_true():
    assert run("(3 < 10)") == Lit(True)


def test_less_than_false():
    assert run("(10 < 3)") == Lit(False)


# ── Conditionals ──────────────────────────────────────────────────────────────

def test_if_true_branch():
    assert run("if true then 1 else 2") == Lit(1)


def test_if_false_branch():
    assert run("if false then 1 else 2") == Lit(2)


def test_nested_if():
    assert run("if true then (if false then 1 else 2) else 3") == Lit(2)


def test_if_with_comparison():
    assert run("if (5 < 10) then 42 else 0") == Lit(42)


# ── Let bindings ──────────────────────────────────────────────────────────────

def test_let_basic():
    assert run("let x = 7 in x") == Lit(7)


def test_let_used_in_body():
    assert run("let double = \\n. (n + n) in double 5") == Lit(10)


def test_let_nested():
    assert run("let x = 3 in let y = 4 in (x + y)") == Lit(7)


def test_let_with_conditional():
    assert run("let x = 5 in if (x < 10) then (x * 2) else x") == Lit(10)


# ── Church numerals ───────────────────────────────────────────────────────────

def test_church_zero_applied():
    # c0 f x  →  x
    assert run(r"#0 f x") == Var("x")


def test_church_one_applied():
    # c1 f x  →  f x
    assert run(r"#1 f x") == App(Var("f"), Var("x"))


def test_church_add():
    # standard add combinator: add #2 #3 should give c5
    result = run(r"let add = \m n f x. m f (n f x) in add #2 #3 f x")
    # c5 f x reduces to f(f(f(f(f x))))
    expected = run(r"#5 f x")
    assert result == expected


# ── Non-termination ───────────────────────────────────────────────────────────

def test_omega_diverges():
    # Ω = (λx. x x)(λx. x x) loops forever
    with pytest.raises(NonTerminatingError):
        run(r"(\x. x x) (\x. x x)")
