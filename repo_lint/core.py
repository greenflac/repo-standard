"""Модель результата, контекст репозитория и печать отчёта.

Три исхода вместо двух (правило Р1 харнеса): проверка возвращает `ok`, `violation`
или `unknown`. Свернуть `unknown` в любую из сторон нельзя — он виден и в отчёте,
и в коде возврата.
"""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

OK = "ok"
VIOLATION = "violation"
UNKNOWN = "unknown"

# Пути, которые прибор не считает содержимым репозитория при прогоне по чужому дереву.
# Фикстуры самого прибора обязаны быть грязными, поэтому исключены здесь и только здесь.
DEFAULT_EXCLUDES = (
    ".git/*",
    "*/fixtures/dirty/*",
    "*/fixtures/clean/*",
    "fixtures/dirty/*",
    "fixtures/clean/*",
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int | None
    message: str


@dataclass
class CheckResult:
    code: str
    title: str
    tier: str
    status: str
    findings: list[Finding] = field(default_factory=list)
    note: str = ""

    @classmethod
    def ok(cls, spec: "CheckSpec", note: str = "") -> "CheckResult":
        return cls(spec.code, spec.title, spec.tier, OK, [], note)

    @classmethod
    def unknown(cls, spec: "CheckSpec", note: str) -> "CheckResult":
        return cls(spec.code, spec.title, spec.tier, UNKNOWN, [], note)

    @classmethod
    def of(cls, spec: "CheckSpec", findings: list[Finding], note: str = "") -> "CheckResult":
        status = VIOLATION if findings else OK
        return cls(spec.code, spec.title, spec.tier, status, findings, note)


@dataclass(frozen=True)
class CheckSpec:
    code: str
    title: str
    tier: str  # base | public
    func: object


REGISTRY: list[CheckSpec] = []


def check(code: str, title: str, tier: str = "base"):
    """Регистрирует проверку. Код совпадает с кодом правила в repo-standard.md (Е1)."""

    def wrap(func):
        spec = CheckSpec(code, title, tier, func)
        REGISTRY.append(spec)
        func.spec = spec
        return func

    return wrap


class Repo:
    """Дерево репозитория плюс дешёвые производные от него (П2: дешёвое раньше дорогого)."""

    def __init__(self, root: Path, excludes: tuple[str, ...] = DEFAULT_EXCLUDES):
        self.root = root.resolve()
        self.excludes = excludes
        self.git_available = (self.root / ".git").exists() and _has_git()
        self.files = self._collect_files()
        self._text_cache: dict[str, str | None] = {}

    def _collect_files(self) -> list[str]:
        if self.git_available:
            out = subprocess.run(
                ["git", "-C", str(self.root), "ls-files", "-z"],
                capture_output=True,
                text=True,
                check=False,
            )
            if out.returncode == 0:
                raw = [p for p in out.stdout.split("\0") if p]
                return [p for p in raw if not self._excluded(p)]
        raw = []
        for path in self.root.rglob("*"):
            if path.is_file():
                rel = path.relative_to(self.root).as_posix()
                if not self._excluded(rel):
                    raw.append(rel)
        return sorted(raw)

    def _excluded(self, rel: str) -> bool:
        return any(fnmatch.fnmatch(rel, pattern) for pattern in self.excludes)

    def exists(self, *candidates: str) -> str | None:
        for candidate in candidates:
            if (self.root / candidate).is_file():
                return candidate
        return None

    def by_suffix(self, *suffixes: str) -> list[str]:
        return [f for f in self.files if f.endswith(suffixes)]

    def root_files(self) -> list[str]:
        return [f for f in self.files if "/" not in f]

    def text(self, rel: str) -> str | None:
        """Текст файла; None — двоичный или нечитаемый (исход «не смогли» на уровне файла)."""
        if rel in self._text_cache:
            return self._text_cache[rel]
        path = self.root / rel
        value: str | None
        try:
            data = path.read_bytes()
            if b"\0" in data[:4096]:
                value = None
            else:
                value = data.decode("utf-8", errors="replace")
        except OSError:
            value = None
        self._text_cache[rel] = value
        return value

    def size_kb(self, rel: str) -> int | None:
        try:
            return (self.root / rel).stat().st_size // 1024
        except OSError:
            return None

    def tags(self) -> list[str] | None:
        if not self.git_available:
            return None
        out = subprocess.run(
            ["git", "-C", str(self.root), "tag", "--list"],
            capture_output=True,
            text=True,
            check=False,
        )
        if out.returncode != 0:
            return None
        return [t for t in out.stdout.split("\n") if t]


def _has_git() -> bool:
    try:
        subprocess.run(["git", "--version"], capture_output=True, check=False)
        return True
    except (OSError, FileNotFoundError):
        return False


def run_checks(repo: Repo, tier: str) -> list[CheckResult]:
    wanted = {"base"} if tier == "base" else {"base", "public"}
    results = []
    for spec in REGISTRY:
        if spec.tier not in wanted:
            continue
        try:
            results.append(spec.func(repo, spec))
        except Exception as exc:  # проверка сломалась — это «не смогли», не «годно» (Р1)
            results.append(CheckResult.unknown(spec, f"проверка упала: {exc!r}"))
    return results


def summarise(results: list[CheckResult]) -> dict[str, int]:
    return {
        "checked": len(results),
        "violations": sum(1 for r in results if r.status == VIOLATION),
        "unknown": sum(1 for r in results if r.status == UNKNOWN),
        "findings": sum(len(r.findings) for r in results),
    }


def exit_code(results: list[CheckResult]) -> int:
    """0 — годно; 1 — есть нарушения; 2 — нарушений нет, но что-то не смогли проверить."""
    summary = summarise(results)
    if summary["violations"]:
        return 1
    if summary["unknown"]:
        return 2
    return 0


def render_text(results: list[CheckResult], repo: Repo, limit: int = 5) -> str:
    lines = [f"repo-lint: {repo.root}", ""]
    for result in sorted(results, key=lambda r: (r.status != VIOLATION, r.code)):
        mark = {OK: "годно", VIOLATION: "НАРУШЕНИЕ", UNKNOWN: "не смогли"}[result.status]
        head = f"[{mark}] {result.code} {result.title}"
        if result.findings:
            head += f" — {len(result.findings)}"
        if result.note:
            head += f" ({result.note})"
        lines.append(head)
        for finding in result.findings[:limit]:
            place = finding.path if finding.line is None else f"{finding.path}:{finding.line}"
            lines.append(f"    {place} — {finding.message}")
        if len(result.findings) > limit:
            lines.append(f"    … ещё {len(result.findings) - limit}")
    summary = summarise(results)
    lines += [
        "",
        f"проверено {summary['checked']}, "
        f"нарушений {summary['violations']}, "
        f"не смогли {summary['unknown']} "
        f"(находок всего {summary['findings']})",
    ]
    return "\n".join(lines)
