from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from src.modules.reporting.application.generate_remediation_draft import (
    GenerateRemediationDraft,
)
from src.modules.reporting.infrastructure.json_artifact_reader import JsonArtifactReader
from src.modules.reporting.infrastructure.markdown_remediation_writer import (
    MarkdownRemediationWriter,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    input_path = Path(args.input)
    out_dir = Path(args.out_dir) if args.out_dir else input_path.parent
    use_case = GenerateRemediationDraft(
        reader=JsonArtifactReader(), writer=MarkdownRemediationWriter()
    )
    try:
        path = use_case.handle(input_path, out_dir)
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"ga4-bq-remediation: invalid input or output: {error}", file=sys.stderr)
        return 2
    print(f"Remediation draft: {path}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ga4-bq-remediation",
        description="Render a non-applying remediation draft from deterministic findings.",
    )
    parser.add_argument("--input", required=True, help="path to findings.json")
    parser.add_argument("--out-dir", help="output directory (default: input directory)")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
