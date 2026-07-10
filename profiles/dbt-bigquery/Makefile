# Profile: Terraform (infra/envs) + dbt/BigQuery (transform/). Superset of the root
# terraform Makefile — canonical targets keep their semantics, dbt is added where it
# belongs (lint=SQLFluff check-only, build=+dbt parse, credentialed runs as extensions).

.PHONY: setup format lint test test-unit test-integration coverage build run \
        security-scan sbom clean help doctor plan dbt-deps dbt-run dbt-test dbt-build

FILE ?=
ENV ?= dev
TRANSFORM_DIR ?= transform
DBT = cd $(TRANSFORM_DIR) && DBT_PROFILES_DIR=. dbt

help: ## List available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

setup: ## Install git hooks (terraform/tflint/dbt/sqlfluff come from your machine setup)
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit install --hook-type pre-commit --hook-type pre-push; else echo "pre-commit not installed — local hooks skipped (CI runs the same gates)"; fi
	@if command -v dbt >/dev/null 2>&1; then $(DBT) deps; else echo "dbt not installed — transform targets unavailable"; fi

format: ## Auto-format terraform + SQL (all, or FILE=<path>)
ifneq ($(FILE),)
	@case "$(FILE)" in \
		*.tf|*.tfvars) terraform fmt "$(FILE)" ;; \
		*.sql) sqlfluff fix --force "$(FILE)" ;; \
		*) : ;; \
	esac
else
	terraform fmt -recursive infra
	@if command -v sqlfluff >/dev/null 2>&1; then sqlfluff fix --force $(TRANSFORM_DIR)/models; else echo "sqlfluff not installed — SQL left as-is"; fi
endif

lint: ## Check-only, zero warnings (COD-001); never fixes
	terraform fmt -check -recursive infra
	@if command -v tflint >/dev/null 2>&1; then tflint --recursive --chdir infra; else echo "tflint not installed — CI still enforces it"; fi
	@if command -v sqlfluff >/dev/null 2>&1; then sqlfluff lint $(TRANSFORM_DIR)/models; else echo "sqlfluff not installed — CI still enforces it"; fi

test: test-integration ## Full suite

test-unit: ## Fast gate for pre-push: fmt + SQL lint (no warehouse)
	terraform fmt -check -recursive infra
	@if command -v sqlfluff >/dev/null 2>&1; then sqlfluff lint $(TRANSFORM_DIR)/models; fi

test-integration: ## terraform test dirs + dbt data tests (dbt part needs credentials)
	@set -e; for dir in $$(find infra -name '*.tftest.hcl' -exec dirname {} \; | sort -u); do \
		echo "Testing $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform test); \
	done; true
	@if command -v dbt >/dev/null 2>&1 && [ -f $(TRANSFORM_DIR)/profiles.yml ]; then $(DBT) test; else echo "dbt or profiles.yml missing — dbt tests skipped (need warehouse credentials)"; fi

coverage: ## dbt has no line coverage; the honest metric is documented+tested models
	@echo "coverage: no line-coverage concept for IaC/SQL; dbt test results above are the gate"

build: ## Credential-free gates: terraform validate every env + dbt parse
	@set -e; for dir in infra/envs/*/; do \
		echo "Validating $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform validate); \
	done
	@if command -v dbt >/dev/null 2>&1; then $(DBT) parse; else echo "dbt not installed — parse gate skipped (CI still enforces it)"; fi

run: plan ## For IaC, "run" shows the plan; transform runs are `make dbt-run`

plan: ## Plan the selected env (ENV=dev by default; needs credentials + backend)
	cd infra/envs/$(ENV) && terraform init -input=false && terraform plan

security-scan: ## Local sweep: secrets + IaC misconfig
	@if command -v gitleaks >/dev/null 2>&1; then gitleaks detect --no-banner; else echo "gitleaks not installed — CI still enforces SEC-002"; fi
	@if command -v trivy >/dev/null 2>&1; then trivy config --exit-code 1 infra; else echo "trivy not installed — CI still enforces SEC-030"; fi

sbom: ## SBOM (SPDX + CycloneDX) into dist/ — REL-020
	@mkdir -p dist
	@if command -v syft >/dev/null 2>&1; then syft . -o spdx-json=dist/sbom.spdx.json -o cyclonedx-json=dist/sbom.cdx.json && echo "SBOM written to dist/"; else echo "syft not installed — release workflow generates the authoritative SBOM"; fi

clean: ## Remove caches/artifacts inside the workspace only (GR-031)
	find infra -type d -name ".terraform" -exec rm -rf {} + 2>/dev/null || true
	rm -rf $(TRANSFORM_DIR)/target $(TRANSFORM_DIR)/dbt_packages dist

doctor: ## Foundation self-check: metadata invariants + guard-hook tests
	@bash scripts/template-check.sh
	@bash .claude/hooks/tests/guard-bash.test.sh

# ---------------------------------------------------------------------------
# Project extensions — dbt workflow (need warehouse credentials)
# ---------------------------------------------------------------------------

dbt-deps: ## Install dbt packages
	$(DBT) deps

dbt-run: ## Build models against the target warehouse
	$(DBT) run

dbt-test: ## Run dbt data tests
	$(DBT) test

dbt-build: ## run + test in DAG order
	$(DBT) build
