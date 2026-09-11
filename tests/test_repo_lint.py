"""Тесты прибора.

Пороговые значения здесь — литералы, а не импорт из `repo_lint.checks` (правило Т2):
импортированное ожидание поедет вместе с кодом и промолчит. Поэтому подмена константы
в модуле обязана красить эти тесты — это и проверяет цель `make mutate`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from repo_lint import Repo, exit_code, render_text, run_checks, summarise  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DIRTY = ROOT / "fixtures" / "dirty"
CLEAN = ROOT / "fixtures" / "clean"

# Каждый класс нарушения базовой ступени обязан быть представлен в грязной фикстуре.
# С1 и С6 проверяются отдельно: их пороги требуют репозитория, собранного под порог.
DIRTY_EXPECTED = [
    "С2", "С3", "С4", "С5",
    "К1", "К2", "К3", "К4", "К5", "К6",
    "Д1", "Д2", "Д3", "Д4", "Д5",
    "Б1", "Б2",
    "А1", "А2", "А3", "А4", "А5",
]


def status_map(root: Path, tier: str = "base") -> dict[str, str]:
    repo = Repo(root)
    return {r.code: r.status for r in run_checks(repo, tier)}


def make_repo(tmp_path: Path, files: dict[str, str | int]) -> Path:
    """Собирает микро-репозиторий; int в значении — размер файла в килобайтах."""
    for rel, content in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, int):
            path.write_bytes(b"x" * content * 1024)
        else:
            path.write_text(content, encoding="utf-8")
    return tmp_path


# ------------------------------------------------------------------ негативный контроль


def test_clean_fixture_is_silent():
    """Вход, на котором прибор обязан молчать (И5). Иначе он меряет не то."""
    repo = Repo(CLEAN)
    results = run_checks(repo, "base")
    assert summarise(results)["violations"] == 0, render_text(results, repo)
    assert summarise(results)["unknown"] == 0, render_text(results, repo)
    assert exit_code(results) == 0


@pytest.mark.parametrize("code", DIRTY_EXPECTED)
def test_dirty_fixture_flags_every_class(code):
    """Вход, на котором прибор обязан шевельнуться — по каждому классу отдельно (И5)."""
    assert status_map(DIRTY).get(code) == "violation"


def test_dirty_fixture_fails_overall():
    repo = Repo(DIRTY)
    results = run_checks(repo, "base")
    assert exit_code(results) == 1
    assert summarise(results)["violations"] >= len(DIRTY_EXPECTED)


# ---------------------------------------------------------------------- пороги, оба края


@pytest.mark.parametrize("count,expected", [(25, "ok"), (26, "violation")])
def test_root_clutter_threshold(tmp_path, count, expected):
    files = {f"file{i}.txt": "x" for i in range(count)}
    assert status_map(make_repo(tmp_path, files))["С1"] == expected


@pytest.mark.parametrize("size_kb,expected", [(1024, "ok"), (1025, "violation")])
def test_big_blob_threshold(tmp_path, size_kb, expected):
    assert status_map(make_repo(tmp_path, {"asset.bin": size_kb}))["С6"] == expected


@pytest.mark.parametrize("count,expected", [(10, "ok"), (11, "violation")])
def test_docs_flat_threshold(tmp_path, count, expected):
    files = {"docs/README.md": "# Индекс\n" + "".join(f"- [d{i}](d{i}.md)\n" for i in range(count))}
    for i in range(count):
        files[f"docs/d{i}.md"] = f"# d{i}\n"
    assert status_map(make_repo(tmp_path, files))["Д3"] == expected


# ------------------------------------------------------------------- три исхода, не два


def test_unmeasurable_is_not_success(tmp_path):
    """Нет workflow — это «не смогли», а не «годно», и код возврата 2, а не 0 (Р1, Р2)."""
    repo = Repo(make_repo(tmp_path, {"README.md": "# x\n"}))
    results = run_checks(repo, "base")
    ci = {r.code: r for r in results if r.code.startswith("А")}
    assert all(r.status == "unknown" for r in ci.values())
    assert exit_code([r for r in results if r.status != "violation"]) == 2


def test_report_prints_three_numbers():
    repo = Repo(DIRTY)
    text = render_text(run_checks(repo, "base"), repo)
    assert "проверено " in text and "нарушений " in text and "не смогли " in text


def test_broken_check_counts_as_unknown(monkeypatch):
    """Упавшая проверка не исчезает и не засчитывается как успех."""
    from repo_lint import core

    spec = next(s for s in core.REGISTRY if s.code == "С1")

    def boom(repo, spec):
        raise RuntimeError("прибор сломался")

    broken = core.CheckSpec(spec.code, spec.title, spec.tier, boom)
    monkeypatch.setattr(core, "REGISTRY", [broken])
    results = core.run_checks(Repo(CLEAN), "base")
    assert [r.status for r in results] == ["unknown"]
    assert core.exit_code(results) == 2


# ------------------------------------------------------------------- публичная ступень


def test_public_tier_adds_checks():
    base = status_map(CLEAN, "base")
    public = status_map(CLEAN, "public")
    assert "Ж1" not in base
    assert public["Ж1"] == "violation"  # LICENSE в фикстуре нет
    assert public["Х1"] == "unknown"  # человеческая часть не сворачивается в успех


def test_public_accepts_full_set(tmp_path):
    files = {
        "README.md": "# Проект\n\n## Как запустить\n\n```\nmake test\n```\n"
        + "Подробности ниже. " * 20
        + "\n![ci](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)\n",
        "LICENSE": "MIT License\n\nCopyright (c) 2026\n",
        "SECURITY.md": "# Безопасность\n",
        "CONTRIBUTING.md": "# Как участвовать\n",
        "CODE_OF_CONDUCT.md": "# Правила\n",
        "CODEOWNERS": "* @owner\n",
        "CHANGELOG.md": "# Changelog\n\n## [0.1.0] - 2026-09-11\n",
        ".github/ISSUE_TEMPLATE/bug.md": "---\nname: bug\n---\n",
        ".github/pull_request_template.md": "## Что меняется\n",
        ".github/dependabot.yml": "version: 2\nupdates: []\n",
        ".github/workflows/ci.yml": (
            "name: ci\non: [push]\npermissions:\n  contents: read\n"
            "concurrency:\n  group: ci\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
            "    steps:\n      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683\n"
        ),
        ".gitignore": "__pycache__/\n.venv/\n.DS_Store\n",
    }
    statuses = status_map(make_repo(tmp_path, files), "public")
    assert statuses["Ж1"] == "ok"
    assert statuses["Ж2"] == "ok"
    assert statuses["Ж3"] == "ok"
    assert statuses["Ж5"] == "ok"
    assert statuses["Ж6"] == "ok"
    # Каталог без git — теги прочитать нечем: третий исход, а не успех (Р1).
    assert statuses["Ж4"] == "unknown"


# ------------------------------------------------------------------------------- CLI


@pytest.mark.parametrize("target,expected", [(CLEAN, 0), (DIRTY, 1)])
def test_cli_exit_codes(target, expected):
    done = subprocess.run(
        [sys.executable, "-m", "repo_lint", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert done.returncode == expected, done.stdout + done.stderr


def test_cli_json_shape():
    done = subprocess.run(
        [sys.executable, "-m", "repo_lint", str(CLEAN), "--format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    import json

    payload = json.loads(done.stdout)
    assert set(payload["summary"]) == {"checked", "violations", "unknown", "findings"}
    assert payload["summary"]["violations"] == 0


# ------------------------------------------- норма и прибор не расходятся (Е1, Е2)


def test_rule_codes_match_registry():
    """Каждое правило с пометкой «Прибор» имеет проверку, и наоборот.

    Расхождение текста и прибора чинится в приборе; тест ловит его сразу, а не
    через полгода чтения (правило Е1: одно знание — одно место).
    """
    import re

    from repo_lint import REGISTRY

    norm = (ROOT / "repo-standard.md").read_text(encoding="utf-8")
    documented = {m.split()[0] for m in re.findall(r"Прибор: `([^`]+)`", norm)}
    registered = {spec.code for spec in REGISTRY} - {"Х1"}
    assert documented == registered, {
        "в норме, но не в приборе": sorted(documented - registered),
        "в приборе, но не в норме": sorted(registered - documented),
    }


def test_check_titles_are_unique():
    from repo_lint import REGISTRY

    codes = [spec.code for spec in REGISTRY]
    assert len(codes) == len(set(codes))
