---
id: secure-ga4-bq-template-agent-overlay
title: Secure GA4 BigQuery Template Agent Overlay
authority: 3
read_when: [agent-entry]
---

# Secure GA4 BigQuery Template Agent Overlay

This protected project layer contains repository identity and stack facts only. The
explicit agent profile loads it after the inherited foundation and Terraform template
contracts.

- Repository: `Yukihide-Mitsuoka/secure-ga4-bq-template`.
- Role: reusable template that builds and inspects governed GA4-to-BigQuery mart layers.
- Stack: Terraform 1.5 or later and Python 3.12 through uv; BigQuery stores governed
  marts while the inspection engine remains stateless.
- Architecture: a modular monolith with Clean Architecture layers inside bounded
  contexts under `src/modules/`.
- Deployment target: Google Cloud through WIF-authenticated GitHub Actions; optional AI
  reporting uses Gemini on Vertex AI with ADC or WIF.
- Execution model: Terraform apply, live inspection, cloud deployment, and GitHub
  governance changes are separate authenticated operations.
