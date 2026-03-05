"""
Environment — stores named definitions for use in the REPL and file loader.

The user can write  :let id = \\x. x  and then use  id  in later expressions.
expand() inlines every known definition before evaluation.
"""

from __future__ import annotations
from terms import Var, Lam, App, BinOp, If, Term


class Environment:
    def __init__(self):
        self._bindings: dict[str, Term] = {}

    def define(self, name: str, term: Term):
        self._bindings[name] = term

    def expand(self, term: Term) -> Term:
        """Inline every free variable that has a known definition.

        This is done before evaluation so named definitions are substituted in.
        Bound lambda parameters temporarily shadow global definitions to avoid
        incorrect expansion inside the lambda body.
        """
        match term:
            case Var(name) if name in self._bindings:
                return self._bindings[name]
            case Lam(param, body):
                # Don't expand the bound parameter itself
                saved = self._bindings.pop(param, None)
                expanded = Lam(param, self.expand(body))
                if saved is not None:
                    self._bindings[param] = saved
                return expanded
            case App(func, arg):
                return App(self.expand(func), self.expand(arg))
            case BinOp(op, left, right):
                return BinOp(op, self.expand(left), self.expand(right))
            case If(cond, then_, else_):
                return If(self.expand(cond), self.expand(then_), self.expand(else_))
            case _:
                return term

    def names(self) -> list[str]:
        return list(self._bindings.keys())
