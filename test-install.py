#!/usr/bin/env python3
"""Exercise the installer with real Stow, without changing the user's home."""
import os
import json
import base64
import pty
import select
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest

import tomlkit

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
        shutil.copy2(REPO / "install-codex-config.py", self.repo)
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
        uv = bin_dir / "uv"
        uv.write_text(f'''#!{sys.executable}
import os, sys
assert sys.argv[1:4] == ['run', '--no-project', '--script'], sys.argv
if os.environ.get('TEST_UV_STATUS'):
    sys.exit(int(os.environ['TEST_UV_STATUS']))
os.execv({sys.executable!r}, [{sys.executable!r}] + sys.argv[4:])
''')
        uv.chmod(0o755)
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
        self.last_install = result
        return text

    def update_config(self, success=True):
        result = subprocess.run(
            ["python3", str(self.repo / "install-codex-config.py"),
             str(self.repo / "codex/.codex/config.toml"), str(self.config)],
            capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return self.config.read_text()

    def test_codex_preserves_toml_syntax_and_comments(self):
        original = '''# Personal preferences
"model" = 'old' # keep this comment
model_reasoning_effort = """
low"""
description = """
# BEGIN mydotfiles — edit in the dotfiles repo
[not_a_table]
model = "inside a string"
# END mydotfiles
"""
features.web_search = true

[desktop] # desktop preferences
appearanceTheme = "system"
'''
        self.config.write_text(original)
        self.config.chmod(0o640)
        updated = self.update_config()
        expected = tomlkit.parse(original).unwrap()
        expected.update(model="gpt-6.1-sol", model_reasoning_effort="high")
        self.assertEqual(tomlkit.parse(updated).unwrap(), expected)
        self.assertIn('# keep this comment', updated)
        self.assertIn('features.web_search = true', updated)
        self.assertIn('[desktop] # desktop preferences', updated)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o640)
        self.assertEqual(self.update_config(), updated)

    def test_codex_removes_legacy_markers(self):
        self.config.write_text(
            '# BEGIN mydotfiles — edit in the dotfiles repo\n'
            + self.config.read_text().split('[desktop]')[0]
            + '# END mydotfiles\n[desktop]\nappearanceTheme = "system"\n')
        updated = self.update_config()
        self.assertNotIn('# BEGIN mydotfiles', updated)
        self.assertNotIn('# END mydotfiles', updated)
        self.assertEqual(tomlkit.parse(updated)['model'], 'gpt-6.1-sol')
        self.assertEqual(self.update_config(), updated)

    def test_codex_invalid_toml_is_unchanged(self):
        for contents in ('model = "one"\nmodel = "two"\n', '[broken\n'):
            with self.subTest(contents=contents):
                self.config.write_text(contents)
                self.assertEqual(self.update_config(success=False), contents)

    def test_codex_missing_keys_are_added_at_top_level(self):
        self.config.write_text('# Local settings\n[custom]\nmodel = "local"\n')
        updated = tomlkit.parse(self.update_config()).unwrap()
        self.assertEqual(updated, {
            'model': 'gpt-6.1-sol', 'model_reasoning_effort': 'high',
            'custom': {'model': 'local'},
        })

    def test_codex_invalid_defaults_leave_destination_unchanged(self):
        original = self.config.read_text()
        (self.repo / 'codex/.codex/config.toml').write_text('model = [broken\n')
        self.assertEqual(self.update_config(success=False), original)

    def test_codex_config_symlink_is_unchanged(self):
        self.config.unlink()
        target = self.repo / 'codex/.codex/config.toml'
        before = target.read_bytes()
        self.config.symlink_to(target)
        self.update_config(success=False)
        self.assertEqual(target.read_bytes(), before)
        self.assertTrue(self.config.is_symlink())

    def test_empty_placeholder_and_rerun(self):
        self.zshrc.touch()
        first = self.install()
        first_zshrc = self.zshrc.read_text()
        self.assertEqual(self.install(), first)
        self.assertEqual(self.zshrc.read_text(), first_zshrc)

    def hide_uv_from_path(self):
        bin_dir = Path(self.env['PATH'].split(os.pathsep)[0])
        self.env['PATH'] = os.pathsep.join(
            entry for entry in self.env['PATH'].split(os.pathsep)
            if entry == str(bin_dir) or not (Path(entry) / 'uv').exists())
        template = self.home / 'uv-template'
        (bin_dir / 'uv').rename(template)
        return bin_dir, template

    def test_uv_in_user_bin_is_reused(self):
        _, template = self.hide_uv_from_path()
        target = self.home / '.local/bin/uv'
        target.parent.mkdir(parents=True)
        template.rename(target)
        self.install()
        self.assertTrue(target.is_file())

    def test_missing_uv_is_installed_without_shell_changes(self):
        bin_dir, template = self.hide_uv_from_path()
        calls = self.home / 'uv-downloads'
        installer = ('set -e\n'
                     '[ "$UV_NO_MODIFY_PATH" = 1 ]\n'
                     'mkdir -p "$UV_INSTALL_DIR"\n'
                     f'cp {shlex.quote(str(template))} "$UV_INSTALL_DIR/uv"\n')
        curl = bin_dir / 'curl'
        curl.write_text(f'''#!{sys.executable}
import pathlib, sys
assert sys.argv[1:3] == ['-LsSf', 'https://astral.sh/uv/install.sh'], sys.argv
assert sys.argv[3] == '-o', sys.argv
pathlib.Path(sys.argv[4]).write_text({installer!r})
with open({str(calls)!r}, 'a') as stream:
    stream.write('download\\n')
''')
        curl.chmod(0o755)
        self.zshrc.write_text('# local shell settings\n')
        self.install()
        self.install()
        self.assertEqual(calls.read_text(), 'download\n')
        self.assertTrue(self.zshrc.read_text().endswith('# local shell settings\n'))

    def test_uv_failure_leaves_config_unchanged(self):
        original = self.config.read_bytes()
        self.env['TEST_UV_STATUS'] = '42'
        result = subprocess.run(['bash', str(self.repo / 'install.sh')],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 42)
        self.assertEqual(self.config.read_bytes(), original)
        self.assertIn('Codex defaults installed: no', result.stderr)

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

    def setup_figma_checkout(self):
        checkout = self.home / "figma/figma"
        checkout.mkdir(parents=True)
        subprocess.run(["git", "init", str(checkout)], check=True, capture_output=True)
        subprocess.run(["git", "-C", str(checkout), "remote", "add", "origin",
                        "https://example.com/figma.git"], check=True)
        minifig = checkout / "minifig"
        minifig.write_text('#!/bin/sh\nprintf "%s\\n" "$PWD" "$@" >> minifig-calls\n'
                           'if [ -n "${TEST_MINIFIG_ERROR:-}" ]; then\n'
                           '  if [ "${TEST_MINIFIG_RECOVER:-0}" = 1 ] && [ -f minifig-failed ]; then\n'
                           '    exit 0\n'
                           '  fi\n'
                           '  touch minifig-failed\n'
                           '  echo "$TEST_MINIFIG_ERROR" >&2\n'
                           'fi\n'
                           'exit "${TEST_MINIFIG_STATUS:-0}"\n')
        minifig.chmod(0o755)
        return checkout

    def test_install_selects_billing_profile_on_each_run(self):
        checkout = self.setup_figma_checkout()
        self.install()
        self.install()
        self.assertEqual((checkout / "minifig-calls").read_text().splitlines(),
                         [str(checkout), "profile", "set", "team/billing", "--wait"] * 2)

    def setup_statsig_checkout(self):
        checkout = self.setup_figma_checkout()
        wrapper = checkout / 'devex/mcp-support/statsig-mcp-server'
        wrapper.parent.mkdir(parents=True)
        wrapper.touch()  # Configuration test; never run an MCP or fetch credentials.
        config = checkout / '.codex/config.toml'
        config.parent.mkdir()
        config.write_text('# Project settings\n[mcp_servers.statsig]\n'
                          'url = "https://api.statsig.com/v1/mcp"\n'
                          'startup_timeout_sec = 90\n'
                          'disabled_tools = ["mutate"]\n'
                          '[mcp_servers.other]\nurl = "https://example.com/mcp"\n')
        self.env['FIGMA_CODER_INSTANCE_TYPE'] = 'devbox'
        return checkout, config, wrapper

    def test_coder_statsig_uses_managed_wrapper_and_preserves_policies(self):
        checkout, config, wrapper = self.setup_statsig_checkout()
        config.chmod(0o640)
        self.install()
        first = config.read_bytes()
        self.install()
        self.assertEqual(config.read_bytes(), first)
        document = tomlkit.parse(config.read_text()).unwrap()
        server = document['mcp_servers']['statsig']
        self.assertNotIn('url', server)
        self.assertEqual(server['command'], str(wrapper.resolve()))
        self.assertTrue(Path(server['command']).is_absolute())
        self.assertEqual(server['cwd'], str(checkout.resolve()))
        self.assertEqual(server['env'], {'DEVCONTAINER': '1', 'INSTANCE_TYPE': 'devbox'})
        self.assertTrue(server['enabled'])
        self.assertEqual(server['startup_timeout_sec'], 90)
        self.assertEqual(server['disabled_tools'], ['mutate'])
        self.assertEqual(document['mcp_servers']['other']['url'], 'https://example.com/mcp')
        self.assertIn('# Project settings', config.read_text())
        self.assertEqual(config.stat().st_mode & 0o777, 0o640)

    def test_coder_statsig_bootstraps_missing_project_config(self):
        _, config, _ = self.setup_statsig_checkout()
        config.rename(config.with_name('config.toml.example'))
        self.install()
        self.assertIn('command', tomlkit.parse(config.read_text())['mcp_servers']['statsig'])

    def test_statsig_is_unchanged_outside_coder_devbox(self):
        _, config, _ = self.setup_statsig_checkout()
        original = config.read_bytes()
        for instance in ('', 'prodbox'):
            with self.subTest(instance=instance):
                self.env['FIGMA_CODER_INSTANCE_TYPE'] = instance
                self.install()
                self.assertEqual(config.read_bytes(), original)

    def test_coder_statsig_rejects_custom_and_invalid_config(self):
        _, config, _ = self.setup_statsig_checkout()
        for original in ('[mcp_servers.statsig]\nurl = "https://custom.example/mcp"\n',
                         '[broken\n'):
            with self.subTest(original=original):
                config.write_text(original)
                self.install(success=False)
                self.assertEqual(config.read_text(), original)

    def test_minifig_failure_fails_install(self):
        checkout = self.setup_figma_checkout()
        self.env["TEST_MINIFIG_STATUS"] = "42"
        self.env["TEST_MINIFIG_ERROR"] = "Unknown profile team/billing"
        self.install(success=False)
        self.assertEqual(self.last_install.returncode, 42)
        self.assertNotIn("retrying", self.last_install.stderr)
        self.assertEqual(len((checkout / "minifig-calls").read_text().splitlines()), 5)

    def minifig_connection_refused(self):
        self.env["TEST_MINIFIG_STATUS"] = "1"
        self.env["TEST_MINIFIG_ERROR"] = (
            "Failed to connect to Minifig server: initialize RPC client: "
            "dial tcp 127.0.0.1:7237: connect: connection refused")

    def test_minifig_startup_race_recovers(self):
        checkout = self.setup_figma_checkout()
        self.minifig_connection_refused()
        self.env["TEST_MINIFIG_RECOVER"] = "1"
        self.install()
        self.assertIn("retrying in 5 seconds", self.last_install.stderr)
        self.assertEqual(len((checkout / "minifig-calls").read_text().splitlines()), 10)

    def test_minifig_connection_timeout_fails_install(self):
        self.setup_figma_checkout()
        self.minifig_connection_refused()
        self.install(success=False)
        self.assertEqual(self.last_install.returncode, 1)
        self.assertIn("Timed out after 120 seconds", self.last_install.stderr)
        self.assertIn("connect: connection refused", self.last_install.stderr)

    def test_minifig_other_connection_error_is_not_retried(self):
        self.setup_figma_checkout()
        self.env["TEST_MINIFIG_STATUS"] = "7"
        self.env["TEST_MINIFIG_ERROR"] = (
            "Failed to connect to Minifig server: permission denied")
        self.install(success=False)
        self.assertEqual(self.last_install.returncode, 7)
        self.assertNotIn("retrying", self.last_install.stderr)

    def setup_mcp_init(self):
        checkout, _, _ = self.setup_statsig_checkout()
        profile = checkout / 'devbox-profiles/team/billing.yml'
        profile.parent.mkdir(parents=True)
        profile.write_text('name: billing\nservice_groups:\n'
                           '  - name: sinatra\n    image_source: local\n'
                           '  - name: pixie\n    image_source: local\n')
        self.env['MCP_CALLS'] = str(self.home / 'mcp-calls')
        (checkout / 'minifig').write_text(f'''#!{sys.executable}
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['MCP_CALLS'], 'a') as stream:
    stream.write('minifig ' + ' '.join(args) + '\\n')
if args == ['system', 'info']:
    print(json.dumps({{'active_profile': 'team/billing'}}))
if args == ['profile', 'list']:
    marker = Path('profile-discovered')
    if marker.exists():
        print('  personal/cpalmer-mcp-init')
    else:
        marker.touch()
        print('  team/billing')
if args[:2] == ['profile', 'set']:
    assert Path('profile-discovered').exists(), 'profile selected before discovery'
if args == ['prebuild', 'inspect']:
    images = [] if os.environ.get('TEST_NO_PIXIE_PREBUILD') else [{{'service': 'pixie'}}]
    print('Active prebuild: test\\n')
    print(json.dumps({{'prebuild': {{'service_images': images}}}}))
if args == ['service', 'wait', 'pixie']:
    sys.exit(int(os.environ.get('TEST_PIXIE_STATUS', '0')))
''')
        codex = Path(self.env['PATH'].split(os.pathsep)[0]) / 'codex'
        codex.write_text(f'''#!{sys.executable}
import os, sys
def record(value):
    with open(os.environ['MCP_CALLS'], 'a') as stream:
        stream.write(value + '\\n')
args = sys.argv[1:]
if args[:2] == ['mcp', 'get']:
    assert args == ['mcp', 'get', 'statsig'], args
    record('managed statsig')
else:
    assert args[:2] == ['mcp', 'login'] and args[3:] == ['--no-browser'], args
    server = args[2]
    record('login-start ' + server)
    if os.environ.get('TEST_LOGIN_FAILURE') == server:
        sys.exit(37)
    os.write(2, b'Help: https://example.com/docs\\n')
    url = 'https://example.com/oauth/authorize?client_id=' + server + '&response_type=code&code_challenge=test'
    os.write(2, url[:35].encode())
    os.write(2, (url[35:] + '\\n').encode())
    os.write(1, b'Paste redirect URL: ')
    reply = b''
    while not reply.endswith(b'\\n'):
        char = os.read(0, 1)
        if not char:
            sys.exit(38)
        reply += char
    assert reply == b'approve\\n', reply
    record('login-done ' + server)
''')
        codex.chmod(0o755)
        return checkout, profile

    def run_mcp_init(self):
        return subprocess.run(
            ['zsh', '-f', '-c', f'source {shlex.quote(str(self.repo / "zsh/.zshrc"))}; mcp-init'],
            env=self.env, input='approve\n' * 4, capture_output=True,
            text=True, timeout=20)

    def test_mcp_init_prebuilt_profile_and_sequential_logins(self):
        checkout, profile = self.setup_mcp_init()
        original = profile.read_bytes()
        result = self.run_mcp_init()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = Path(self.env['MCP_CALLS']).read_text().splitlines()
        self.assertEqual(calls, [
            'minifig system info',
            'minifig profile list', 'minifig profile list',
            'minifig prebuild inspect',
            'minifig profile set personal/cpalmer-mcp-init --wait',
            'minifig service start pixie', 'minifig service wait pixie',
            'login-start figma-coderbox', 'login-done figma-coderbox',
            'login-start figma-admin-coderbox', 'login-done figma-admin-coderbox',
            'login-start figma-mcp-staging', 'login-done figma-mcp-staging',
            'managed statsig', 'login-start hex', 'login-done hex',
        ])
        target = checkout / 'devbox-profiles/personal/cpalmer-mcp-init.yml'
        rendered = subprocess.check_output(['yq', '-o=json', '.', str(target)], text=True)
        self.assertEqual(json.loads(rendered), {
            'name': 'cpalmer-mcp-init', 'service_groups': [
                {'name': 'sinatra', 'image_source': 'local'},
                {'name': 'pixie', 'image_source': 'prebuilt'},
            ]})
        self.assertEqual(profile.read_bytes(), original)
        first = target.read_bytes()
        self.assertEqual(self.run_mcp_init().returncode, 0)
        self.assertEqual(target.read_bytes(), first)
        self.assertEqual(list(target.parent.glob('*.yml.*')), [])

    def test_mcp_init_stops_when_login_fails(self):
        self.setup_mcp_init()
        self.env['TEST_LOGIN_FAILURE'] = 'figma-admin-coderbox'
        result = self.run_mcp_init()
        self.assertEqual(result.returncode, 37, result.stdout + result.stderr)
        calls = Path(self.env['MCP_CALLS']).read_text()
        self.assertIn('login-done figma-coderbox', calls)
        self.assertNotIn('login-start figma-mcp-staging', calls)
        self.assertNotIn('managed statsig', calls)

    def test_mcp_init_reports_missing_pixie_prebuild(self):
        self.setup_mcp_init()
        self.env['TEST_NO_PIXIE_PREBUILD'] = '1'
        result = self.run_mcp_init()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Minifig will build Pixie locally', result.stdout)
        self.assertNotIn('Starting prebuilt Pixie', result.stdout)

    def test_mcp_init_waits_for_healthy_pixie_before_login(self):
        self.setup_mcp_init()
        self.env['TEST_PIXIE_STATUS'] = '1'
        result = self.run_mcp_init()
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn('login-start', Path(self.env['MCP_CALLS']).read_text())
        self.assertIn('Pixie did not become healthy', result.stderr)

    def test_mcp_init_copies_each_url_before_waiting_for_approval(self):
        self.setup_mcp_init()
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        process = subprocess.Popen(
            ['zsh', '-f', '-c', f'source {shlex.quote(str(self.repo / "zsh/.zshrc"))}; mcp-init'],
            env=self.env, stdin=subprocess.PIPE, stdout=slave, stderr=slave)
        os.close(slave)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        output = b''

        def read_until(marker):
            nonlocal output
            while marker not in output:
                ready, _, _ = select.select([master], [], [], 10)
                self.assertTrue(ready, output.decode(errors='replace'))
                chunk = os.read(master, 4096)
                self.assertTrue(chunk)
                output += chunk

        for server in ('figma-coderbox', 'figma-admin-coderbox', 'figma-mcp-staging', 'hex'):
            url = ('https://example.com/oauth/authorize?client_id=' + server
                   + '&response_type=code&code_challenge=test').encode()
            read_until(b'\x1b]52;c;' + base64.b64encode(url) + b'\x07')
            read_until(b'Paste redirect URL: ')
            self.assertNotIn('login-done ' + server,
                             Path(self.env['MCP_CALLS']).read_text())
            process.stdin.write(b'approve\n')
            process.stdin.flush()
        process.communicate(timeout=10)
        self.assertEqual(process.returncode, 0, output.decode(errors='replace'))
        self.assertEqual(output.count(b'\x1b]52;c;'), 4)


if __name__ == "__main__":
    unittest.main()
