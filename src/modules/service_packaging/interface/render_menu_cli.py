from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from src.modules.service_packaging.application.render_menu import RenderInspectionMenu
from src.modules.service_packaging.infrastructure.markdown_menu_writer import (
    MarkdownMenuWriter,
)
from src.modules.service_packaging.infrastructure.yaml_profile_repository import (
    YamlMenuProfileRepository,
)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    use_case = RenderInspectionMenu(reader=YamlMenuProfileRepository(), writer=MarkdownMenuWriter())
    try:
        path = use_case.handle(Path(args.profile), Path(args.out_dir))
    except (FileNotFoundError, FileExistsError, OSError, ValueError) as error:
        print(f"ga4-bq-service-menu: invalid input or output: {error}", file=sys.stderr)
        return 2
    print(f"Inspection menu: {path}")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ga4-bq-service-menu",
        description="Render customer-facing Markdown from a versioned inspection profile.",
    )
    parser.add_argument("--profile", required=True, help="path to a service profile YAML")
    parser.add_argument(
        "--out-dir",
        default="reports/service-packaging",
        help="output directory (default: reports/service-packaging)",
    )
    return parser


if __name__ == "__main__":
    raise SystemExit(main())
