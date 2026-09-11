"""Точка входа примера: развилка вынесена из main в функцию (правило Т5)."""

import os


def target_url(env: dict) -> str:
    """Адрес читается из окружения: в тестах он подменяется, в проде задаётся деплоем."""
    return env.get("TARGET_URL", "https://example.invalid")


def main() -> int:
    print(target_url(os.environ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
