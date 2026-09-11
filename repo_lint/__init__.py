"""repo-lint: прибор соответствия репозитория стандарту оформления."""

from . import checks as _checks  # noqa: F401  регистрация проверок в реестре
from .core import REGISTRY, Repo, exit_code, render_text, run_checks, summarise

__all__ = ["REGISTRY", "Repo", "exit_code", "render_text", "run_checks", "summarise"]
