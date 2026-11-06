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
        self.repo = root / "dotfiles 'shared $settings"
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
            self.assertFalse(self.zshrc.is_symlink())
            lines = self.zshrc.read_text().splitlines()
            self.assertEqual(sum(line.startswith("source ") for line in lines), 1)
            self.assertNotIn("# BEGIN mydotfiles zsh", lines)
            self.assertNotIn("# END mydotfiles zsh", lines)
            self.assertIn("Dotfiles installation complete.", output)
        else:
            self.assertIn("Dotfiles installation incomplete", output)
            self.assertIn("Codex defaults installed: yes", output)
        return text

    def test_empty_placeholder_and_rerun(self):
        self.zshrc.touch()
        first = self.install()
        first_zshrc = self.zshrc.read_text()
        self.assertEqual(self.install(), first)
        self.assertEqual(self.zshrc.read_text(), first_zshrc)

    def test_fresh_home(self):
        shutil.rmtree(self.config.parent)
        # install() also checks preservation of existing settings.
        result = subprocess.run(["bash", str(self.repo / "install.sh")],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.zshrc.is_symlink())
        self.assertIn('model_reasoning_effort = "high"', self.config.read_text())

    def test_nonempty_file_is_preserved(self):
        for contents in ("export MY_SETTING=yes\n", " \n\t"):
            with self.subTest(contents=contents):
                self.zshrc.write_text(contents)
                self.install()
                first = self.zshrc.read_text()
                self.assertTrue(first.endswith(contents))
                self.install()
                self.assertEqual(self.zshrc.read_text(), first)

    def test_old_managed_links_are_rejected(self):
        for target in (self.repo / "zsh/.zshrc",
                       Path("..") / self.repo.name / "zsh/.zshrc"):
            with self.subTest(target=target):
                if self.zshrc.is_symlink() or self.zshrc.exists():
                    self.zshrc.unlink()
                self.zshrc.symlink_to(target)
                before = (self.repo / "zsh/.zshrc").read_bytes()
                self.install(success=False)
                self.assertTrue(self.zshrc.is_symlink())
                self.assertEqual(self.zshrc.readlink(), target)
                self.assertEqual((self.repo / "zsh/.zshrc").read_bytes(), before)

    def test_shared_updates_and_local_overrides(self):
        shared = self.repo / "zsh/.zshrc"
        shared.write_text('SHARED_VALUE=first\nLOCAL_VALUE=shared\n')
        self.zshrc.write_text('LOCAL_VALUE=local\nalias databox="echo databox"\n')
        self.zshrc.chmod(0o640)
        self.install()
        self.assertEqual(self.zshrc.stat().st_mode & 0o777, 0o640)

        def read_settings():
            result = subprocess.run(
                ["zsh", "-f", "-c", 'source "$HOME/.zshrc"; '
                 'print -r -- "$SHARED_VALUE/$LOCAL_VALUE"; alias databox'],
                env=self.env, capture_output=True, text=True, check=True)
            return result.stdout

        self.assertIn("first/local", read_settings())
        shared.write_text('SHARED_VALUE=updated\nLOCAL_VALUE=shared\n')
        self.assertIn("updated/local", read_settings())
        self.assertIn("databox=", read_settings())
        with self.zshrc.open("a") as stream:
            stream.write("# Added by a local tool\n")
        self.install()
        self.assertTrue(self.zshrc.read_text().endswith("# Added by a local tool\n"))

    def test_existing_source_line_leaves_file_unchanged(self):
        self.install()
        contents = self.zshrc.read_bytes() + b"# Local setting without final newline"
        self.zshrc.write_bytes(contents)
        self.install()
        self.assertEqual(self.zshrc.read_bytes(), contents)

    def test_duplicate_source_lines_are_rejected(self):
        self.install()
        source_line = self.zshrc.read_bytes()
        contents = source_line + source_line + b"# local settings\n"
        self.zshrc.write_bytes(contents)
        self.install(success=False)
        self.assertEqual(self.zshrc.read_bytes(), contents)

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

    def test_codex_directory_symlink_is_rejected(self):
        codex_dir = self.config.parent
        shutil.rmtree(codex_dir)
        target = self.repo / "codex/.codex"
        before = (target / "config.toml").read_bytes()
        codex_dir.symlink_to(target, target_is_directory=True)
        result = subprocess.run(["bash", str(self.repo / "install.sh")],
                                env=self.env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected a real directory", result.stderr)
        self.assertEqual(codex_dir.readlink(), target)
        self.assertEqual((target / "config.toml").read_bytes(), before)

    def test_old_skill_file_links_are_rejected(self):
        skill = next((self.repo / "codex/.agents/skills").glob("*/SKILL.md")).parent
        target = self.home / ".agents/skills" / skill.name
        target.mkdir(parents=True)
        old_link = target / "SKILL.md"
        old_link.symlink_to(skill / "SKILL.md")
        self.install(success=False)
        self.assertFalse(target.is_symlink())
        self.assertEqual(old_link.readlink(), skill / "SKILL.md")

    def test_gh_failure_leaves_defaults_installed(self):
        self.env["TEST_GH_STATUS"] = "42"
        self.install(success=False)


if __name__ == "__main__":
    unittest.main()
