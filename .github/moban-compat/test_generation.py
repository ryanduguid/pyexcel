"""Run against a disposable checkout with the pinned template trees present."""

import hashlib
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch


def render():
    from moban.main import main

    sys.argv = ["moban", "-f"]
    with patch(
        "gease.contributors.EndPoint.get_all_contributors",
        return_value=[
            {
                "login": "moban-fixture",
                "name": "moban-fixture",
                "html_url": "https://example.invalid/contributor",
            }
        ],
    ):
        main()


def snapshot(paths):
    return {
        path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
        for path in paths
    }


if __name__ == "__main__":
    if sys.argv[1:] == ["--render"]:
        render()
    else:
        script = str(Path(__file__).resolve())
        outputs = (
            Path(".github/moban-compat/outputs.txt").read_text().splitlines()
        )
        assert len(outputs) == len(set(outputs)) == 29
        readme = Path("README.rst").read_bytes()
        subprocess.run([sys.executable, script, "--render"], check=True)
        first = snapshot(outputs)
        assert Path("README.rst").read_bytes() == readme
        assert (
            Path(".github/workflows/moban-update.yml").read_bytes()
            == Path(".moban.d/moban-update.yml").read_bytes()
        )
        assert "moban-fixture" in Path("CONTRIBUTORS.rst").read_text()
        assert "pyexcel" in Path("setup.py").read_text()
        subprocess.run([sys.executable, script, "--render"], check=True)
        assert snapshot(outputs) == first, "generation must be idempotent"
        print(
            "29 outputs generated twice; contributor global, local workflow "
            "shadow and idempotence pass"
        )
