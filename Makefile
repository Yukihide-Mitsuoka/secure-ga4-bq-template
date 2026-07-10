# Canonical command interface (CLAUDE.md §11) wired for this template's layout:
# root configs under infra/envs/<env>/ that reference modules from
# github.com/Yukihide-Mitsuoka/terraform-gcp-modules pinned by tag (?ref=vX.Y.Z).
# The heavier layered-foundations reference stays available in profiles/terraform-gcp/.

.PHONY: setup format lint test test-unit test-integration coverage build run \
        security-scan sbom clean help doctor plan

FILE ?=
ENV ?= dev

help: ## List available targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-18s %s\n", $$1, $$2}'

setup: ## Install git hooks (terraform/tflint/gitleaks come from your machine setup)
	@if command -v pre-commit >/dev/null 2>&1; then pre-commit install --hook-type pre-commit --hook-type pre-push; else echo "pre-commit not installed — local hooks skipped (CI runs the same gates)"; fi

format: ## Auto-format terraform (all, or FILE=<path>)
ifneq ($(FILE),)
	@case "$(FILE)" in *.tf|*.tfvars) terraform fmt "$(FILE)" ;; *) : ;; esac
else
	terraform fmt -recursive infra
endif

lint: ## Check-only, zero warnings (COD-001); never fixes
	terraform fmt -check -recursive infra
	@if command -v tflint >/dev/null 2>&1; then tflint --recursive --chdir infra; else echo "tflint not installed — CI still enforces it"; fi

test: test-integration ## Full suite (no app-level unit tests in a pure-IaC starter)

test-unit: ## Fast gate for pre-push: fmt check only (terraform has no fast unit layer)
	terraform fmt -check -recursive infra

test-integration: ## terraform test for every dir that has *.tftest.hcl
	@set -e; for dir in $$(find infra -name '*.tftest.hcl' -exec dirname {} \; | sort -u); do \
		echo "Testing $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform test); \
	done; true

coverage: ## Not applicable to pure IaC; kept honest with a note (no fake metric)
	@echo "coverage: no application code in this IaC starter; nothing to measure"

build: ## Credential-free validate of every env
	@set -e; for dir in infra/envs/*/; do \
		echo "Validating $$dir..."; \
		(cd "$$dir" && terraform init -backend=false -input=false >/dev/null && terraform validate); \
	done

run: plan ## For IaC, "run" shows the plan

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
	rm -rf dist

doctor: ## Foundation self-check: metadata invariants + guard-hook tests
	@bash scripts/template-check.sh
	@bash .claude/hooks/tests/guard-bash.test.sh
