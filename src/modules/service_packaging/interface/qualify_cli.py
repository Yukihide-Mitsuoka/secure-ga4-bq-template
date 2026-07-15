from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from src.modules.service_packaging.application.qualify_engagement import QualifyEngagement
from src.modules.service_packaging.infrastructure.qualification_artifact_writer import (
    QualificationArtifactWriter,
)
from src.modules.service_packaging.infrastructure.yaml_profile_repository import (
    YamlMenuProfileRepository,
)
from src.modules.service_packaging.infrastructure.yaml_scope_repository import (
    YamlEngagementScopeRepository,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    use_case = QualifyEngagement(
        profile_reader=YamlMenuProfileRepository(),
        scope_reader=YamlEngagementScopeRepository(),
        writer=QualificationArtifactWriter(),
    )
    try:
        json_path, markdown_path = use_case.handle(
            Path(args.profile), Path(args.scope), Path(args.out_dir)
        )
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"ga4-bq-qualification: invalid input or output: {error}", file=sys.stderr)
        return 2
    print(f"Qualification JSON: {json_path}")
    print(f"Qualification Markdown: {markdown_path}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ga4-bq-qualification",
        description="Qualify an anonymous engagement scope against a versioned menu profile.",
    )
    parser.add_argument("--profile", required=True, help="path to a service profile YAML")
    parser.add_argument("--scope", required=True, help="path to an engagement scope YAML")
    parser.add_argument("--out-dir", required=True, help="output directory")
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
