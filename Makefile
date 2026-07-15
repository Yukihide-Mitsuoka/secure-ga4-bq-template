# Canonical command interface (CLAUDE.md §11) for this template's two toolchains
# (ADR-0003): Terraform roots under infra/envs/<env>/ (modules referenced by tag)
# and the Python inspection engine under src/modules/inspection (uv-managed).
# The heavier layered-foundations reference stays available in profiles/terraform-gcp/.

.PHONY: setup format lint test test-unit test-integration coverage build run \
        security-scan sbom clean help doctor plan inspect report-ai remediation-draft \
        render-inspection-menu

FILE ?=
ENV ?= dev

help: ## List available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

setup: ## Install toolchain: python deps (uv sync) + git hooks — idempotent
	uv sync
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit install --hook-type pre-commit --hook-type pre-push; else echo "pre-commit not installed — local hooks skipped (CI runs the same gates)"; fi

format: ## Auto-format terraform + python (all, or FILE=<path>)
ifneq ($(FILE),)
	@case "$(FILE)" in \
		*.tf|*.tfvars) terraform fmt "$(FILE)" ;; \
		*.py) uv run ruff format "$(FILE)" && uv run ruff check --fix-only "$(FILE)" ;; \
		*) : ;; \
	esac
else
	terraform fmt -recursive infra
	uv run ruff format .
	uv run ruff check --fix-only .
endif

lint: ## Check-only, zero warnings (COD-001); never fixes
	terraform fmt -check -recursive infra
	@if command -v tflint >/dev/null 2>&1; then tflint --recursive --chdir infra; else echo "tflint not installed — CI still enforces it"; fi
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src

test: test-unit test-integration ## Full suite

test-unit: ## Fast gate for pre-push: terraform fmt check + python unit tier
	terraform fmt -check -recursive infra
	uv run pytest tests --ignore-glob="**/integration/**"

test-integration: ## terraform test dirs + python integration tier (when present)
	@set -e; for dir in $$(find infra -name '*.tftest.hcl' -exec dirname {} \; | sort -u); do \
		echo "Testing $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform test); \
	done; true
	@if find tests -path '*/integration/*' -name 'test_*.py' 2>/dev/null | grep -q .; then \
		uv run pytest tests --ignore-glob="**/unit/**"; \
	else echo "no python integration tests yet — unit tier is the gate"; fi

coverage: ## Python tests with coverage (TST-003 ratchet; domain/application ≥ 80%)
	uv run pytest tests --cov=src --cov-report=term-missing --cov-report=xml

build: ## Credential-free gates: terraform validate every env + uv lockfile consistency
	@set -e; for dir in infra/envs/*/; do \
		echo "Validating $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform validate); \
	done
	uv lock --check

run: plan ## For IaC, "run" shows the plan; the inspection engine runs via `make inspect`

plan: ## Plan the selected env (ENV=dev by default; needs credentials + backend)
	cd infra/envs/$(ENV) && terraform init -input=false && terraform plan

# ---------------------------------------------------------------------------
# Project extensions — inspection engine (read-only; needs ADC credentials)
# ---------------------------------------------------------------------------

PARAMS ?= inspection-params.yml
OUT ?= reports

inspect: ## Run the FR-4 inspection (PARAMS=<engagement yaml> [OUT=reports] [FAIL_ON=HIGH])
	uv run python -m src.modules.inspection.interface.cli \
		--params "$(PARAMS)" --out-dir "$(OUT)" $(if $(FAIL_ON),--fail-on $(FAIL_ON))

FINDINGS ?= findings.json

report-ai: ## Generate advisory AI Markdown (FINDINGS=<findings.json> [OUT=<dir>])
	uv run python -m src.modules.reporting.interface.cli \
		--input "$(FINDINGS)" $(if $(filter command line environment,$(origin OUT)),--out-dir "$(OUT)")

remediation-draft: ## Render non-applying remediation Markdown (FINDINGS=<json> [OUT=<dir>])
	uv run python -m src.modules.reporting.interface.remediation_cli \
		--input "$(FINDINGS)" $(if $(filter command line environment,$(origin OUT)),--out-dir "$(OUT)")

MENU_PROFILE ?= service-packages/inspection-standard.yml
MENU_OUT ?= reports/service-packaging

render-inspection-menu: ## Render customer menu (MENU_PROFILE=<yaml> [MENU_OUT=<dir>])
	uv run python -m src.modules.service_packaging.interface.render_menu_cli \
		--profile "$(MENU_PROFILE)" --out-dir "$(MENU_OUT)"

security-scan: ## Local sweep: secrets + IaC misconfig + python dependency vulns
	@if command -v gitleaks >/dev/null 2>&1; then gitleaks detect --no-banner; else echo "gitleaks not installed — CI still enforces SEC-002"; fi
	@if command -v trivy >/dev/null 2>&1; then trivy config --exit-code 1 infra && trivy fs --scanners vuln --exit-code 1 uv.lock; else echo "trivy not installed — CI still enforces SEC-030"; fi

sbom: ## SBOM (SPDX + CycloneDX) into dist/ — REL-020
	@mkdir -p dist
	@if command -v syft >/dev/null 2>&1; then syft . -o spdx-json=dist/sbom.spdx.json -o cyclonedx-json=dist/sbom.cdx.json && echo "SBOM written to dist/"; else echo "syft not installed — release workflow generates the authoritative SBOM"; fi

clean: ## Remove caches/artifacts inside the workspace only (GR-031)
	find infra -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist htmlcov .coverage coverage.xml .pytest_cache .ruff_cache .mypy_cache
	find src tests -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

doctor: ## Foundation self-check: metadata invariants + guard-hook tests
	@bash scripts/template-check.sh
	@bash .claude/hooks/tests/guard-bash.test.sh
