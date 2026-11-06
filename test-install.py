#!/usr/bin/env python3
"""Exercise the installer with real Stow, without changing the user's home."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parent


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.repo = root / "dotfiles"
        self.repo.mkdir()
        for name in ("codex", "git", "tmux", "zsh"):
            shutil.copytree(REPO / name, self.repo / name, symlinks=True)
        shutil.copy2(REPO / "install.sh", self.repo)
        self.home = root / "home"
        self.home.mkdir()
        self.zshrc = self.home / ".zshrc"
        self.config = self.home / ".codex/config.toml"
        self.config.parent.mkdir()
        self.config.write_text('model = "old"\nmodel_reasoning_effort = "low"\n'
                               '[desktop]\nappearanceTheme = "system"\n'
                               '[profiles.custom]\nmodel_reasoning_effort = "low"\n')
        bin_dir = root / "bin"
        bin_dir.mkdir()
        gh = bin_dir / "gh"
        gh.write_text('#!/bin/sh\nexit "${TEST_GH_STATUS:-0}"\n')
        gh.chmod(0o755)
        plugin = self.home / ".tmux/plugins/tpm/bin/install_plugins"
        plugin.parent.mkdir(parents=True)
        plugin.write_text("#!/bin/sh\nexit 0\n")
        plugin.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.home),
                        PATH=f"{bin_dir}:{os.environ['PATH']}")

    def install(self, success=True):
        result = subprocess.run(["bash", str(self.repo / "install.sh")],
                                env=self.env, capture_output=True, text=True)
        output = result.stdout + result.stderr
        self.assertEqual(result.returncode == 0, success, output)
        text = self.config.read_text()
        top_level = text.split("[desktop]")[0]
        self.assertEqual(top_level.count('model = "gpt-6.1-sol"'), 1)
        self.assertEqual(top_level.count('model_reasoning_effort = "high"'), 1)
        self.assertNotIn('"old"', top_level)
        self.assertNotIn('"low"', top_level)
        self.assertIn('[desktop]\nappearanceTheme = "system"', text)
        self.assertIn('[profiles.custom]\nmodel_reasoning_effort = "low"', text)
        if success:
            self.assertTrue(self.zshrc.is_symlink())
            self.assertEqual(self.zshrc.resolve(), (self.repo / "zsh/.zshrc").resolve())
            self.assertIn("Dotfiles installation complete.", output)
        else:
            self.assertIn("Dotfiles installation incomplete", output)
            self.assertIn("Codex defaults installed: yes", output)
        return text

    def test_empty_placeholder_and_rerun(self):
        self.zshrc.touch()
        first = self.install()
        self.assertEqual(self.install(), first)

    def test_fresh_home(self):
        shutil.rmtree(self.config.parent)
        # install() also checks preservation of existing settings.
        result = subprocess.run(["bash", str(self.repo / "install.sh")],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.zshrc.is_symlink())
        self.assertIn('model_reasoning_effort = "high"', self.config.read_text())

    def test_nonempty_file_is_preserved(self):
        for contents in ("export MY_SETTING=yes\n", " \n\t"):
            with self.subTest(contents=contents):
                self.zshrc.write_text(contents)
                self.install(success=False)
                self.assertFalse(self.zshrc.is_symlink())
                self.assertEqual(self.zshrc.read_text(), contents)

    def test_foreign_and_dangling_links_are_preserved(self):
        target = self.home / "other-zshrc"
        target.touch()
        self.zshrc.symlink_to(target)
        self.install(success=False)
        self.assertEqual(self.zshrc.readlink(), target)
        self.assertEqual(target.read_bytes(), b"")
        target.unlink()
        self.install(success=False)
        self.assertEqual(self.zshrc.readlink(), target)

    def test_directory_is_preserved(self):
        self.zshrc.mkdir()
        marker = self.zshrc / "keep"
        marker.write_text("local content")
        self.install(success=False)
        self.assertEqual(marker.read_text(), "local content")

    def test_gh_failure_leaves_defaults_installed(self):
        self.env["TEST_GH_STATUS"] = "42"
        self.install(success=False)


if __name__ == "__main__":
    unittest.main()
