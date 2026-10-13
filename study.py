"""Run this file from CMD. Files inside curriculum_engine are imported modules."""

import sys

if __name__ == "__main__":
    try:
        from curriculum_engine.cli import main
    except ModuleNotFoundError as exc:
        print(f"Missing dependency or project file: {exc.name}", file=sys.stderr)
        print("Extract the entire ZIP, then run: py -m pip install -r requirements.txt", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(main())
