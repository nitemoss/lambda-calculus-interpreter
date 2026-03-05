"""
REPL and file loader.

run_file() — evaluate a .lc file and print results
repl()     — interactive read-eval-print loop
"""

from __future__ import annotations
import readline  # enables arrow-key history in the REPL

from parser import parse, KEYWORDS
from reduction import evaluate, reduce_step, NonTerminatingError
from environment import Environment


HELP_TEXT = """
Commands:
  <term>                evaluate a lambda calculus expression
  :let name = <term>    define a named term for reuse
  :step <term>          evaluate one step at a time (press Enter to continue)
  :trace <term>         evaluate and print every intermediate step
  :load <file>          load and run a .lc file
  :env                  list all defined names
  :help                 show this message
  :quit                 exit

Syntax:
  \\x. body   or  λx. body     lambda (function definition)
  f arg                        application (function call)
  let x = t1 in t2             shorthand for  (\\x. t2) t1
  if c then t1 else t2         conditional
  #n                           Church numeral for integer n  (e.g. #3)
  true  false                  boolean literals
  (x + 1)  (n * n)  (n == 0)  arithmetic / comparison (wrap in parentheses)
"""


def run_file(path: str, env: Environment, trace: bool = False):
    """Load a .lc file, evaluate each expression, and print results.

    Lines of the form  name = term  are stored as definitions.
    All other non-blank, non-comment lines are evaluated and printed.
    """
    with open(path) as f:
        lines = f.readlines()

    for lineno, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("--"):
            continue
        try:
            parts = line.split("=", 1)
            lhs = parts[0].strip()
            if (len(parts) == 2
                    and lhs.isidentifier()
                    and lhs not in KEYWORDS):
                term = parse(parts[1].strip())
                term = env.expand(term)
                env.define(lhs, term)
                print(f"{lhs} defined.")
            else:
                term = parse(line)
                term = env.expand(term)
                result = evaluate(term, trace=trace)
                print(f"{line}  →  {result}")
        except (SyntaxError, NonTerminatingError, ValueError) as e:
            print(f"Line {lineno}: Error — {e}")


def repl():
    """Start an interactive read-eval-print loop."""
    env = Environment()
    print("Lambda Calculus Interpreter  (type :help for usage, :quit to exit)")

    while True:
        try:
            line = input("λ> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        if line in (":quit", ":q"):
            break

        if line in (":help", ":h"):
            print(HELP_TEXT)
            continue

        if line == ":env":
            names = env.names()
            print("Defined names:", ", ".join(names) if names else "(none)")
            continue

        if line.startswith(":let "):
            rest = line[5:].strip()
            try:
                name, _, expr = rest.partition("=")
                name = name.strip()
                term = env.expand(parse(expr.strip()))
                env.define(name, term)
                print(f"Defined: {name}")
            except SyntaxError as e:
                print(f"Syntax error: {e}")
            continue

        if line.startswith(":load "):
            path = line[6:].strip()
            try:
                run_file(path, env)
            except FileNotFoundError:
                print(f"File not found: {path}")
            continue

        if line.startswith(":step "):
            expr = line[6:].strip()
            try:
                term = env.expand(parse(expr))
                print(f"  Start: {term}")
                step = 0
                while True:
                    input("  [Enter for next step, Ctrl-C to stop] ")
                    term, changed = reduce_step(term)
                    step += 1
                    print(f"  Step {step}: {term}")
                    if not changed:
                        print("  Normal form reached.")
                        break
            except KeyboardInterrupt:
                print()
            except (SyntaxError, NonTerminatingError) as e:
                print(f"  Error: {e}")
            continue

        if line.startswith(":trace "):
            expr = line[7:].strip()
            try:
                term = env.expand(parse(expr))
                result = evaluate(term, trace=True)
                print(f"  Result: {result}")
            except (SyntaxError, NonTerminatingError) as e:
                print(f"Error: {e}")
            continue

        # Plain expression — evaluate and print result
        try:
            term = env.expand(parse(line))
            result = evaluate(term)
            print(f"→  {result}")
        except (SyntaxError, NonTerminatingError, ValueError) as e:
            print(f"Error: {e}")
