UV ?= uv
PYTHON ?= $(UV) run --locked python
RUFF ?= $(UV) run --locked ruff
GITLEAKS ?= gitleaks
ACTIONLINT ?= actionlint
AUDITOR ?= pip-audit

.PHONY: help sync lock-check validate check-plan test test-plan test-wheel lint format-check render-plan next check-publication check-artifacts audit-dependencies pipeline-help benchmark-fixture

help:
	@printf '%s\n' 'sync         Install the locked package and development tools' 'lock-check   Verify pyproject.toml and uv.lock agree without updating them' 'validate     Lock, plan, full tests, lint and format checks' 'check-plan   Validate backlog, links, publication safety and generated progress' 'test         Run all installed-package and planning tests' 'test-plan    Run only standard-library planning-tool tests' 'test-wheel   Build/install/import a wheel outside the checkout' 'lint         Check Python source, tooling and tests with locked Ruff' 'format-check Check formatting without rewriting files' 'render-plan  Regenerate BACKLOG.md and STATUS.md' 'next         List dependency-ready tasks in enabled scopes'
	@printf '%s\n' 'check-publication Scan exact committed tree/fetched history and frozen workflow policy (pinned tools required)' 'check-artifacts Scan nine built synthetic HTML/CSS/CLI-manifest files (pinned Gitleaks required)' 'audit-dependencies Audit complete committed package inventory without resolution (isolated pinned auditor required)' 'pipeline-help Show independent fixture-only collect/build/check CLI options'
	@printf '%s\n' 'benchmark-fixture Measure fictional full-batch grouping scores; NOT the real gold gate'

sync:
	$(UV) sync --locked

lock-check:
	$(UV) lock --check

validate: lock-check check-plan test lint format-check

check-plan:
	$(PYTHON) tools/plan.py check

test-plan:
	$(PYTHON) -m unittest discover -s tests -p test_plan.py -v

test:
	$(PYTHON) -W error::ResourceWarning -m unittest discover -s tests -v

test-wheel:
	$(PYTHON) tools/check_wheel.py

lint:
	$(RUFF) check src tools tests

format-check:
	$(RUFF) format --check src tools tests

render-plan:
	$(PYTHON) tools/plan.py render

next:
	$(PYTHON) tools/plan.py next

check-publication:
	$(PYTHON) tools/check_security.py publication --gitleaks "$(GITLEAKS)" --actionlint "$(ACTIONLINT)"

check-artifacts:
	$(PYTHON) tools/check_security.py artifacts --directory .local/fixture-sites --gitleaks "$(GITLEAKS)"

audit-dependencies:
	$(PYTHON) tools/check_security.py audit --auditor "$(AUDITOR)"

pipeline-help:
	$(PYTHON) -B -m wrap_brief.cli --help

benchmark-fixture:
	$(PYTHON) -B tools/measure_grouping_fixture.py
