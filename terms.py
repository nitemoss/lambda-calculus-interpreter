"""
Term tree — the AST for lambda calculus expressions.

Every expression is one of:
  Var   — a variable name
  Lam   — a function definition (λx. body)
  App   — a function call (func arg)
  Lit   — an integer or boolean literal
  BinOp — a binary arithmetic / comparison operation
  If    — a conditional expression
"""

from __future__ import annotations
from dataclasses import dataclass


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
        func_str = f"({self.func})" if isinstance(self.func, Lam) else str(self.func)
        arg_str = str(self.arg)
        if isinstance(self.arg, (App, Lam)):
            arg_str = f"({arg_str})"
        return f"{func_str} {arg_str}"


@dataclass
class Lit:
    """A literal value — a plain integer or boolean.

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


# Type alias — use 'Term' anywhere you mean "any of the above"
Term = Var | Lam | App | Lit | BinOp | If
