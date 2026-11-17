"""Build and run all automated checks from any working directory."""
import shutil
import subprocess
import sys

from site_tools.project import ROOT


def check():
    node = shutil.which('node')
    if not node:
        raise SystemExit('Node.js is needed for JavaScript checks; Python alone can still build and serve the site.')
    commands = [
        [sys.executable, 'scripts/build.py'],
        [sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts/tests', '-t', 'scripts'],
        [sys.executable, 'scripts/validate.py'],
    ]
    commands.extend([node, '--check', str(path.relative_to(ROOT))] for path in sorted((ROOT / 'src/assets').glob('*.js')))
    commands.extend([node, str(path.relative_to(ROOT))] for path in sorted((ROOT / 'scripts/tests/js').glob('test_*.cjs')))
    for command in commands:
        subprocess.run(command, cwd=ROOT, check=True)
    print('All automated checks passed. Browser layout and native dialog behavior still need visual testing.')


if __name__ == '__main__':
    check()
