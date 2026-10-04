"""Real cmd/PowerShell/environment checks on Windows CI; listening remains manual."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv

ROOT = Path(__file__).resolve().parents[3]


@unittest.skipUnless(os.name == 'nt', 'requires Windows cmd and PowerShell')
class WindowsLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='Rocky launcher with spaces ')
        self.root = Path(self.temp.name) / 'project with spaces'
        self.root.mkdir()
        for name in ('scripts', 'software', 'language'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info'))
        shutil.copy2(ROOT / 'Rocky.bat', self.root / 'Rocky.bat')
        self.env = dict(os.environ)
        self.env.pop('ROCKY_PYTHON', None)
        self.env['PYTHONPATH'] = str(self.root / 'software')

    def tearDown(self):
        self.temp.cleanup()

    def ps(self, command):
        script = str(self.root / 'scripts' / 'Launch-Rocky.ps1').replace("'", "''")
        return subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', f". '{script}'; {command}"], env=self.env, cwd=Path(self.temp.name), capture_output=True, text=True, timeout=30)

    def test_double_click_entry_from_other_directory_and_spaced_path(self):
        # cmd executes the same .bat entry that Explorer uses; no desktop mutation.
        result = subprocess.run(['cmd.exe', '/d', '/c', str(self.root / 'Rocky.bat')], input='0\n', cwd=Path(self.temp.name), env=self.env, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Rocky desktop menu', result.stdout)

    def test_missing_environment_gives_exact_repair_without_creating_it(self):
        result = self.ps('$p = Find-Python; if ($p) { exit 9 }')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('-Action setup', result.stdout)
        self.assertIn(str(self.root / 'Rocky.bat'), result.stdout)
        self.assertFalse((self.root / '.venv-rocky').exists())

    def test_valid_environment_and_broken_explicit_override(self):
        target = self.root / '.venv-rocky'
        venv.EnvBuilder(system_site_packages=True, with_pip=False).create(target)
        result = self.ps('$p = Find-Python; if (-not $p) { exit 9 }; Write-Host $p')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(str(target / 'Scripts' / 'python.exe'), result.stdout)
        broken = self.root / 'broken python.exe'
        broken.write_text('not an executable')
        self.env['ROCKY_PYTHON'] = str(broken)
        result = self.ps('$p = Find-Python; if ($p) { exit 9 }')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('repair command', result.stdout)
