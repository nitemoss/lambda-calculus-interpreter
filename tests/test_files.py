"""Tests that load .lc files from tests/testdata/ and check evaluation results."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser import parse
from reduction import evaluate
from environment import Environment
from terms import Lit, Var, App, Lam

TESTDATA = os.path.join(os.path.dirname(__file__), "testdata")


def eval_file_expressions(filename: str) -> list:
    """
    Parse and evaluate every non-comment, non-definition line in a .lc file.
    Definition lines (name = term) are stored in the environment for reuse.
    Returns a list of (expression_string, result) pairs.
    """
    env = Environment()
    results = []
    with open(os.path.join(TESTDATA, filename)) as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("--"):
                continue
            parts = line.split("=", 1)
            lhs = parts[0].strip()
            if len(parts) == 2 and lhs.isidentifier():
                term = env.expand(parse(parts[1].strip()))
                env.define(lhs, term)
            else:
                term = env.expand(parse(line))
                results.append((line, evaluate(term)))
    return results


# ── arithmetic.lc ─────────────────────────────────────────────────────────────

def test_arithmetic_file_addition():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(3 + 4)"] == Lit(7)


def test_arithmetic_file_subtraction():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(10 - 3)"] == Lit(7)


def test_arithmetic_file_multiplication():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(3 * 4)"] == Lit(12)


def test_arithmetic_file_chained():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(2 + 3) * (10 - 4)"] == Lit(30)


def test_arithmetic_file_equality_true():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(7 == 7)"] == Lit(True)


def test_arithmetic_file_equality_false():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(7 == 8)"] == Lit(False)


def test_arithmetic_file_less_than_true():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(3 < 10)"] == Lit(True)


def test_arithmetic_file_less_than_false():
    results = dict(eval_file_expressions("arithmetic.lc"))
    assert results["(10 < 3)"] == Lit(False)


# ── beta.lc ───────────────────────────────────────────────────────────────────

def test_beta_file_identity():
    results = dict(eval_file_expressions("beta.lc"))
    assert results[r"(\x. x) y"] == Var("y")


def test_beta_file_constant():
    results = dict(eval_file_expressions("beta.lc"))
    assert results[r"(\x y. x) true false"] == Lit(True)


def test_beta_file_increment():
    results = dict(eval_file_expressions("beta.lc"))
    assert results[r"(\x. (x + 1)) 41"] == Lit(42)


def test_beta_file_double():
    results = dict(eval_file_expressions("beta.lc"))
    assert results[r"(\f. \x. f x) (\n. (n * 2)) 5"] == Lit(10)


# ── let_bindings.lc ───────────────────────────────────────────────────────────

def test_let_file_basic():
    results = dict(eval_file_expressions("let_bindings.lc"))
    assert results["let x = 7 in x"] == Lit(7)


def test_let_file_double():
    results = dict(eval_file_expressions("let_bindings.lc"))
    assert results[r"let double = \n. (n + n) in double 5"] == Lit(10)


def test_let_file_nested():
    results = dict(eval_file_expressions("let_bindings.lc"))
    assert results["let x = 3 in let y = 4 in (x + y)"] == Lit(7)


def test_let_file_conditional():
    results = dict(eval_file_expressions("let_bindings.lc"))
    assert results["let x = 5 in if (x < 10) then (x * 2) else x"] == Lit(10)


def test_let_file_pythagorean():
    results = dict(eval_file_expressions("let_bindings.lc"))
    assert results[r"let sq = \n. (n * n) in ((sq 3) + (sq 4))"] == Lit(25)


# ── conditionals.lc ───────────────────────────────────────────────────────────

def test_conditionals_file_true_branch():
    results = dict(eval_file_expressions("conditionals.lc"))
    assert results["if true then 1 else 2"] == Lit(1)


def test_conditionals_file_false_branch():
    results = dict(eval_file_expressions("conditionals.lc"))
    assert results["if false then 1 else 2"] == Lit(2)


def test_conditionals_file_nested():
    results = dict(eval_file_expressions("conditionals.lc"))
    assert results["if true then (if false then 1 else 2) else 3"] == Lit(2)


def test_conditionals_file_comparison():
    results = dict(eval_file_expressions("conditionals.lc"))
    assert results["if (5 == 5) then true else false"] == Lit(True)


# ── church.lc ─────────────────────────────────────────────────────────────────

def test_church_file_zero():
    results = dict(eval_file_expressions("church.lc"))
    # c0 f x  →  x
    assert results["#0 f x"] == Var("x")


def test_church_file_one():
    results = dict(eval_file_expressions("church.lc"))
    # c1 f x  →  f x
    assert results["#1 f x"] == App(Var("f"), Var("x"))


def test_church_file_add():
    results = dict(eval_file_expressions("church.lc"))
    # add #2 #3 f x  should equal  #5 f x
    expected = evaluate(parse("#5 f x"))
    assert results["add #2 #3 f x"] == expected


def test_church_file_mul():
    results = dict(eval_file_expressions("church.lc"))
    # mul #2 #3 f x  should equal  #6 f x
    expected = evaluate(parse("#6 f x"))
    assert results["mul #2 #3 f x"] == expected
