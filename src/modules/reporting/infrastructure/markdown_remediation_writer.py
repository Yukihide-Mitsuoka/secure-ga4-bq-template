from __future__ import annotations

import html
import os
import tempfile
from pathlib import Path

from src.modules.reporting.domain.model import InspectionArtifact
from src.modules.reporting.domain.remediation import REMEDIATION_RECIPE_VERSION, recipe_for


class MarkdownRemediationWriter:
    def write(self, artifact: InspectionArtifact, out_dir: Path) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "remediation-draft.md"
        if target.exists():
            raise FileExistsError(f"remediation draft already exists: {target}")
        content = _render(artifact)
        descriptor, temporary_name = tempfile.mkstemp(prefix=".remediation-draft-", dir=out_dir)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.link(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        return target


def _render(artifact: InspectionArtifact) -> str:
    lines = [
        "# Deterministic remediation draft",
        "",
        "> Draft only: do not apply directly. Human review, repository adaptation, plan,",
        "> and engagement approval are required.",
        "",
        f"- Project: {_code(artifact.project_id)}",
        f"- Captured at: {_code(artifact.captured_at)}",
        f"- Recipe version: {_code(REMEDIATION_RECIPE_VERSION)}",
        f"- Findings: {len(artifact.findings)}",
    ]
    for finding in artifact.findings:
        recipe = recipe_for(finding.check_id)
        lines.extend(
            [
                "",
                f"## {finding.ref}: {finding.check_id}",
                "",
                f"- Severity: **{finding.severity}**",
                f"- Resource: {_code(finding.resource)}",
                f"- Rule: {_code(finding.rule_ref)}",
                f"- Recipe: {_code(recipe.recipe_id)} ({recipe.kind})",
                "",
                f"### {recipe.title}",
                "",
                "Required inputs:",
                "",
            ]
        )
        lines.extend(f"- {_code(value)}" for value in recipe.required_inputs)
        lines.extend(["", "### Draft example", ""])
        if recipe.example is None:
            lines.append(
                "No safe code example can be inferred. Complete the required inputs and "
                "follow the validation procedure."
            )
        else:
            lines.extend(
                [
                    f"```{recipe.example_language}",
                    recipe.example,
                    "```",
                ]
            )
        lines.extend(["", "### Validation", ""])
        lines.extend(
            f"{index}. {step}" for index, step in enumerate(recipe.validation_steps, start=1)
        )
    lines.extend(["", "No changes were applied or submitted by this generator.", ""])
    return "\n".join(lines)


def _code(value: str) -> str:
    escaped = html.escape(value, quote=True).replace("`", "&#96;")
    escaped = escaped.replace("\r", "&#13;").replace("\n", "&#10;")
    return f"`{escaped}`"
