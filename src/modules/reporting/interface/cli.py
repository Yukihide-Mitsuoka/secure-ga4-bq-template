from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

from src.modules.reporting.application.generate_ai_report import GenerateAiReport
from src.modules.reporting.application.ports import (
    GeneratedOutputError,
    ProviderError,
    TextGenerator,
)
from src.modules.reporting.infrastructure.json_artifact_reader import JsonArtifactReader
from src.modules.reporting.infrastructure.markdown_report_writer import MarkdownReportWriter
from src.modules.reporting.infrastructure.vertex_ai_generator import VertexAiGenerator

GeneratorFactory = Callable[[str, str, str], TextGenerator]


def main(
    argv: Sequence[str] | None = None,
    *,
    generator_factory: GeneratorFactory = lambda project, location, model: VertexAiGenerator(
        project=project, location=location, model=model
    ),
) -> int:
    args = _parser().parse_args(argv)
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    model = os.environ.get("GA4_BQ_REPORT_MODEL", "gemini-2.5-flash")
    if not project or not location:
        print(
            "ga4-bq-report: GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION are required",
            file=sys.stderr,
        )
        return 2

    input_path = Path(args.input)
    out_dir = Path(args.out_dir) if args.out_dir else input_path.parent
    use_case = GenerateAiReport(
        reader=JsonArtifactReader(),
        generator=generator_factory(project, location, model),
        writer=MarkdownReportWriter(),
    )
    try:
        path = use_case.handle(input_path, out_dir)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"ga4-bq-report: invalid input or output: {error}", file=sys.stderr)
        return 2
    except (ProviderError, GeneratedOutputError) as error:
        print(f"ga4-bq-report: generation failed: {error}", file=sys.stderr)
        return 1
    print(f"AI report: {path}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ga4-bq-report",
        description="Generate an advisory Vertex AI report from deterministic findings.",
    )
    parser.add_argument("--input", required=True, help="path to findings.json")
    parser.add_argument("--out-dir", help="output directory (default: input directory)")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
