"""The 11 deterministic checkpoints (FR-4), one category module each.

Every check is a pure function with the uniform signature
`(snapshot, params, catalog) -> list[Finding]` — unused context arguments are
accepted so the runner treats all checkpoints identically. Determinism and
read-only-ness are module invariants (MODULE.md #1-#4).

`ALL_CHECKS` is the canonical registry: exactly eleven entries, ordered by
check id. The B acceptance bar (>=10 checkpoints detected, requirements §8)
is measured against this registry.
"""

from collections.abc import Callable

from src.modules.inspection.domain.catalog import SensitivityCatalog
from src.modules.inspection.domain.checks.audit_logging import (
    check_chk06_data_access_overenabled,
    check_chk07_audit_pipeline,
)
from src.modules.inspection.domain.checks.column_security import (
    check_chk04_catalog_columns_untagged,
    check_chk05_taxonomy_consistency,
)
from src.modules.inspection.domain.checks.cost import (
    check_chk08_large_tables_unpartitioned,
    check_chk09_partition_filter_not_required,
    check_chk10_long_lived_without_expiration,
)
from src.modules.inspection.domain.checks.dataset_hygiene import check_chk11_dataset_hygiene
from src.modules.inspection.domain.checks.iam import (
    check_chk01_basic_roles,
    check_chk02_public_members,
    check_chk03_project_wide_data_roles,
)
from src.modules.inspection.domain.finding import Finding
from src.modules.inspection.domain.params import InspectionParams
from src.modules.inspection.domain.snapshot import ProjectSnapshot

Check = Callable[[ProjectSnapshot, InspectionParams, SensitivityCatalog], list[Finding]]

ALL_CHECKS: tuple[Check, ...] = (
    check_chk01_basic_roles,
    check_chk02_public_members,
    check_chk03_project_wide_data_roles,
    check_chk04_catalog_columns_untagged,
    check_chk05_taxonomy_consistency,
    check_chk06_data_access_overenabled,
    check_chk07_audit_pipeline,
    check_chk08_large_tables_unpartitioned,
    check_chk09_partition_filter_not_required,
    check_chk10_long_lived_without_expiration,
    check_chk11_dataset_hygiene,
)

__all__ = ["ALL_CHECKS", "Check"]
