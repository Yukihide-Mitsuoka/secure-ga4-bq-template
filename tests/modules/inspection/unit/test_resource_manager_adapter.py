"""Unit tests for the Resource Manager IAM adapter (policy v3 translation)."""

from typing import Any

from src.modules.inspection.infrastructure.gcp.resource_manager import ResourceManagerIamAdapter


class FakeRequest:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def execute(self) -> dict[str, Any]:
        return self._response


class FakeProjectsResource:
    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response
        self.last_call: dict[str, Any] = {}

    def getIamPolicy(self, resource: str, body: dict[str, Any]) -> FakeRequest:  # noqa: N802
        self.last_call = {"resource": resource, "body": body}
        return FakeRequest(self._response)


class FakeResourceManagerService:
    def __init__(self, response: dict[str, Any]) -> None:
        self.projects_resource = FakeProjectsResource(response)

    def projects(self) -> FakeProjectsResource:
        return self.projects_resource


def test_bindings_and_audit_configs_are_translated() -> None:
    service = FakeResourceManagerService(
        {
            "bindings": [
                {"role": "roles/owner", "members": ["user:a@example.com", "group:g@example.com"]},
                {"role": "roles/bigquery.dataViewer", "members": ["allUsers"]},
            ],
            "auditConfigs": [
                {
                    "service": "bigquery.googleapis.com",
                    "auditLogConfigs": [
                        {"logType": "DATA_READ", "exemptedMembers": ["user:x@example.com"]},
                        {"logType": "ADMIN_READ"},
                    ],
                }
            ],
        }
    )
    iam = ResourceManagerIamAdapter(service).get_project_iam_policy("p")
    assert [(b.role, b.members) for b in iam.bindings] == [
        ("roles/owner", ("user:a@example.com", "group:g@example.com")),
        ("roles/bigquery.dataViewer", ("allUsers",)),
    ]
    config = iam.audit_configs[0]
    assert config.service == "bigquery.googleapis.com"
    assert [(lc.log_type, lc.exempted_members) for lc in config.log_configs] == [
        ("DATA_READ", ("user:x@example.com",)),
        ("ADMIN_READ", ()),
    ]


def test_policy_version_3_is_requested_for_audit_configs() -> None:
    # CHK-06 needs auditConfigs, which only policy v3 responses carry.
    service = FakeResourceManagerService({})
    ResourceManagerIamAdapter(service).get_project_iam_policy("p")
    assert service.projects_resource.last_call == {
        "resource": "projects/p",
        "body": {"options": {"requestedPolicyVersion": 3}},
    }


def test_empty_policy_yields_empty_domain_model() -> None:
    iam = ResourceManagerIamAdapter(FakeResourceManagerService({})).get_project_iam_policy("p")
    assert iam.bindings == ()
    assert iam.audit_configs == ()
