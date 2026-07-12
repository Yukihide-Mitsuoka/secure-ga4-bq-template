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
                                                                 │ source=?ref            uses:@v1
                                                                 ├────────▶ terraform-gcp-modules (tagged library)
                                                                 └────────▶ gcp-cicd-workflows (reusable workflows)
```

| Decision | Rule |
|----------|------|
| New GA4→BQ secure-mart engagement? | "Use this template" **here** — one repo per engagement |
| Plain GCP/Terraform project (no GA4 asset)? | Use [terraform-gcp-template](https://github.com/Yukihide-Mitsuoka/terraform-gcp-template) |
| Reusable Terraform building blocks | [terraform-gcp-modules](https://github.com/Yukihide-Mitsuoka/terraform-gcp-modules), referenced by tag, never copied |
| Reusable CI/CD (WIF auth, deploy, cost gate) | [gcp-cicd-workflows](https://github.com/Yukihide-Mitsuoka/gcp-cicd-workflows), `uses: ...@v1` |
| Base updates | terraform-gcp-template changes arrive as sync PRs ([template-sync.yml](.github/workflows/template-sync.yml)); engagement repos repoint their sync source to THIS repo |

## What this adds on top of terraform-gcp-template

| Addition | Location | Status |
|----------|----------|--------|
| Normative requirements (2 modes: build / inspect; 11 deterministic inspection checkpoints; GA4 sensitive-column catalog; dbt/Dataform rail) | [`docs/requirements/`](docs/requirements/README.md) | imported |
| GA4 sensitivity catalog + `event_params` unnest examples | [`catalog/ga4-sensitivity.yml`](catalog/README.md) + exemplar in [`profiles/dbt-bigquery/skeleton/`](profiles/dbt-bigquery/skeleton/) | imported |
| dbt / Dataform engine profiles (profile-copy selection) | dbt: [`profiles/dbt-bigquery/`](profiles/dbt-bigquery/README.md); Dataform planned | partial |
| WIF wiring (deployer SA + read-only inspector SA) | planned — design in [design-modules-wif-wiring.md](docs/requirements/design-modules-wif-wiring.md) | — |
| Inspection engine (11 deterministic checks; JSON/Markdown output) | [src/modules/inspection/](src/modules/inspection/MODULE.md) | implemented |
| AI inspection narrative (Vertex AI; pseudonymized provider input) | [src/modules/reporting/](src/modules/reporting/MODULE.md) | implemented |

The Terraform building blocks themselves (`bigquery-dataset`, `bigquery-policy-tags`,
`bigquery-data-policy`, `log-router-sink`, `bq-inspector-role`) are **not** in this repo:
they will be added to terraform-gcp-modules and referenced by tag.

## Visibility
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

This repo is **private**: the requirement docs carry engagement pricing and internal
organization details. Sanitize those before ever flipping visibility.

## Using this template

1. **Create the engagement repo**: GitHub → "Use this template".
2. **Repoint template sync**: in `.github/workflows/template-sync.yml`, change
   `source_repo_path` to `Yukihide-Mitsuoka/secure-ga4-bq-template`; set the repo variable
   `TEMPLATE_SYNC_ENABLED=true`.
3. **Replace placeholders**: `grep -rn "{{" . --exclude-dir=.git` — engagement parameters
   (sensitivity-catalog overrides, unnest keys, IAM principals, audit-log scope) are the
   per-engagement input; the template body stays unchanged (FR-7).
4. **Configure GitHub** (one-time): `bash scripts/setup-github.sh`.
5. **Install local gates**: `make setup`.
6. **Verify**: `make doctor && make build`.

## License

MIT — see [LICENSE](LICENSE).
