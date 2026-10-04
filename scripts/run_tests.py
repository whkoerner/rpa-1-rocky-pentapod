"""Run every existing host suite; never hide a failed suite behind a later success."""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITES = ('language/tests', 'software/rpa_link/tests', 'software/simulation/tests', 'software/brain/tests', 'software/rocky/tests')


def main():
    print(f"Python: {sys.version}\nExecutable: {sys.executable}", flush=True)
    if shutil.which('git'):
        subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, check=False)
        subprocess.run(['git', 'status', '--short'], cwd=ROOT, check=False)
    failed = []
    for suite in SUITES:
        print(f"\nSuite: {suite}", flush=True)
        if subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', suite, '-v'], cwd=ROOT, stderr=subprocess.STDOUT).returncode:
            failed.append(suite)
    if shutil.which('node'):
        if subprocess.run(['node', 'software/brain_web/protocol.test.js'], cwd=ROOT, stderr=subprocess.STDOUT).returncode:
            failed.append('browser protocol')
    else:
        print('NOT RUN: browser protocol tests (Node.js is not installed). Python results remain valid.')
    print('FAILED: ' + ', '.join(failed) if failed else 'All available host suites passed. Windows listening, real-model, offline, Pi and hardware acceptance are separate.')
    return bool(failed)


if __name__ == '__main__':
    raise SystemExit(main())
