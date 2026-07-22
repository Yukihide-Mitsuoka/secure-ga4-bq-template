# secure-ga4-bq-template

**Secure standard asset for GA4→BigQuery** — a template repository for engagements that
build or inspect GA4→BQ **mart layers** with three security controls baked in:
① column-level security (policy tags) ② least-privilege IAM ③ cost-optimized audit
logging. Built on [terraform-gcp-template](https://github.com/Yukihide-Mitsuoka/terraform-gcp-template)
(which is built on [ai-dev-foundation](https://github.com/Yukihide-Mitsuoka/ai-dev-foundation)).

> **AI agents:** stop reading this file. Your entry point is [CLAUDE.md](CLAUDE.md)
> (Claude Code) or [AGENTS.md](AGENTS.md) (everyone else). Requirements live in
> [docs/requirements/](docs/requirements/README.md).

## Position in the template chain

```
ai-dev-foundation ─sync▶ terraform-gcp-template ─sync▶ secure-ga4-bq-template ─"Use this template"▶ engagement repo
   (base template)          (GCP/Terraform layer)           (this repo)
                                                                 │ tagged refs       versioned workflows
                                                                 ├────────▶ terraform-gcp-modules (v0.3.0 / v0.4.0)
                                                                 └────────▶ gcp-cicd-workflows (BQ Inspect v1 / cost gate v2.0.2)
```

| Decision | Rule |
|----------|------|
| New GA4→BQ secure-mart engagement? | "Use this template" **here** — one repo per engagement |
| Plain GCP/Terraform project (no GA4 asset)? | Use [terraform-gcp-template](https://github.com/Yukihide-Mitsuoka/terraform-gcp-template) |
| Reusable Terraform building blocks | [terraform-gcp-modules](https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules), referenced by tag, never copied |
| Reusable CI/CD (inspection and cost gate) | [gcp-cicd-workflows](https://github.com/Yukihide-Mitsuoka/gcp-cicd-workflows), BQ Inspect at `v1` and cost gate at `v2.0.2` |
| Base updates | terraform-gcp-template changes arrive as sync PRs ([template-sync.yml](.github/workflows/template-sync.yml)); engagement repos repoint their sync source to THIS repo |

## What this adds on top of terraform-gcp-template

| Addition | Location | Status |
|----------|----------|--------|
| Normative requirements (build / inspect modes; 11 security checkpoints plus CHK-12 metadata governance; dbt/Dataform rail) | [`docs/requirements/`](docs/requirements/README.md) | implemented baseline |
| GA4 sensitivity catalog + `event_params` unnest examples | [`catalog/ga4-sensitivity.yml`](catalog/README.md) + exemplar in [`profiles/dbt-bigquery/skeleton/`](profiles/dbt-bigquery/skeleton/) | imported |
| Secure-mart build rail (Terraform datasets/taxonomy plus profile-copy engine selection) | [`infra/envs/dev/`](infra/README.md); [`profiles/dbt-bigquery/`](profiles/dbt-bigquery/README.md); [`profiles/dataform-bigquery/`](profiles/dataform-bigquery/README.md) | implemented |
| WIF wiring (deployer, read-only inspector, and isolated cost-gate SAs) | [inspection identities](infra/envs/dev/wif.tf); [cost-gate identity](infra/envs/dev/cost_gate_wif.tf) | implemented |
| Read-only inspection engine (CHK-01..CHK-11 security plus CHK-12 table/leaf-column description completeness; JSON/Markdown output) | [src/modules/inspection/](src/modules/inspection/MODULE.md) | implemented |
| Reporting (deterministic remediation draft plus optional Vertex AI narrative) | [src/modules/reporting/](src/modules/reporting/MODULE.md) | implemented |
| Reusable scheduled/on-demand inspection and PR dry-run cost gate | [BQ Inspect](.github/workflows/bq-inspect.yml) at `v1`; [BQ Cost Gate](.github/workflows/bq-cost-gate.yml) at `v2.0.2` | implemented, opt-in |
| Configurable standard-inspection menu and deterministic scope qualification | [`service-packages/`](service-packages/inspection-standard.yml); [src/modules/service_packaging/](src/modules/service_packaging/MODULE.md) | implemented |

Terraform module code is **not** vendored here. The current dev environment references
`bigquery-dataset`, `bigquery-policy-tags`, and `github-oidc` at `v0.3.0`, and
`bq-inspector-role` at `v0.4.0`; upgrades require an explicit reviewed tag change.

## Visibility

This repository is **public**. Checked-in code and documentation are public, including
the reviewed requirement sources. Complete inspection artifacts can expose business
configuration and remain **Internal** under [SEC-011](.ai/security.md#sec-011-data-classification);
do not commit them to this repository. See the
[deployment data boundary](docs/deployment/configuration.md).

## Inspection and AI reporting

Run the deterministic, read-only inspection first:

```bash
make inspect PARAMS=inspection-params.yml OUT=reports
```

AI reporting is optional. Configure ADC plus the variables in `.env.example`, then point
it at the generated artifact:

```bash
make report-ai FINDINGS=reports/<project>/<timestamp>/findings.json
```

`ai-report.md` is a human-review draft; `findings.json` and `summary.md` are authoritative.

Render the separate non-applying remediation attachment without cloud credentials:

```bash
make remediation-draft FINDINGS=reports/<project>/<timestamp>/findings.json
```

`remediation-draft.md` uses deterministic local recipes and explicit placeholders. It is
review material, not an apply-ready Terraform file.

Render the customer-facing standard inspection menu without cloud credentials:

```bash
make render-inspection-menu
```

The command reads `service-packages/inspection-standard.yml` and writes
`reports/service-packaging/inspection-menu.md`. Use `MENU_PROFILE=<yaml>` or
`MENU_OUT=<dir>` to select another reviewed profile or output directory. Change product
values in the versioned profile rather than in the renderer. Existing output is never
overwritten.

Qualify the anonymous example scope against that same profile:

```bash
make qualify-inspection-scope
```

For an engagement, copy and edit `engagement-scope.example.yml`, then pass its path as
`SCOPE=<yaml>`. The command writes deterministic `qualification.json` and
`qualification.md` beside the menu output and never overwrites either artifact. It uses
only declared counts and work flags; it does not access GCP, inspect row values, call AI,
or calculate a final sales price.

For GitHub Actions, copy `inspection-params.example.yml` to `inspection-params.yml`, set
the repository variables `WIF_PROVIDER` and `INSPECTOR_SA`, then run **BQ Inspect**
manually. Set `BQ_INSPECT_ENABLED=true` only after that run succeeds to enable the weekly
schedule. The workflow uploads `findings.json`, `summary.md`, and
`remediation-draft.md`; it never applies remediation.

## Using this template

1. **Create the engagement repo**: GitHub → "Use this template".
2. **Repoint template sync**: in `.github/workflows/template-sync.yml`, change
   `source_repo_path` to `Yukihide-Mitsuoka/secure-ga4-bq-template`; set the repo variable
   `TEMPLATE_SYNC_ENABLED=true`.
3. **Replace placeholders**: `grep -rn "{{" . --exclude-dir=.git` — engagement parameters
   (sensitivity-catalog overrides, unnest keys, IAM principals, audit-log scope) are the
   per-engagement input; the template body stays unchanged (FR-7).
4. **Review GitHub governance** with GET-only `plan`, then use `audit` as the compliance
   gate. A separately authorized local `apply` can enforce the reviewed policy; read its
   authentication and partial-application constraints before use. See
   [Usage](docs/foundation/guides/usage.md#5-review-and-optionally-apply-github-governance).
   Collaboration settings share one verified repository PATCH action; squash-only merge
   is applied before a linear-history Ruleset so every intermediate state remains valid.
   `scripts/setup-github.sh` is a compatibility wrapper for the same `plan` and exactly
   confirmed `apply` paths; it contains no independent governance policy.
5. **Install local gates**: `make setup`.
6. **Verify**: `make doctor && make build`.

## License

MIT — see [LICENSE](LICENSE).
