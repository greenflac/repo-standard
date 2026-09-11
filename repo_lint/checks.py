"""Проверки стандарта. Код проверки совпадает с кодом правила в repo-standard.md.

Происхождение констант-решений помечено по правилу И4 харнеса.
"""

from __future__ import annotations

import re

from .core import UNKNOWN, CheckResult, CheckSpec, Finding, Repo, check

# ВЫБРАНО (автор стандарта, из наблюдения: izhplasteco — 52 файла в корне, читать невозможно;
# lead_centre — 12, читается сразу). Мутация этого числа обязана красить тест.
ROOT_FILES_MAX = 25
# ВЫБРАНО: порог «бинарь, о котором надо принять решение»; git хранит его вечно.
BIG_BLOB_KB = 1024
# ВЫБРАНО: плоский docs/ крупнее этого читается как свалка, а не как документация.
DOCS_FLAT_MAX = 10

CODE_SUFFIXES = (".py", ".js", ".mjs", ".ts", ".php", ".sh", ".css", ".go", ".rb")
TEXT_SUFFIXES = CODE_SUFFIXES + (".md", ".yml", ".yaml", ".json", ".html", ".txt", ".cfg", ".toml")

DEV_ARTIFACT_PATTERNS = (
    r"(^|/)preview-[^/]+$",
    r"(^|/)[^/]*-proto\.[^/]+$",
    r"\.(bak|orig|rej|tmp|swp)$",
    r"~$",
    r"(^|/)[^/]*\.(draft|copy)\.[^/]+$",
)
WORKLOG_PATTERNS = (
    r"(^|/)HANDOFF[_-][^/]+\.md$",
    r"(^|/)[^/]*-session-[^/]*\.md$",
    r"(^|/)[^/]*\d{4}-\d{2}-\d{2}[^/]*\.md$",
    r"(^|/)[^/]*(audit|отчет|отчёт|аудит)[^/]*\.md$",
)
WORKLOG_HOMES = ("docs/journal/", "docs/archive/", ".handoff/")
GENERATED_PATTERNS = (
    r"(^|/)__pycache__/",
    r"(^|/)node_modules/",
    r"(^|/)\.DS_Store$",
    r"(^|/)Thumbs\.db$",
    r"\.pyc$",
    r"(^|/)\.venv/",
    r"\.log$",
)

