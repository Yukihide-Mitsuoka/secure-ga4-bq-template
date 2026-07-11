# Profile: Terraform (infra/envs) + Dataform/BigQuery (transform/). Superset of the
# root terraform Makefile — canonical targets keep their semantics, Dataform is added
# where it belongs (build=+compile, credentialed runs as extensions). Note one honest
# gap: `dataform format` has no check-only mode, so lint enforces the rail naming
# conventions instead (rail FR-4) and formatting stays format's job.

.PHONY: setup format lint test test-unit test-integration coverage build run \
        security-scan sbom clean help doctor plan naming-check dataform-run dataform-test

FILE ?=
ENV ?= dev
TRANSFORM_DIR ?= transform
DATAFORM = cd $(TRANSFORM_DIR) && dataform

help: ## List available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

setup: ## Install git hooks (terraform/tflint come from machine setup; dataform: npm i -g @dataform/cli)
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit install --hook-type pre-commit --hook-type pre-push; else echo "pre-commit not installed — local hooks skipped (CI runs the same gates)"; fi
	@if command -v dataform >/dev/null 2>&1; then $(DATAFORM) install; else echo "dataform CLI not installed (npm i -g @dataform/cli) — transform targets unavailable"; fi

format: ## Auto-format terraform + SQLX (dataform format is project-wide)
ifneq ($(FILE),)
	@case "$(FILE)" in \
		*.tf|*.tfvars) terraform fmt "$(FILE)" ;; \
		*.sqlx) if command -v dataform >/dev/null 2>&1; then $(DATAFORM) format; fi ;; \
		*) : ;; \
	esac
else
	terraform fmt -recursive infra
	@if command -v dataform >/dev/null 2>&1; then $(DATAFORM) format; else echo "dataform not installed — SQLX left as-is"; fi
endif

lint: naming-check ## Check-only, zero warnings (COD-001); never fixes
	terraform fmt -check -recursive infra
	@if command -v tflint >/dev/null 2>&1; then tflint --recursive --chdir infra; else echo "tflint not installed — CI still enforces it"; fi

naming-check: ## Rail naming conventions: staging=stg_*, intermediate=int_*, marts=fct_*/dim_*
	@bad=$$( \
		find $(TRANSFORM_DIR)/definitions/staging -name '*.sqlx' ! -name 'stg_*' 2>/dev/null; \
		find $(TRANSFORM_DIR)/definitions/intermediate -name '*.sqlx' ! -name 'int_*' 2>/dev/null; \
		find $(TRANSFORM_DIR)/definitions/marts -name '*.sqlx' ! -name 'fct_*' ! -name 'dim_*' 2>/dev/null); \
	if [ -n "$$bad" ]; then echo "naming violations (stg_*/int_*/fct_*/dim_* — rail §2.2):"; echo "$$bad"; exit 1; fi

test: test-integration ## Full suite

test-unit: naming-check ## Fast gate for pre-push: fmt + naming (no warehouse)
	terraform fmt -check -recursive infra

test-integration: ## terraform test dirs + dataform assertions (dataform part needs credentials)
	@set -e; for dir in $$(find infra -name '*.tftest.hcl' -exec dirname {} \; | sort -u); do \
		echo "Testing $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform test); \
	done; true
	@if command -v dataform >/dev/null 2>&1 && [ -f $(TRANSFORM_DIR)/.df-credentials.json ]; then $(DATAFORM) test; else echo "dataform or .df-credentials.json missing — dataform tests skipped (need warehouse credentials)"; fi

coverage: ## No line-coverage concept for IaC/SQLX; assertions above are the gate
	@echo "coverage: no line-coverage concept for IaC/SQLX; dataform assertion results are the gate"

build: ## Credential-free gates: terraform validate every env + dataform compile
	@set -e; for dir in infra/envs/*/; do \
		echo "Validating $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform validate); \
	done
	@if command -v dataform >/dev/null 2>&1; then $(DATAFORM) compile; else echo "dataform not installed — compile gate skipped (CI still enforces it)"; fi

run: plan ## For IaC, "run" shows the plan; transform runs are `make dataform-run`

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
	rm -rf $(TRANSFORM_DIR)/.dataform $(TRANSFORM_DIR)/node_modules dist

doctor: ## Foundation self-check: metadata invariants + guard-hook tests
	@bash scripts/template-check.sh
	@bash .claude/hooks/tests/guard-bash.test.sh

# ---------------------------------------------------------------------------
# Project extensions — Dataform workflow (need warehouse credentials)
# ---------------------------------------------------------------------------

dataform-run: ## Build models against the target warehouse
	$(DATAFORM) run

dataform-test: ## Run dataform unit tests + assertions
	$(DATAFORM) test
