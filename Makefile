.PHONY: test lint self mutate all

test: ## тесты прибора
	python3 -m pytest tests -q

self: ## прибор проверяет собственный репозиторий (гейт: код возврата 0)
	python3 -m repo_lint . --tier base

mutate: ## подмена констант-решений в обе стороны: тесты обязаны краснеть (Т1)
	python3 scripts/mutate.py

lint: ## синтаксис без внешних зависимостей
	python3 -m compileall -q repo_lint scripts tests

all: lint test self mutate
