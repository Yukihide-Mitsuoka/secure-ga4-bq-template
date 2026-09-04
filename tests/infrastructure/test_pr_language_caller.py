import unittest
from pathlib import Path

ROOT = Path(__file__).parents[2]


class PullRequestLanguageCallerTest(unittest.TestCase):
    def test_protected_caller_uses_accepted_base_policy(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")

        for fragment in (
            "types: [opened, reopened, synchronize, edited, labeled, unlabeled, ready_for_review]",
            "ref: ${{ github.event.pull_request.base.sha }}",
            "working-directory: .pr-language-base",
            "PR_ROLE: ${{ steps.pr-role.outputs.role }}",
            "PR_AUTHOR: ${{ github.event.pull_request.user.login }}",
            "python3 -m scripts.pr_language_policy",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, workflow)

        self.assertNotIn("pull_request_target:", workflow)

    def test_protected_workflow_rule_is_role_aware(self):
        rules = (ROOT / ".ai/workflow.md").read_text(encoding="utf-8")

        self.assertIn("English for Foundation and inheritable", rules)
        self.assertIn("template producers, Japanese for consumer leaves", rules)
        self.assertIn("PR language guide", rules)


if __name__ == "__main__":
    unittest.main()
