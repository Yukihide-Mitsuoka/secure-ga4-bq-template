import json
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).parents[2]
WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "template-sync.yml"
MANIFEST = REPOSITORY_ROOT / ".github" / "inheritance" / "manifest.json"
IGNORE = REPOSITORY_ROOT / ".templatesyncignore"


class TemplateSyncWorkflowTest(unittest.TestCase):
    def test_unused_parent_test_selector_remains_leaf_owned(self):
        path = "scripts/run-foundation-tests.sh"
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        ignored = {
            line.strip()
            for line in IGNORE.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertIn(path, manifest["protected_paths"])
        self.assertNotIn(path, manifest["inherited_paths"])
        self.assertIn("scripts/**", ignored)

    def test_sync_pr_records_exact_action_source_commit(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("id: template-sync", workflow)
        self.assertIn("steps.template-sync.outputs.pr_branch", workflow)
        self.assertIn(
            'SOURCE_REPOSITORY: "Yukihide-Mitsuoka/terraform-gcp-template"',
            workflow,
        )
        self.assertIn(
            'gh api "repos/${SOURCE_REPOSITORY}/commits/${SOURCE_SHORT}"',
            workflow,
        )
        self.assertIn("gh pr edit", workflow)

    def test_template_sync_runs_daily_off_the_hour(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn('cron: "17 7 * * *"', workflow)
        self.assertNotIn('cron: "0 7 * * 1"', workflow)

    def test_template_sync_is_single_flight_and_preserves_open_prs(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("group: template-sync-${{ github.repository }}", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertIn("id: sync-preflight", workflow)
        self.assertIn("--state open --limit 101", workflow)
        self.assertIn("More than 100 open PRs prevent bounded", workflow)
        self.assertIn('startswith("chore/template_sync_")', workflow)
        self.assertIn("Multiple open Template Sync PRs require human review", workflow)
        self.assertIn("steps.sync-preflight.outputs.should_sync == 'true'", workflow)
        self.assertNotIn("is_force_push_pr", workflow)
        self.assertNotIn("cleanup_old", workflow)

    def test_sync_pr_body_stays_inside_the_run_block(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertNotIn("\nBefore merge:\n", workflow)
        self.assertIn("\n          Before merge:\n", workflow)
        self.assertIn(
            "\n          - Finalize manual boundaries and "
            ".github/inheritance/lock.json in this same reviewed PR.",
            workflow,
        )


if __name__ == "__main__":
    unittest.main()
