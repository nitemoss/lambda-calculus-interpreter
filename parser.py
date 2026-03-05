"""
Parser — turns a source string into a Term tree.

Grammar:
  term  ::= lam | let | if | app
  lam   ::= ("\" | "λ") name+ "." term
  let   ::= "let" name "=" term "in" term
  if    ::= "if" term "then" term "else" term
  app   ::= atom+                             (left-associative)
  atom  ::= name | number | "true" | "false" | "#"number | "(" term ")"

Infix operators (+ - * == <) are handled inside app, folded into BinOp nodes.
"""

from __future__ import annotations
from terms import Var, Lam, App, Lit, BinOp, If, Term


KEYWORDS = {"let", "in", "if", "then", "else", "true", "false"}


# ---------------------------------------------------------------------------
# Church numeral builder
# ---------------------------------------------------------------------------

def _church_numeral(n: int) -> Term:
    """Build the Church numeral for n:  λf. λx. f(f(…(f x)…))

    The number n is represented as "apply f exactly n times to x".
    """
    body: Term = Var("x")
    for _ in range(n):
        body = App(Var("f"), body)
    return Lam("f", Lam("x", body))


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class Parser:
    def __init__(self, text: str):
        self.tokens = self._tokenize(text)
        self.pos = 0

    # ── Tokenizer ────────────────────────────────────────────────────────────

    def _tokenize(self, text: str) -> list[str]:
        """Split the input into a flat list of tokens."""
        tokens = []
        i = 0
        while i < len(text):
            c = text[i]
            if c.isspace():
                i += 1
            elif c in "().":
                tokens.append(c)
                i += 1
            elif c in r"\λ":
                tokens.append("λ")
                i += 1
            elif c == "#":
                # Church numeral sugar: #3  →  token "#3"
                j = i + 1
                while j < len(text) and text[j].isdigit():
                    j += 1
                tokens.append(text[i:j])
                i = j
            elif c.isdigit():
                j = i
                while j < len(text) and text[j].isdigit():
                    j += 1
                tokens.append(text[i:j])
                i = j
            elif c.isalpha() or c == "_":
                j = i
                while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                    j += 1
                tokens.append(text[i:j])
                i = j
            elif text[i:i+2] == "==":
                tokens.append("==")
                i += 2
            elif c == "=":
                tokens.append("=")
                i += 1
            elif c in "+-*<":
                tokens.append(c)
                i += 1
            else:
                raise SyntaxError(f"Unexpected character: {c!r}")
        return tokens

    # ── Token helpers ─────────────────────────────────────────────────────────

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def consume(self, expected: str | None = None) -> str:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input")
        if expected is not None and tok != expected:
            raise SyntaxError(f"Expected {expected!r} but got {tok!r}")
        self.pos += 1
        return tok

    def at_end(self) -> bool:
        return self.pos >= len(self.tokens)

    # ── Grammar rules ─────────────────────────────────────────────────────────

    def parse_term(self) -> Term:
        tok = self.peek()

        # Lambda:  λx y. body
        if tok == "λ":
            self.consume("λ")
            params = []
            while self.peek() not in (".", None):
                params.append(self.consume())
            if not params:
                raise SyntaxError("Lambda needs at least one parameter")
            self.consume(".")
            body = self.parse_term()
            for p in reversed(params):
                body = Lam(p, body)
            return body

        # Let:  let x = t1 in t2   →   (λx. t2) t1
        if tok == "let":
            self.consume("let")
            name = self.consume()
            self.consume("=")
            definition = self.parse_term()
            self.consume("in")
            body = self.parse_term()
            return App(Lam(name, body), definition)

        # If:  if cond then t1 else t2
        if tok == "if":
            self.consume("if")
            cond = self.parse_term()
            self.consume("then")
            then_ = self.parse_term()
            self.consume("else")
            else_ = self.parse_term()
            return If(cond, then_, else_)

        return self.parse_app()

    def parse_app(self) -> Term:
        """Parse a left-associative chain of atoms: a b c  →  App(App(a,b),c).

        Infix operators (+ - * == <) are handled inline between atoms.
        """
        atoms = []
        while self.peek() not in (None, ".", ")", "then", "else", "in"):
            if self.peek() in ("+", "-", "*", "==", "<") and atoms:
                op = self.consume()
                right = self.parse_atom()
                atoms[-1] = BinOp(op, atoms[-1], right)
            else:
                atoms.append(self.parse_atom())
        if not atoms:
            raise SyntaxError("Expected an expression")
        result = atoms[0]
        for atom in atoms[1:]:
            result = App(result, atom)
        return result

    def parse_atom(self) -> Term:
        """Parse a single indivisible unit."""
        tok = self.peek()

        if tok is None:
            raise SyntaxError("Unexpected end of input")

        if tok == "(":
            self.consume("(")
            term = self.parse_term()
            self.consume(")")
            return term

        # Church numeral sugar:  #3  →  λf. λx. f (f (f x))
        if tok.startswith("#"):
            self.consume()
            return _church_numeral(int(tok[1:]))

        if tok == "true":
            self.consume()
            return Lit(True)
        if tok == "false":
            self.consume()
            return Lit(False)

        if tok.isdigit() or (len(tok) > 1 and tok[0].isdigit()):
            self.consume()
            return Lit(int(tok))

        if tok not in KEYWORDS and (tok[0].isalpha() or tok[0] == "_"):
            self.consume()
            return Var(tok)

        raise SyntaxError(f"Unexpected token: {tok!r}")


def parse(text: str) -> Term:
    """Parse a string into a Term tree. Raises SyntaxError on bad input."""
    p = Parser(text.strip())
    term = p.parse_term()
    if not p.at_end():
        raise SyntaxError(f"Unexpected token after expression: {p.peek()!r}")
    return term
