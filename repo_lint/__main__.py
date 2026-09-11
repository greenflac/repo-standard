"""CLI прибора.

Коды возврата (Р1, Р2): 0 — годно, 1 — есть нарушения, 2 — нарушений нет,
но что-то проверить не смогли.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import Repo, exit_code, render_text, run_checks, summarise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="repo-lint", description="соответствие стандарту оформления")
    parser.add_argument("path", nargs="?", default=".", help="корень репозитория")
    parser.add_argument("--tier", choices=("base", "public"), default="base")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--limit", type=int, default=5, help="сколько находок печатать на проверку")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"не смогли проверить: {root} не каталог", file=sys.stderr)
        return 2

    repo = Repo(root)
    results = run_checks(repo, args.tier)

    if args.format == "json":
        payload = {
            "root": str(repo.root),
            "tier": args.tier,
            "summary": summarise(results),
            "checks": [
                {
                    "code": r.code,
                    "title": r.title,
                    "tier": r.tier,
                    "status": r.status,
                    "note": r.note,
                    "findings": [
                        {"path": f.path, "line": f.line, "message": f.message} for f in r.findings
                    ],
                }
                for r in results
            ],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_text(results, repo, limit=args.limit))

    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
