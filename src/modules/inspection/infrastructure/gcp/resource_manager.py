"""IamPolicyPort implementation over cloudresourcemanager v3.

One read-only call: projects.getIamPolicy with requestedPolicyVersion=3 —
version 3 is required for the auditConfigs that CHK-06 evaluates. Never any
setIamPolicy (FR-6, MODULE.md invariant #1).
"""

from __future__ import annotations

from typing import Any

from src.modules.inspection.domain.snapshot import (
    AuditConfig,
    AuditLogConfig,
    IamBinding,
    ProjectIam,
)


class ResourceManagerIamAdapter:
    def __init__(self, resource_manager_service: Any) -> None:
        self._service = resource_manager_service

    def get_project_iam_policy(self, project_id: str) -> ProjectIam:
        response = (
            self._service.projects()
            .getIamPolicy(
                resource=f"projects/{project_id}",
                body={"options": {"requestedPolicyVersion": 3}},
            )
            .execute()
        )
        return ProjectIam(
            bindings=tuple(
                IamBinding(
                    role=str(binding.get("role", "")),
                    members=tuple(str(m) for m in binding.get("members") or []),
                )
                for binding in response.get("bindings") or []
            ),
            audit_configs=tuple(
                AuditConfig(
                    service=str(config.get("service", "")),
                    log_configs=tuple(
                        AuditLogConfig(
                            log_type=str(log_config.get("logType", "")),
                            exempted_members=tuple(
                                str(m) for m in log_config.get("exemptedMembers") or []
                            ),
                        )
                        for log_config in config.get("auditLogConfigs") or []
                    ),
                )
                for config in response.get("auditConfigs") or []
            ),
        )
