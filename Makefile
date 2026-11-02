PYTHON ?= python3
RUFF ?= ruff

.PHONY: help validate check-plan test-plan render-plan next

help:
	@printf '%s\n' 'validate    All plan checks, tests and Ruff lint/format (requires ruff)' 'check-plan  Validate backlog, links, publication safety and generated progress' 'test-plan   Run deterministic planning-tool tests' 'render-plan Regenerate BACKLOG.md and STATUS.md' 'next        List dependency-ready tasks in enabled scopes'

validate: check-plan test-plan
	$(RUFF) check tools tests
	$(RUFF) format --check tools tests

check-plan:
	$(PYTHON) tools/plan.py check

test-plan:
	$(PYTHON) -m unittest discover -s tests -v

render-plan:
	$(PYTHON) tools/plan.py render

next:
	$(PYTHON) tools/plan.py next