COMMENT_RE = re.compile(r"^\s*(?P<kind>#|//|/\*|\*(?!/)|<!--)\s?(?P<body>.*?)\s*(\*/|-->)?\s*$")
# Строка внутри блочного комментария — чаще проза документации, чем брошенный код,
# поэтому правила К1 и К2 смотрят только на однострочные комментарии.
LINE_COMMENT_KINDS = ("#", "//")
# Глаголы пересказа: комментарий, который называет действие следующей строки её же словами.
RESTATE_VERB_RE = re.compile(
    r"^(set|get|增|increment|decrement|add|call|return|init|initialize|create|delete|remove|"
    r"update|check|loop|iterate|assign|define|"
    r"устанавлива\w+|увеличива\w+|уменьша\w+|вызыва\w+|возвраща\w+|создаём|создаем|"
    r"создать|удаля\w+|обновля\w+|проверя\w+|присваива\w+|объявля\w+)\b",
    re.IGNORECASE,
)
CHATTER_RE = re.compile(
    r"(как договорились|как просили|как обсуждали|теперь (?:исправлено|работает|стало)|"
    r"я (?:добавил|исправил|изменил|убрал|сделал)|мы (?:добавили|исправили|решили)|"
    r"финальная версия|итоговая версия|исправлено по замечани|"
    r"\b(claude|chatgpt|gpt-4|копилот|copilot|нейросет)\b|"
    r"(?:as (?:we )?discussed|as requested|i (?:added|fixed|changed|removed)|final version))",
    re.IGNORECASE,
)
AUTHOR_STAMP_RE = re.compile(
    r"(@author\b|\bавтор\s*:|\bcreated by\b|\bдата создания\b|\bmodified by\b|"
    r"\bcreated\s*:\s*\d{2,4}[-./]\d{1,2})",
    re.IGNORECASE,
)
TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX|ВРЕМЕННО|ЗАГЛУШКА)\b")
# Метка, взятая в кавычки или обратные кавычки, либо стоящая в альтернативе регулярного
# выражения, — это разговор о метке (норма, тест, сам прибор), а не незакрытая работа.
TODO_MENTION_RE = re.compile(
    r"([`'\"][^`'\"]*\b(TODO|FIXME|HACK|XXX)\b[^`'\"]*[`'\"]|\|\s*(TODO|FIXME|HACK|XXX)\s*\||"
    r"\((TODO|FIXME|HACK|XXX)\||\b(TODO|FIXME|HACK|XXX)\)\B)"
)
DEBT_RE = re.compile(r"\bDEBT\(\d{4}-\d{2}-\d{2}\)")
CODE_LOOKING_RE = re.compile(
    r"(;\s*$|\{\s*$|\}\s*$"
    r"|^\s*(if|for|while|return|function|def|const|let|var|echo|print|import|from)\b.*[:;)]\s*$"
    r"|^\s*\w+\s*=\s*[^=\s].*;\s*$"
    r"|^\s*\w+(\.\w+)*\([^)]*\)\s*;\s*$)"
)
SECRET_RE = re.compile(
    r"(-----BEGIN (?:RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----"
    r"|\b(?:password|passwd|pwd|secret|api[_-]?key|token)\s*[:=]\s*['\"][^'\"\s]{8,}['\"]"
    r"|\bAKIA[0-9A-Z]{16}\b"
    r"|\bghp_[A-Za-z0-9]{20,}\b"
    r"|\bsk-[A-Za-z0-9]{20,}\b)",
    re.IGNORECASE,
)
PLACEHOLDER_SECRET_RE = re.compile(
    r"(xxx|your[_-]?|placeholder|example|changeme|<[^>]+>|\.\.\.|здесь|укажите|password_here)",
    re.IGNORECASE,
)
DEBUG_RE = {
    ".js": re.compile(r"(^|[^.\w])console\.(log|debug|dir)\s*\("),
    ".mjs": re.compile(r"(^|[^.\w])console\.(log|debug|dir)\s*\("),
    ".ts": re.compile(r"(^|[^.\w])console\.(log|debug|dir)\s*\("),
    ".php": re.compile(r"\b(var_dump|print_r|dd)\s*\("),
}
# Комментарий, объясняющий причину, правилом К1 не трогается — он и есть норма.
WHY_MARKER_RE = re.compile(
    r"(потому|чтобы|чтоб|иначе|поэтому|так как|ради|правило\s+[А-ЯA-Z]\d|"
    r"because|so that|otherwise|to avoid|since)",
    re.IGNORECASE,
)
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)#][^)]*)\)")
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)", re.MULTILINE)
SHA_PIN_RE = re.compile(r"@[0-9a-f]{40}$")


def _lines(repo: Repo, rel: str) -> list[str]:
    text = repo.text(rel)
    return text.splitlines() if text is not None else []


def _comment_bodies(repo: Repo, rel: str, kinds: tuple[str, ...] | None = None):
    for number, line in enumerate(_lines(repo, rel), start=1):
        match = COMMENT_RE.match(line)
        if match and match.group("body"):
            if kinds is not None and match.group("kind") not in kinds:
                continue
            yield number, line, match.group("body")


def _code_files(repo: Repo) -> list[str]:
    return [f for f in repo.files if f.endswith(CODE_SUFFIXES)]


# ---------------------------------------------------------------- С. структура


@check("С1", "корень не захламлён", "base")
def root_clutter(repo: Repo, spec: CheckSpec) -> CheckResult:
    root = repo.root_files()
    if len(root) > ROOT_FILES_MAX:
        return CheckResult.of(
            spec,
            [Finding(".", None, f"файлов в корне {len(root)}, порог {ROOT_FILES_MAX}")],
        )
    return CheckResult.ok(spec, f"файлов в корне {len(root)}")


