PYTHON ?= python3

.PHONY: help check-plan test-plan render-plan next

help:
	@printf '%s\n' 'check-plan  Validate backlog, links, publication safety and generated progress' 'test-plan   Run deterministic planning-tool tests' 'render-plan Regenerate BACKLOG.md and STATUS.md' 'next        List dependency-ready tasks in enabled scopes'

check-plan:
	$(PYTHON) tools/plan.py check

test-plan:
	$(PYTHON) -m unittest discover -s tests -v

render-plan:
	$(PYTHON) tools/plan.py render

next:
	$(PYTHON) tools/plan.py next
