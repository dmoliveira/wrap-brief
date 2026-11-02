"""Bounded repository guidance regressions; live protection is checked separately."""

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_REPORT = "https://github.com/dmoliveira/wrap-brief/security/advisories/new"


class GovernanceTests(unittest.TestCase):
    def test_security_and_issue_routes_are_private_without_public_fallback(self):
        security = (ROOT / "SECURITY.md").read_text()
        self.assertIn(PRIVATE_REPORT, security)
        self.assertIn("do not fall back to public issues", security)
        config = (ROOT / ".github/ISSUE_TEMPLATE/config.yml").read_text()
        self.assertIn("blank_issues_enabled: false", config)
        self.assertIn(PRIVATE_REPORT, config)
        for name in ("bug_report", "feature_request"):
            text = (ROOT / f".github/ISSUE_TEMPLATE/{name}.md").read_text()
            self.assertTrue(text.startswith("---\nname:"))
            self.assertIn("This issue is public", text)
            self.assertIn(PRIVATE_REPORT, text)
            self.assertIn("credentials", text)

    def test_pr_template_requires_validation_rollback_and_no_activation(self):
        text = (ROOT / ".github/PULL_REQUEST_TEMPLATE.md").read_text()
        for section in ("## Summary", "## Validation", "## Rollback"):
            self.assertIn(section, text)
        self.assertIn("synthetic", text)
        self.assertIn("no bypass", text)
        self.assertIn("No live source", text)

    def test_ownership_and_fork_guidance_do_not_claim_enforced_peer_approval(self):
        owners = (ROOT / ".github/CODEOWNERS").read_text()
        self.assertIn("* @dmoliveira", owners)
        text = (ROOT / "CONTRIBUTING.md").read_text()
        self.assertIn("zero independent approvals are platform-mandatory", text)
        self.assertIn("No service account, personal token", text)
        self.assertIn("T01.04", text)
        self.assertIn("unprivileged `pull_request`", text)
        self.assertIn("T01.03", text)


if __name__ == "__main__":
    unittest.main()
