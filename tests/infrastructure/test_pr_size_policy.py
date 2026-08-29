import unittest
from pathlib import Path

from scripts.pr_size_policy import (
    evaluate_size,
    is_authenticated_template_sync,
    summarize_lockfiles,
)


class PullRequestSizePolicyTests(unittest.TestCase):
    def test_child_workflow_uses_the_fail_closed_policy(self) -> None:
        workflow = (Path(__file__).parents[2] / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("python3 scripts/pr_size_policy.py", workflow)
        self.assertIn("PR_AUTHOR: ${{ github.event.pull_request.user.login }}", workflow)
        self.assertIn("PR_BODY: ${{ github.event.pull_request.body }}", workflow)

    def test_excludes_lockfile_churn_from_hard_limit(self) -> None:
        lockfile_stats = summarize_lockfiles(
            [
                {"filename": "package.json", "additions": 15, "deletions": 58},
                {
                    "filename": "nested/pnpm-lock.yaml",
                    "additions": 300,
                    "deletions": 700,
                },
            ]
        )

        result = evaluate_size(315, 758, 2, lockfile_stats)

        self.assertEqual(result.changed_lines, 73)
        self.assertEqual(result.changed_files, 1)
        self.assertEqual(result.level, "ok")

    def test_authenticated_template_sync_may_exceed_only_numeric_limit(self) -> None:
        authenticated = is_authenticated_template_sync(
            pr_author="github-actions[bot]",
            head_repository="Yukihide-Mitsuoka/secure-ga4-bq-template",
            target_repository="Yukihide-Mitsuoka/secure-ga4-bq-template",
            head_ref="chore/template_sync_3726fbb",
            base_ref="main",
            pr_body=(
                "Direct-parent-source: "
                "https://github.com/Yukihide-Mitsuoka/terraform-gcp-template@" + "a" * 40
            ),
        )

        self.assertEqual(
            evaluate_size(1020, 168, 28, (0, 0, 0), authenticated).level,
            "mechanical",
        )

    def test_template_sync_authentication_fails_closed(self) -> None:
        valid = {
            "pr_author": "github-actions[bot]",
            "head_repository": "Yukihide-Mitsuoka/secure-ga4-bq-template",
            "target_repository": "Yukihide-Mitsuoka/secure-ga4-bq-template",
            "head_ref": "chore/template_sync_3726fbb",
            "base_ref": "main",
            "pr_body": (
                "Direct-parent-source: "
                "https://github.com/Yukihide-Mitsuoka/terraform-gcp-template@" + "a" * 40
            ),
        }
        invalid_overrides = (
            {"pr_author": "maintainer"},
            {"head_repository": "attacker/fork"},
            {"target_repository": "attacker/repository"},
            {"head_ref": "chore/manual-sync_3726fbb"},
            {"head_ref": "chore/template_sync_abc123"},
            {"base_ref": "release"},
            {"pr_body": ("Direct-parent-source: https://github.com/attacker/template@" + "a" * 40)},
            {
                "pr_body": (
                    "Direct-parent-source: "
                    "https://github.com/Yukihide-Mitsuoka/terraform-gcp-template@" + "a" * 39
                )
            },
        )

        self.assertTrue(is_authenticated_template_sync(**valid))
        for override in invalid_overrides:
            with self.subTest(override=override):
                self.assertFalse(is_authenticated_template_sync(**(valid | override)))

    def test_rejects_malformed_or_excessive_exclusions(self) -> None:
        with self.assertRaises(ValueError):
            summarize_lockfiles(
                [{"filename": "pnpm-lock.yaml", "additions": "300", "deletions": 0}]
            )
        with self.assertRaises(ValueError):
            evaluate_size(10, 10, 1, (11, 0, 1))

    def test_preserves_limits_for_ordinary_prs(self) -> None:
        self.assertEqual(evaluate_size(401, 0, 1, (0, 0, 0)).level, "soft")
        self.assertEqual(evaluate_size(801, 0, 1, (0, 0, 0)).level, "hard")


if __name__ == "__main__":
    unittest.main()
