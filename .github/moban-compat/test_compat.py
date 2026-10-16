"""Regressions for the two downstream dependency wheels."""

import importlib.metadata
import base64
import csv
import hashlib
import io
import importlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import fs
import jinja2
import jinja2_fsloader
from fs.memoryfs import MemoryFS
from fs.opener import Opener
from fs.opener.errors import EntryPointError, UnsupportedProtocol
from fs.opener.registry import Registry


class ExampleOpener(Opener):
    protocols = ["example"]

    def open_fs(self, fs_url, parse_result, writeable, create, cwd):
        return MemoryFS()


class CompatibilityTests(unittest.TestCase):
    def test_repaired_distribution_records(self):
        for name in ("fs", "jinja2-fsloader"):
            with self.subTest(distribution=name):
                distribution = importlib.metadata.distribution(name)
                self.assertEqual(
                    distribution.metadata["Requires-Python"], ">=3.15"
                )
                self.assertIn("Build: 1", distribution.read_text("WHEEL"))
                self.assertNotIn("Tag: py2", distribution.read_text("WHEEL"))
                self.assertTrue(
                    any(
                        path.name in ("LICENSE", "COPYING")
                        for path in distribution.files
                    )
                )
                records = csv.reader(
                    io.StringIO(distribution.read_text("RECORD"))
                )
                for path, digest, size in records:
                    self.assertNotIn(".git/", path)
                    if digest:
                        contents = distribution.locate_file(path).read_bytes()
                        algorithm, encoded = digest.split("=", 1)
                        self.assertEqual(algorithm, "sha256")
                        self.assertEqual(len(contents), int(size))
                        self.assertEqual(
                            base64.urlsafe_b64encode(
                                hashlib.sha256(contents).digest()
                            )
                            .decode()
                            .rstrip("="),
                            encoded,
                        )

    def test_namespace_extensions_remain_visible(self):
        opener_module = importlib.import_module("fs.opener")
        with tempfile.TemporaryDirectory() as temporary:
            extra = Path(temporary) / "fs" / "opener"
            extra.mkdir(parents=True)
            try:
                with patch.object(sys, "path", [temporary, *sys.path]):
                    importlib.reload(fs)
                    importlib.reload(opener_module)
                    self.assertIn(str(extra.parent), fs.__path__)
                    self.assertIn(str(extra), opener_module.__path__)
            finally:
                importlib.reload(fs)
                importlib.reload(opener_module)

    def test_git_filesystem_uses_the_external_opener(self):
        with tempfile.TemporaryDirectory() as temporary:
            (Path(temporary) / "templates").mkdir()
            (Path(temporary) / "templates" / "example.jj2").write_text(
                "template fixture"
            )
            with patch(
                "gitfs2.repo.git_clone", return_value=temporary
            ) as clone:
                with fs.open_fs(
                    "git://github.com/example/fixture?branch=dev!/templates"
                ) as filesystem:
                    self.assertEqual(
                        filesystem.readtext("example.jj2"), "template fixture"
                    )
                require = clone.call_args.args[0]
                self.assertEqual(
                    require.git_url, "https://github.com/example/fixture"
                )
                self.assertEqual(require.branch, "dev")

    def test_current_distribution_contract(self):
        self.assertEqual(importlib.metadata.version("setuptools"), "84.0.0")
        self.assertEqual(importlib.metadata.version("MarkupSafe"), "3.0.4")
        self.assertEqual(jinja2.__version__, "3.1.6")
        self.assertEqual(jinja2_fsloader.__version__, "0.3.0")
        with self.assertRaises(ModuleNotFoundError):
            __import__("pkg_resources")
        self.assertIn("git", fs.opener.registry.protocols)
        self.assertIn("pypi", fs.opener.registry.protocols)
        self.assertIsInstance(fs.opener.registry.get_opener("git"), Opener)
        self.assertIsInstance(fs.opener.registry.get_opener("pypi"), Opener)

    def test_external_loading_can_be_disabled(self):
        registry = Registry(load_extern=False)
        installed = registry.install(ExampleOpener)
        with patch("fs.opener.registry.entry_points") as discover:
            self.assertEqual(registry.protocols, ["example"])
            self.assertIs(registry.get_opener("example"), installed)
            with self.assertRaises(UnsupportedProtocol):
                registry.get_opener("missing")
            discover.assert_not_called()

    def test_discovery_is_lazy_and_deduplicated(self):
        registry = Registry(load_extern=True)
        registry.install(ExampleOpener)
        point = Mock(name="entrypoint")
        point.name = "example"
        with patch(
            "fs.opener.registry.entry_points", return_value=[point, point]
        ) as discover:
            self.assertEqual(registry.protocols, ["example"])
            discover.assert_called_once_with(group="fs.opener")
            point.load.assert_not_called()

    def test_first_external_match_wins_and_builtin_falls_back(self):
        registry = Registry(load_extern=True)
        installed = registry.install(ExampleOpener)
        first, second = Mock(), Mock()
        first.load.return_value = ExampleOpener
        with patch(
            "fs.opener.registry.entry_points", return_value=[first, second]
        ) as discover:
            self.assertIsInstance(
                registry.get_opener("example"), ExampleOpener
            )
            discover.assert_called_once_with(group="fs.opener", name="example")
            first.load.assert_called_once()
            second.load.assert_not_called()
        with patch("fs.opener.registry.entry_points", return_value=[]):
            self.assertIs(registry.get_opener("example"), installed)

    def test_plugin_errors_are_reported(self):
        registry = Registry(load_extern=True)
        for result in (RuntimeError("broken import"), str):
            with self.subTest(result=result):
                point = Mock()
                if isinstance(result, Exception):
                    point.load.side_effect = result
                else:
                    point.load.return_value = result
                with patch(
                    "fs.opener.registry.entry_points", return_value=[point]
                ):
                    with self.assertRaises(EntryPointError):
                        registry.get_opener("example")

    def test_modern_jinja_loader_and_extensions(self):
        with MemoryFS() as filesystem:
            filesystem.writetext("base.jj2", "{% block body %}{% endblock %}")
            filesystem.writetext(
                "child.jj2",
                '{% extends "base.jj2" %}{% block body %}'
                "{% set result = [] %}{% for n in [1, 2, 3] %}"
                "{% if n == 2 %}{% continue %}{% endif %}"
                "{% do result.append(n) %}{% endfor %}"
                '{{ result|join(",") }}{% endblock %}',
            )
            loader = jinja2_fsloader.FSLoader(filesystem)
            environment = jinja2.Environment(
                loader=loader,
                extensions=["jinja2.ext.do", "jinja2.ext.loopcontrols"],
            )
            self.assertEqual(
                environment.get_template("child.jj2").render(), "1,3"
            )
            self.assertEqual(
                loader.list_templates(), ["base.jj2", "child.jj2"]
            )
            with self.assertRaises(jinja2.TemplateNotFound):
                environment.get_template("missing.jj2")


if __name__ == "__main__":
    unittest.main()
