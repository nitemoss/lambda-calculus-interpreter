"""Tests for free variable analysis."""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reduction import free_vars
from parser import parse


def test_variable_is_free():
    assert free_vars(parse("x")) == {"x"}


def test_literal_has_no_free_vars():
    assert free_vars(parse("42")) == set()


def test_lambda_binds_its_param():
    # λx. x  — x is bound, nothing is free
    assert free_vars(parse(r"\x. x")) == set()


def test_lambda_body_free_var():
    # λx. y  — y is free
    assert free_vars(parse(r"\x. y")) == {"y"}


def test_lambda_does_not_bind_other_vars():
    # λx. x y  — y is free
    assert free_vars(parse(r"\x. x y")) == {"y"}


def test_application_union():
    # f x  — both free
    assert free_vars(parse("f x")) == {"f", "x"}


def test_nested_lambda_inner_binding():
    # λx. λy. x  — both bound
    assert free_vars(parse(r"\x y. x")) == set()


def test_binop_free_vars():
    assert free_vars(parse("(x + y)")) == {"x", "y"}


def test_if_free_vars():
    assert free_vars(parse("if b then x else y")) == {"b", "x", "y"}
