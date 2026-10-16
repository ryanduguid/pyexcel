"""Exercise the workflow's actual commit script using local Git fixtures."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from ruamel.yaml import YAML


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = YAML(typ="safe").load(
    (ROOT / "workflows/moban-update.yml").read_text()
)
COMMIT = next(
    step["run"]
    for step in WORKFLOW["jobs"]["commit"]["steps"]
    if step.get("id") == "commit"
)
PUSH = WORKFLOW["jobs"]["commit"]["steps"][-1]["run"]
COLLECT = next(
    step["run"]
    for step in WORKFLOW["jobs"]["generate"]["steps"]
    if step.get("name") == "Collect generated changes"
)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.consumer = self.root / "consumer"
        self.consumer.mkdir()
        self.environment = {
            "PATH": "/usr/bin:/bin",
            "HOME": str(self.root),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        self.git(self.consumer, "init", "-q", "-b", "fixture")
        self.git(self.consumer, "config", "user.name", "Fixture")
        self.git(
            self.consumer, "config", "user.email", "fixture@example.invalid"
        )
        for path, content in {
            ".github/moban-compat/outputs.txt": (
                ROOT / "moban-compat/outputs.txt"
            ).read_text(),
            ".github/workflows/tests.yml": "name: fixture\n",
            "LICENSE": "Fixture licence\n",
            "lint.sh": "#!/bin/sh\nexit 0\n",
        }.items():
            file = self.consumer / path
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(content)
        self.git(self.consumer, "add", ".")
        self.git(self.consumer, "commit", "-qm", "Fixture base")
        self.source = self.git(
            self.consumer, "rev-parse", "HEAD"
        ).stdout.strip()
        self.producer = self.root / "producer"
        self.git(
            self.root, "clone", "-q", str(self.consumer), str(self.producer)
        )
        artifact = self.root / "moban-changes"
        artifact.mkdir()
        self.patch = artifact / "moban.patch"
        self.output = self.root / "output"
        self.environment.update(
            RUNNER_TEMP=str(self.root),
            SOURCE_SHA=self.source,
            TARGET_REF="refs/heads/fixture",
            GITHUB_OUTPUT=str(self.output),
        )

    def git(self, cwd, *args):
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=self.environment,
            text=True,
            capture_output=True,
            check=True,
        )

    def run_commit(self, empty=False, collect=False):
        if empty:
            self.patch.write_bytes(b"")
        elif collect:
            subprocess.run(
                ["bash", "-euo", "pipefail", "-c", COLLECT],
                cwd=self.producer,
                env=self.environment,
                text=True,
                capture_output=True,
                check=True,
            )
            self.patch.write_bytes((self.root / "moban.patch").read_bytes())
        else:
            self.git(self.producer, "add", "-N", ".")
            self.patch.write_text(
                self.git(self.producer, "diff", "HEAD", "--binary").stdout
            )
        return subprocess.run(
            [
                "bash",
                "--noprofile",
                "--norc",
                "-euo",
                "pipefail",
                "-c",
                COMMIT,
            ],
            cwd=self.consumer,
            env=self.environment,
            text=True,
            capture_output=True,
        )

    def test_benign_commit_and_local_push(self):
        (self.producer / "LICENSE").write_text("Updated fixture licence\n")
        marker = self.root / "executed"
        (self.producer / "lint.sh").write_text(
            f"#!/bin/sh\ntouch '{marker}'\n"
        )
        result = self.run_commit()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("committed=true", self.output.read_text())
        self.assertFalse(marker.exists())
        remote = self.root / "remote.git"
        self.git(self.root, "init", "--bare", "-q", str(remote))
        self.git(self.consumer, "remote", "add", "origin", str(remote))
        pushed = subprocess.run(
            ["bash", "-euo", "pipefail", "-c", PUSH],
            cwd=self.consumer,
            env=self.environment,
            text=True,
            capture_output=True,
        )
        self.assertEqual(pushed.returncode, 0, pushed.stdout + pushed.stderr)
        self.assertEqual(
            self.git(remote, "rev-parse", "refs/heads/fixture").stdout,
            self.git(self.consumer, "rev-parse", "HEAD").stdout,
        )

    def test_empty_patch_is_a_clean_noop(self):
        self.assertEqual(self.run_commit(empty=True).returncode, 0)
        self.assertFalse(self.output.exists())
        self.assertEqual(
            self.git(self.consumer, "rev-parse", "HEAD").stdout.strip(),
            self.source,
        )

    def test_stale_source_is_rejected(self):
        self.environment["SOURCE_SHA"] = "0" * 40
        self.assertNotEqual(self.run_commit(empty=True).returncode, 0)

    def test_workflow_changes_require_review(self):
        (self.producer / ".github/workflows/tests.yml").write_text(
            "name: changed\n"
        )
        self.assertNotEqual(self.run_commit().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_collection_keeps_staged_metadata(self):
        (self.producer / "LICENSE").write_text("Staged fixture licence\n")
        self.git(self.producer, "add", "LICENSE")
        result = self.run_commit(collect=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Staged fixture licence", self.patch.read_text())
        self.assertIn("committed=true", self.output.read_text())

    def test_collection_keeps_staged_workflows_for_review(self):
        (self.producer / ".github/workflows/tests.yml").write_text(
            "name: staged-workflow\n"
        )
        self.git(self.producer, "add", ".github/workflows/tests.yml")
        self.assertNotEqual(self.run_commit(collect=True).returncode, 0)
        self.assertIn("staged-workflow", self.patch.read_text())
        self.assertFalse(self.output.exists())

    def test_allowlist_changes_cannot_authorise_a_new_path(self):
        (self.producer / ".github/moban-compat/outputs.txt").write_text(
            "unexpected.txt\n"
        )
        (self.producer / "unexpected.txt").write_text("untrusted\n")
        self.assertNotEqual(self.run_commit().returncode, 0)
        self.assertFalse((self.consumer / "unexpected.txt").exists())

    def test_symlinks_are_rejected(self):
        file = self.producer / "LICENSE"
        file.unlink()
        file.symlink_to("lint.sh")
        self.assertNotEqual(self.run_commit().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_executable_modes_are_rejected(self):
        os.chmod(self.producer / "lint.sh", 0o755)
        self.assertNotEqual(self.run_commit().returncode, 0)
        self.assertFalse(self.output.exists())

    def test_deletions_are_rejected(self):
        (self.producer / "LICENSE").unlink()
        self.assertNotEqual(self.run_commit().returncode, 0)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
