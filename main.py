"""
Entry point for the lambda calculus interpreter.

Usage:
  python main.py                    # start interactive REPL
  python main.py file.lc            # run a .lc file
  python main.py --trace file.lc    # run a .lc file with step trace
"""

import sys
from environment import Environment
from repl import repl, run_file

if __name__ == "__main__":
    if len(sys.argv) == 1:
        repl()
    elif len(sys.argv) == 2:
        run_file(sys.argv[1], Environment())
    elif len(sys.argv) == 3 and sys.argv[1] == "--trace":
        run_file(sys.argv[2], Environment(), trace=True)
    else:
        print("Usage:")
        print("  python main.py                    # start REPL")
        print("  python main.py file.lc            # run a file")
        print("  python main.py --trace file.lc    # run with step trace")
