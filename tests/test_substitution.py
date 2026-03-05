"""Tests for capture-avoiding substitution."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reduction import subst
from parser import parse
from terms import Var, Lam, Lit


def test_replace_matching_variable():
    # x[5/x]  →  5
    assert subst(Var("x"), "x", Lit(5)) == Lit(5)


def test_leave_different_variable():
    # y[5/x]  →  y
    assert subst(Var("y"), "x", Lit(5)) == Var("y")


def test_no_substitution_under_rebinding():
    # (λx. x)[5/x]  →  λx. x  (x is rebound, nothing changes)
    term = Lam("x", Var("x"))
    assert subst(term, "x", Lit(5)) == term


def test_substitution_in_body():
    # (λy. x)[5/x]  →  λy. 5
    result = subst(Lam("y", Var("x")), "x", Lit(5))
    assert result == Lam("y", Lit(5))


def test_alpha_rename_to_avoid_capture():
    # (λy. x)[y/x]  — naive substitution would capture y inside λy
    # should alpha-rename: λy'. y  (fresh name for the binder)
    result = subst(Lam("y", Var("x")), "x", Var("y"))
    # The binder must be renamed (not 'y'), and the body must be Var("y")
    assert isinstance(result, Lam)
    assert result.param != "y"          # binder was renamed
    assert result.body == Var("y")      # the substituted value is present


def test_substitution_in_application():
    # (f x)[g/f]  →  g x
    result = subst(parse("f x"), "f", Var("g"))
    assert result == parse("g x")


def test_literal_unchanged():
    assert subst(Lit(42), "x", Lit(0)) == Lit(42)
