"""Tests for the parser — checks that strings produce the right AST."""

import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser import parse
from terms import Var, Lam, App, Lit, BinOp, If


def test_variable():
    assert parse("x") == Var("x")


def test_integer_literal():
    assert parse("42") == Lit(42)


def test_true_literal():
    assert parse("true") == Lit(True)


def test_false_literal():
    assert parse("false") == Lit(False)


def test_identity_lambda():
    assert parse(r"\x. x") == Lam("x", Var("x"))


def test_lambda_unicode():
    assert parse("λx. x") == Lam("x", Var("x"))


def test_multi_param_lambda():
    # λx y. x  desugars to  λx. λy. x
    assert parse(r"\x y. x") == Lam("x", Lam("y", Var("x")))


def test_application():
    assert parse("f x") == App(Var("f"), Var("x"))


def test_application_is_left_associative():
    # f x y  →  (f x) y
    assert parse("f x y") == App(App(Var("f"), Var("x")), Var("y"))


def test_parenthesised_expression():
    assert parse("(x)") == Var("x")


def test_binop_addition():
    assert parse("(x + 1)") == BinOp("+", Var("x"), Lit(1))


def test_binop_multiplication():
    assert parse("(n * n)") == BinOp("*", Var("n"), Var("n"))


def test_binop_equality():
    assert parse("(n == 0)") == BinOp("==", Var("n"), Lit(0))


def test_binop_less_than():
    assert parse("(x < 10)") == BinOp("<", Var("x"), Lit(10))


def test_if_expression():
    assert parse("if true then 1 else 0") == If(Lit(True), Lit(1), Lit(0))


def test_let_desugars_to_application():
    # let x = 5 in x  →  (λx. x) 5
    assert parse("let x = 5 in x") == App(Lam("x", Var("x")), Lit(5))


def test_church_numeral_zero():
    # #0  →  λf. λx. x
    assert parse("#0") == Lam("f", Lam("x", Var("x")))


def test_church_numeral_one():
    # #1  →  λf. λx. f x
    assert parse("#1") == Lam("f", Lam("x", App(Var("f"), Var("x"))))


def test_unknown_character_raises():
    with pytest.raises(SyntaxError):
        parse("@x")


def test_empty_lambda_raises():
    with pytest.raises(SyntaxError):
        parse(r"\. x")


def test_trailing_token_raises():
    with pytest.raises(SyntaxError):
        parse("x y )")
