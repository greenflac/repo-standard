"""Мутация констант-решений: проверка, что тесты действительно их сторожат (правило Т1).

Каждая константа подменяется в обе стороны — строже и слабее. Если после подмены
тесты остались зелёными, константу никто не проверяет, и скрипт падает с указанием,
какая именно мутация выжила.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "repo_lint" / "checks.py"
ROOT = TARGET.parents[1]

# имя константы -> (строже, слабее)
MUTATIONS = {
    "ROOT_FILES_MAX": (10, 500),
    "BIG_BLOB_KB": (64, 100000),
    "DOCS_FLAT_MAX": (2, 500),
}


def run_tests() -> bool:
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-x", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


def mutate(source: str, name: str, value: int) -> str:
    pattern = re.compile(rf"^{name} = \d+$", re.MULTILINE)
    mutated, count = pattern.subn(f"{name} = {value}", source)
    if count != 1:
        raise SystemExit(f"не смогли подменить {name}: совпадений {count}, ожидалась 1")
    return mutated


def main() -> int:
    original = TARGET.read_text(encoding="utf-8")
    if not run_tests():
        print("тесты красные до мутации — мутировать нечего")
        return 2
    survived = []
    checked = 0
    try:
        for name, (stricter, looser) in MUTATIONS.items():
            for direction, value in (("строже", stricter), ("слабее", looser)):
                checked += 1
                TARGET.write_text(mutate(original, name, value), encoding="utf-8")
                green = run_tests()
                mark = "выжила" if green else "убита"
                print(f"{name} {direction} -> {value}: мутация {mark}")
                if green:
                    survived.append(f"{name} {direction} -> {value}")
    finally:
        TARGET.write_text(original, encoding="utf-8")
    print(f"\nпроверено мутаций {checked}, выжило {len(survived)}, не смогли 0")
    if survived:
        print("константу никто не сторожит: " + "; ".join(survived))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
