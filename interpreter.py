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
#
# The tricky case is a lambda whose parameter has the same name as a free
# variable in 'replacement'. Without care, that free variable would become
# accidentally bound ("captured") by the lambda. We prevent this by renaming
# the lambda's parameter first (alpha-renaming).
#
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


# ---------------------------------------------------------------------------
# PART 5 — REDUCTION (ONE STEP AT A TIME)
# ---------------------------------------------------------------------------
# We reduce using *normal order*: always pick the outermost, leftmost redex.
# This guarantees that if any reduction sequence terminates, normal order will.
#
# A "redex" (reducible expression) is a function call where the function is
# a lambda:  (λx. body) arg.  We replace it with  body[x := arg].
#
# For built-ins we add "delta reductions":
#   (3 + 4)      →  7
#   (if true …)  →  the then-branch

def reduce_step(term: Term) -> tuple[Term, bool]:
    """Try to perform one reduction step on 'term'.

    Returns (new_term, True)  if a step was taken,
            (term,     False) if the term is already in normal form.
    """
    match term:

        # ── Beta reduction ──────────────────────────────────────────────────
        # (λx. body) arg  →  body[x := arg]
        case App(Lam(param, body), arg):
            return subst(body, param, arg), True

        # ── Application: reduce function first, then argument ───────────────
        case App(func, arg):
            reduced_func, changed = reduce_step(func)
            if changed:
                return App(reduced_func, arg), True
            reduced_arg, changed = reduce_step(arg)
            return App(func, reduced_arg), changed

        # ── Lambda: reduce inside the body ──────────────────────────────────
        case Lam(param, body):
            reduced_body, changed = reduce_step(body)
            return Lam(param, reduced_body), changed

        # ── Delta reduction: arithmetic ──────────────────────────────────────
        # Only fires when both sides are already literal numbers.
        case BinOp(op, Lit(l), Lit(r)):
            match op:
                case "+":  result = l + r
                case "-":  result = l - r
                case "*":  result = l * r
                case "==": result = (l == r)
                case "<":  result = (l < r)
                case _:    raise ValueError(f"Unknown operator: {op}")
            return Lit(result), True

        # ── BinOp: reduce operands first ────────────────────────────────────
        case BinOp(op, left, right):
            reduced_left, changed = reduce_step(left)
            if changed:
                return BinOp(op, reduced_left, right), True
            reduced_right, changed = reduce_step(right)
            return BinOp(op, left, reduced_right), changed

        # ── Delta reduction: conditional ────────────────────────────────────
        case If(Lit(True), then_, _):
            return then_, True
        case If(Lit(False), _, else_):
            return else_, True

        # ── If: reduce condition first ───────────────────────────────────────
        case If(cond, then_, else_):
            reduced_cond, changed = reduce_step(cond)
            return If(reduced_cond, then_, else_), changed

        # ── Variable or literal: nothing to reduce ───────────────────────────
        case _:
            return term, False


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


# ---------------------------------------------------------------------------
# PART 6 — PARSER
# ---------------------------------------------------------------------------
# We turn a string like "\x. x y" into the tree  Lam("x", App(Var("x"), Var("y"))).
#
# The grammar we parse:
#
#   term   ::= lam | let | letrec | if | app
#   lam    ::= ("\" | "λ") name+ "." term
#   app    ::= atom+                          (left-associative)
#   atom   ::= name | number | "true" | "false" | "#"number | "(" term ")"

KEYWORDS = {"let", "in", "if", "then", "else", "true", "false"}


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

        # Otherwise: application (one or more atoms, possibly with infix ops)
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
                # Fold the operator into the last atom as a BinOp
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

        # Parenthesised sub-expression
        if tok == "(":
            self.consume("(")
            term = self.parse_term()
            self.consume(")")
            return term

        # Church numeral sugar:  #3  →  λf. λx. f (f (f x))
        if tok.startswith("#"):
            self.consume()
            return _church_numeral(int(tok[1:]))

        # Boolean literals
        if tok == "true":
            self.consume()
            return Lit(True)
        if tok == "false":
            self.consume()
            return Lit(False)

        # Integer literal
        if tok.isdigit() or (len(tok) > 1 and tok[0].isdigit()):
            self.consume()
            return Lit(int(tok))

        # Variable name
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


# ---------------------------------------------------------------------------
# PART 7 — BUILT-IN COMBINATORS
# ---------------------------------------------------------------------------

def _church_numeral(n: int) -> Term:
    """Build the Church numeral for n:  λf. λx. f(f(…(f x)…))

    Church numerals encode natural numbers as higher-order functions.
    The number n is represented as "apply f exactly n times to x".
    """
    body: Term = Var("x")
    for _ in range(n):
        body = App(Var("f"), body)
    return Lam("f", Lam("x", body))


# ---------------------------------------------------------------------------
# PART 8 — ENVIRONMENT (named definitions)
# ---------------------------------------------------------------------------
# The REPL keeps a dictionary of  name → term  so the user can write
#   :let id = \x. x
# and then use  id  in later expressions.

class Environment:
    def __init__(self):
        self._bindings: dict[str, Term] = {}

    def define(self, name: str, term: Term):
        self._bindings[name] = term

    def expand(self, term: Term) -> Term:
        """Inline every free variable that has a known definition.

        This is done before evaluation so named definitions are substituted in.
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


    elif len(sys.argv) == 3 and sys.argv[1] == "--trace":
        run_file(sys.argv[2], Environment(), trace=True)
    else:
        print("Usage:")
        print("  python interpreter.py                    # start REPL")
        print("  python interpreter.py file.lc            # run a file")
        print("  python interpreter.py --trace file.lc    # run with step trace")