@check("С2", "артефактов разработки нет в дереве", "base")
def dev_artifacts(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = [
        Finding(f, None, "артефакт разработки")
        for f in repo.files
        if any(re.search(p, f) for p in DEV_ARTIFACT_PATTERNS)
    ]
    return CheckResult.of(spec, findings)


@check("С3", "рабочие записи лежат отдельно от продукта", "base")
def worklog_placement(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for f in repo.files:
        if not any(re.search(p, f) for p in WORKLOG_PATTERNS):
            continue
        if f.startswith(WORKLOG_HOMES):
            continue
        findings.append(Finding(f, None, f"рабочая запись вне {WORKLOG_HOMES[0]}"))
    return CheckResult.of(spec, findings)


@check("С4", "сгенерированное не в git", "base")
def generated_tracked(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = [
        Finding(f, None, "служебный или сгенерированный файл в индексе")
        for f in repo.files
        if any(re.search(p, f) for p in GENERATED_PATTERNS)
    ]
    return CheckResult.of(spec, findings)


@check("С5", ".gitignore есть и покрывает мусор", "base")
def gitignore(repo: Repo, spec: CheckSpec) -> CheckResult:
    rel = repo.exists(".gitignore")
    if rel is None:
        return CheckResult.of(spec, [Finding(".gitignore", None, "файла нет")])
    body = repo.text(rel) or ""
    needed = {".DS_Store": any(f.endswith((".html", ".css", ".js", ".php")) for f in repo.files)}
    if any(f.endswith(".py") for f in repo.files):
        needed["__pycache__"] = True
        needed[".venv"] = True
    if any(f.endswith("package.json") for f in repo.files):
        needed["node_modules"] = True
    findings = [
        Finding(rel, None, f"не покрыт мусор: {token}")
        for token, wanted in needed.items()
        if wanted and token not in body
    ]
    return CheckResult.of(spec, findings)


@check("С6", "крупные бинарники не лежат в git", "base")
def big_blobs(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for f in repo.files:
        size = repo.size_kb(f)
        if size is None:
            continue
        if size > BIG_BLOB_KB:
            findings.append(Finding(f, None, f"{size} КБ, порог {BIG_BLOB_KB} КБ"))
    return CheckResult.of(spec, findings)


# ------------------------------------------------------------ К. код и комментарии


@check("К1", "комментарий не пересказывает код", "base")
def comment_restates_code(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in _code_files(repo):
        lines = _lines(repo, rel)
        for number, _raw, body in _comment_bodies(repo, rel, LINE_COMMENT_KINDS):
            if number >= len(lines):
                continue
            if not RESTATE_VERB_RE.match(body):
                continue
            following = lines[number].strip()
            if not following or COMMENT_RE.match(following):
                continue
            words = {w.lower() for w in re.findall(r"\w{3,}", body)}
            code_words = {w.lower() for w in re.findall(r"\w{3,}", following)}
            overlap = len(words & code_words)
            if WHY_MARKER_RE.search(body):
                continue
            if (len(words) <= 6 and overlap >= 2) or (len(words) <= 5 and overlap >= 1):
                findings.append(Finding(rel, number, f"пересказ следующей строки: {body[:60]}"))
    return CheckResult.of(spec, findings, note="эвристика")


@check("К2", "закомментированного кода нет", "base")
def commented_out_code(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in _code_files(repo):
        for number, _raw, body in _comment_bodies(repo, rel, LINE_COMMENT_KINDS):
            if len(body) < 6 or TODO_RE.search(body) or DEBT_RE.search(body):
                continue
            if CODE_LOOKING_RE.search(body) and not re.search(r"[а-яА-Я]{4,}", body):
                findings.append(Finding(rel, number, f"похоже на код: {body[:60]}"))
    return CheckResult.of(spec, findings)


@check("К3", "в комментариях нет следов диалога", "base")
def chatter_comments(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in repo.by_suffix(*CODE_SUFFIXES, ".html"):
        for number, _raw, body in _comment_bodies(repo, rel):
            if CHATTER_RE.search(body):
                findings.append(Finding(rel, number, f"реплика в комментарии: {body[:60]}"))
    return CheckResult.of(spec, findings)


@check("К4", "авторства и дат нет в шапках файлов", "base")
def author_stamp(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in repo.by_suffix(*CODE_SUFFIXES, ".html"):
        for number, _raw, body in _comment_bodies(repo, rel):
            if AUTHOR_STAMP_RE.search(body):
                findings.append(Finding(rel, number, f"штамп авторства: {body[:60]}"))
    return CheckResult.of(spec, findings)


@check("К5", "незакрытая работа помечена DEBT(дата)", "base")
def todo_without_debt(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in repo.by_suffix(*TEXT_SUFFIXES):
        for number, line in enumerate(_lines(repo, rel), start=1):
            if not TODO_RE.search(line) or DEBT_RE.search(line):
                continue
            if TODO_MENTION_RE.search(line):
                continue
            if True:
                findings.append(Finding(rel, number, f"метка без даты: {line.strip()[:60]}"))
    return CheckResult.of(spec, findings)


@check("К6", "отладочной печати нет", "base")
def debug_output(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in repo.files:
        suffix = "." + rel.rsplit(".", 1)[-1] if "." in rel else ""
        pattern = DEBUG_RE.get(suffix)
        if pattern is None:
            continue
        if "/tests/" in rel or rel.startswith("tests/") or "/scripts/" in rel:
            continue
        for number, line in enumerate(_lines(repo, rel), start=1):
            if pattern.search(line) and not COMMENT_RE.match(line):
                findings.append(Finding(rel, number, f"отладочная печать: {line.strip()[:60]}"))
    return CheckResult.of(spec, findings)


# ------------------------------------------------------------------ Д. документация


@check("Д1", "README отвечает на четыре вопроса", "base")
def readme_shape(repo: Repo, spec: CheckSpec) -> CheckResult:
    rel = repo.exists("README.md", "README.rst", "readme.md")
    if rel is None:
        return CheckResult.of(spec, [Finding("README.md", None, "файла нет")])
    body = repo.text(rel) or ""
    findings = []
    if len(body) < 400:
        findings.append(Finding(rel, None, f"{len(body)} байт — короче любого полезного README"))
    if not re.search(r"^#\s+\S", body, re.MULTILINE):
        findings.append(Finding(rel, None, "нет заголовка H1"))
    if "```" not in body and not re.search(r"^\s{4}\S", body, re.MULTILINE):
        findings.append(Finding(rel, None, "нет ни одной команды запуска"))
    if not re.search(
        r"(как запустить|запуск|установк|использован|usage|install|getting started|quick ?start)",
        body,
        re.IGNORECASE,
    ):
        findings.append(Finding(rel, None, "нет секции запуска или установки"))
    return CheckResult.of(spec, findings)


@check("Д2", "обещания README подкреплены командой", "base")
def readme_claims(repo: Repo, spec: CheckSpec) -> CheckResult:
    rel = repo.exists("README.md", "readme.md")
    if rel is None:
        return CheckResult.unknown(spec, "README не найден")
    lines = _lines(repo, rel)
    claim_re = re.compile(r"(\d+\s*%|\bв\s+\d+(?:[.,]\d+)?\s*раз|\b\d+x\b)")
    evidence_re = re.compile(r"(```|\bкоманда\b|\bвывод\b|\bпрогон\b|\bmake\b|\$ )", re.IGNORECASE)
    findings = []
    for number, line in enumerate(lines, start=1):
        if not claim_re.search(line):
            continue
        window = lines[max(0, number - 9) : number + 8]
        if not any(evidence_re.search(w) for w in window):
            findings.append(Finding(rel, number, f"число без команды рядом: {line.strip()[:60]}"))
    return CheckResult.of(spec, findings, note="эвристика")


@check("Д3", "docs/ не плоская свалка", "base")
def docs_flat(repo: Repo, spec: CheckSpec) -> CheckResult:
    docs = [f for f in repo.files if f.startswith("docs/")]
    if not docs:
        return CheckResult.ok(spec, "docs/ нет")
    flat = [
        f
        for f in docs
        if f.count("/") == 1
        and f.endswith(".md")
        and f.rsplit("/", 1)[-1] not in ("README.md", "index.md")
    ]
    if len(flat) > DOCS_FLAT_MAX:
        return CheckResult.of(
            spec,
            [Finding("docs/", None, f"{len(flat)} файлов одним уровнем, порог {DOCS_FLAT_MAX}")],
            note="измеримая тень правила о жанрах",
        )
    return CheckResult.ok(spec, f"файлов первого уровня {len(flat)}")


@check("Д4", "у docs/ есть индекс, документов-сирот нет", "base")
def orphan_docs(repo: Repo, spec: CheckSpec) -> CheckResult:
    docs = [f for f in repo.files if f.startswith("docs/") and f.endswith(".md")]
    if not docs:
        return CheckResult.ok(spec, "docs/ нет")
    findings = []
    if repo.exists("docs/README.md") is None and repo.exists("docs/index.md") is None:
        findings.append(Finding("docs/README.md", None, "индекса нет"))
    mentions = "\n".join(repo.text(f) or "" for f in repo.by_suffix(".md"))
    for doc in docs:
        name = doc.rsplit("/", 1)[-1]
        if name in ("README.md", "index.md"):
            continue
        if doc.startswith(WORKLOG_HOMES):  # журнал сессий — не документация продукта (С3)
            continue
        if name not in mentions and doc not in mentions:
            findings.append(Finding(doc, None, "ни одной ссылки из других документов"))
    return CheckResult.of(spec, findings)


@check("Д5", "относительные ссылки в markdown не битые", "base")
def broken_links(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in repo.by_suffix(".md"):
        base = repo.root / rel
        for number, line in enumerate(_lines(repo, rel), start=1):
            for target in MD_LINK_RE.findall(line):
                target = target.split(" ")[0].split("#")[0].strip()
                if not target or re.match(r"^[a-z]+:", target) or target.startswith("/"):
                    continue
                if not (base.parent / target).exists():
                    findings.append(Finding(rel, number, f"ссылка в никуда: {target}"))
    return CheckResult.of(spec, findings)


# --------------------------------------------------------------- Б. секреты


@check("Б1", "секретов в дереве нет", "base")
def secrets(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    for rel in repo.files:
        name = rel.rsplit("/", 1)[-1]
        if name == ".env" or (name.startswith(".env.") and "example" not in name and "sample" not in name):
            findings.append(Finding(rel, None, "файл окружения в git"))
        if "example" in rel or "sample" in rel or rel.endswith(".md"):
            continue
        if not rel.endswith(TEXT_SUFFIXES) and "." in name:
            continue
        for number, line in enumerate(_lines(repo, rel), start=1):
            match = SECRET_RE.search(line)
            if match and not PLACEHOLDER_SECRET_RE.search(match.group(0)):
                findings.append(Finding(rel, number, "похоже на секрет в коде"))
    return CheckResult.of(spec, findings)


@check("Б2", "пример конфигурации есть", "base")
def config_example(repo: Repo, spec: CheckSpec) -> CheckResult:
    uses_env = any(
        re.search(r"(getenv\(|os\.environ[.\[]|process\.env\.|\$_ENV\[)", repo.text(f) or "")
        for f in _code_files(repo)
    )
    if not uses_env:
        return CheckResult.ok(spec, "переменные окружения не используются")
    example = any(
        ("example" in f or "sample" in f) and ("env" in f.lower() or "config" in f.lower())
        for f in repo.files
    )
    if example:
        return CheckResult.ok(spec)
    return CheckResult.of(spec, [Finding(".", None, "код читает окружение, файла-примера нет")])


# ------------------------------------------------------------------- А. CI


def _workflows(repo: Repo) -> list[str]:
    return [
        f
        for f in repo.files
        if f.startswith(".github/workflows/") and f.endswith((".yml", ".yaml"))
    ]


@check("А1", "у workflow задан permissions", "base")
def workflow_permissions(repo: Repo, spec: CheckSpec) -> CheckResult:
    flows = _workflows(repo)
    if not flows:
        return CheckResult.unknown(spec, "workflow не найдены")
    findings = [
        Finding(f, None, "нет ключа permissions")
        for f in flows
        if not re.search(r"^\s*permissions:", repo.text(f) or "", re.MULTILINE)
    ]
    return CheckResult.of(spec, findings)


@check("А2", "нет опасного pull_request_target с чужим кодом", "base")
def dangerous_workflow(repo: Repo, spec: CheckSpec) -> CheckResult:
    flows = _workflows(repo)
    if not flows:
        return CheckResult.unknown(spec, "workflow не найдены")
    findings = []
    for f in flows:
        body = repo.text(f) or ""
        if "pull_request_target" in body and re.search(r"ref:\s*\$\{\{\s*github\.event\.pull_request", body):
            findings.append(Finding(f, None, "pull_request_target с checkout головы PR"))
    return CheckResult.of(spec, findings)


@check("А3", "действия запинены", "base")
def unpinned_actions(repo: Repo, spec: CheckSpec) -> CheckResult:
    flows = _workflows(repo)
    if not flows:
        return CheckResult.unknown(spec, "workflow не найдены")
    findings = []
    for f in flows:
        for number, line in enumerate(_lines(repo, f), start=1):
            match = USES_RE.match(line)
            if not match:
                continue
            ref = match.group(1)
            if ref.startswith("./") or ref.startswith("docker://"):
                continue
            if "@" not in ref or ref.endswith(("@main", "@master", "@latest")):
                findings.append(Finding(f, number, f"плавающая ссылка: {ref}"))
    return CheckResult.of(spec, findings)


@check("А4", "concurrency задан", "base")
def concurrency(repo: Repo, spec: CheckSpec) -> CheckResult:
    flows = _workflows(repo)
    if not flows:
        return CheckResult.unknown(spec, "workflow не найдены")
    findings = [
        Finding(f, None, "нет ключа concurrency")
        for f in flows
        if not re.search(r"^\s*concurrency:", repo.text(f) or "", re.MULTILINE)
    ]
    return CheckResult.of(spec, findings)


@check("А5", "зелень не выдаётся за проверку", "base")
def green_washing(repo: Repo, spec: CheckSpec) -> CheckResult:
    flows = _workflows(repo)
    if not flows:
        return CheckResult.unknown(spec, "workflow не найдены")
    findings = []
    for f in flows:
        for number, line in enumerate(_lines(repo, f), start=1):
            if re.search(r"continue-on-error:\s*true", line):
                findings.append(Finding(f, number, "шаг не может покрасить сборку"))
            if re.search(r"(nick-fields/retry|--reruns|retry:\s*\d)", line):
                findings.append(Finding(f, number, "ретрай проверки (Т7)"))
    return CheckResult.of(spec, findings)


# ------------------------------------------------------- Ж. публичная ступень


@check("Ж1", "LICENSE есть", "public")
def license_present(repo: Repo, spec: CheckSpec) -> CheckResult:
    rel = repo.exists("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
    if rel is None:
        return CheckResult.of(spec, [Finding("LICENSE", None, "файла нет")])
    body = (repo.text(rel) or "")[:4000]
    known = re.search(r"(MIT License|Apache License|GNU GENERAL PUBLIC|BSD \d-Clause|Mozilla Public)", body)
    if not known:
        return CheckResult.of(spec, [Finding(rel, None, "лицензия не распознана по тексту")])
    return CheckResult.ok(spec, known.group(1))


@check("Ж2", "community-файлы на месте", "public")
def community_files(repo: Repo, spec: CheckSpec) -> CheckResult:
    wanted = ("SECURITY.md", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "CODEOWNERS")
    findings = []
    for name in wanted:
        if repo.exists(name, f".github/{name}", f"docs/{name}") is None:
            findings.append(Finding(name, None, "файла нет"))
    return CheckResult.of(spec, findings)


@check("Ж3", "шаблоны issue и PR есть", "public")
def templates(repo: Repo, spec: CheckSpec) -> CheckResult:
    has_issue = any(f.startswith(".github/ISSUE_TEMPLATE") for f in repo.files)
    has_pr = repo.exists(
        ".github/pull_request_template.md",
        ".github/PULL_REQUEST_TEMPLATE.md",
        "PULL_REQUEST_TEMPLATE.md",
    )
    findings = []
    if not has_issue:
        findings.append(Finding(".github/ISSUE_TEMPLATE", None, "шаблонов issue нет"))
    if has_pr is None:
        findings.append(Finding(".github/pull_request_template.md", None, "шаблона PR нет"))
    return CheckResult.of(spec, findings)


@check("Ж4", "CHANGELOG и теги SemVer", "public")
def changelog(repo: Repo, spec: CheckSpec) -> CheckResult:
    findings = []
    rel = repo.exists("CHANGELOG.md", "docs/CHANGELOG.md")
    if rel is None:
        findings.append(Finding("CHANGELOG.md", None, "файла нет"))
    tags = repo.tags()
    if tags is None:
        return CheckResult(spec.code, spec.title, spec.tier, UNKNOWN, findings, "git недоступен, теги не прочитаны")
    good = [t for t in tags if re.match(r"^v?\d+\.\d+\.\d+", t)]
    if tags and not good:
        findings.append(Finding(".", None, f"теги есть ({len(tags)}), ни один не по SemVer"))
    return CheckResult.of(spec, findings)


@check("Ж5", "бейдж сборки указывает на свой workflow", "public")
def ci_badge(repo: Repo, spec: CheckSpec) -> CheckResult:
    rel = repo.exists("README.md")
    if rel is None:
        return CheckResult.unknown(spec, "README не найден")
    body = repo.text(rel) or ""
    badges = re.findall(r"!\[[^\]]*\]\((https://github\.com/[^)]+/badge\.svg[^)]*)\)", body)
    flows = {f.rsplit("/", 1)[-1] for f in _workflows(repo)}
    if not badges:
        return CheckResult.of(spec, [Finding(rel, None, "бейджа сборки нет")])
    findings = [
        Finding(rel, None, f"бейдж не указывает ни на один workflow репозитория: {b}")
        for b in badges
        if not any(name in b for name in flows)
    ]
    return CheckResult.of(spec, findings)


@check("Ж6", "действия запинены по SHA, dependabot включён", "public")
def sha_pinning(repo: Repo, spec: CheckSpec) -> CheckResult:
    flows = _workflows(repo)
    if not flows:
        return CheckResult.unknown(spec, "workflow не найдены")
    findings = []
    for f in flows:
        for number, line in enumerate(_lines(repo, f), start=1):
            match = USES_RE.match(line)
            if match and not match.group(1).startswith(("./", "docker://")):
                if not SHA_PIN_RE.search(match.group(1)):
                    findings.append(Finding(f, number, f"не по SHA: {match.group(1)}"))
    if repo.exists(".github/dependabot.yml", ".github/dependabot.yaml") is None:
        findings.append(Finding(".github/dependabot.yml", None, "файла нет"))
    return CheckResult.of(spec, findings)


@check("Х1", "проверяется человеком, не прибором", "public")
def human_only(repo: Repo, spec: CheckSpec) -> CheckResult:
    return CheckResult.unknown(
        spec,
        "защита ветки, обязательность ревью, секреты в настройках, смысл README — глазами (Р1)",
    )
