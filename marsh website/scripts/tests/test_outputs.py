"""Regression tests for isolated builds and safe generated-directory replacement."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from site_tools.builder import build
from site_tools.project import ROOT
from site_tools.validation import validate
from site_tools.outputs import ensure_local_directory
from site_tools import outputs


class OutputsTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        shutil.copytree(ROOT / 'src', self.root / 'src')

    def remove_page(self):
        path = self.root / 'src/navigation.json'
        items = json.loads(path.read_text(encoding='utf-8'))
        for item in items:
            if 'children' in item:
                item['children'] = [page for page in item['children'] if page['slug'] != 'pathway-flowchart']
        path.write_text(json.dumps(items), encoding='utf-8')

    def snapshot(self, directory=None):
        directory = directory or self.root / 'build'
        return {path.relative_to(directory).as_posix(): path.read_bytes() for path in directory.rglob('*') if path.is_file()}

    def change_home_and_styles(self):
        for name, comment in (('pages/home.html', '<!-- changed -->'), ('assets/styles.css', '/* changed */')):
            path = self.root / 'src' / name
            path.write_text(path.read_text(encoding='utf-8') + '\n' + comment, encoding='utf-8')

    def test_build_contains_only_public_files(self):
        build(self.root)
        self.assertTrue((self.root / 'build/index.html').is_file())
        self.assertTrue((self.root / 'build/assets/styles.css').is_file())
        for name in ('src', 'scripts', 'README.md'):
            self.assertFalse((self.root / 'build' / name).exists())
        self.assertFalse((self.root / 'index.html').exists())
        validate(self.root)

    def test_rebuild_removes_stale_pages_and_assets(self):
        build(self.root)
        old_asset = self.root / 'build/assets/old-image.txt'
        old_asset.write_text('stale output', encoding='utf-8')
        self.remove_page()
        build(self.root)
        self.assertFalse((self.root / 'build/pathway-flowchart').exists())
        self.assertFalse(old_asset.exists())
        self.assertTrue((self.root / 'src/pages/pathway-flowchart.html').is_file())
        validate(self.root)

    def test_source_error_keeps_previous_build(self):
        build(self.root)
        home = self.root / 'build/index.html'
        previous = home.read_bytes()
        (self.root / 'src/pages/home.html').write_text('<p>[@missing-source]</p>', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Unknown citation key'):
            build(self.root)
        self.assertEqual(home.read_bytes(), previous)
        self.assertEqual(list(self.root.glob('.build-*')), [])

    def test_unknown_build_directory_is_preserved(self):
        directory = self.root / 'build'
        directory.mkdir()
        personal = directory / 'notes.txt'
        personal.write_text('keep', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'not recognized as generated'):
            build(self.root)
        self.assertEqual(personal.read_text(encoding='utf-8'), 'keep')
        self.assertEqual(list(self.root.glob('.build-*')), [])

    def test_empty_build_directory_can_be_reused_after_cleanup(self):
        (self.root / 'build').mkdir()
        build(self.root)
        validate(self.root)

    def test_validation_catches_unexpected_and_changed_output(self):
        build(self.root)
        extra = self.root / 'build/extra.txt'
        extra.write_text('unexpected', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'unexpected files'):
            validate(self.root)
        extra.unlink()
        (self.root / 'build/index.html').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Generated file changed'):
            validate(self.root)

    def test_validation_detects_navigation_change(self):
        build(self.root)
        self.remove_page()
        with self.assertRaisesRegex(ValueError, 'inventory differs'):
            validate(self.root)

    def test_cleanup_cannot_target_source(self):
        with self.assertRaisesRegex(ValueError, 'Not a generated build directory'):
            ensure_local_directory(self.root / 'src', self.root)
        self.assertTrue((self.root / 'src/pages/home.html').is_file())

    def test_rebuild_works_while_build_is_current_directory(self):
        build(self.root)
        previous = Path.cwd()
        try:
            os.chdir(self.root / 'build')
            build(self.root)
        finally:
            os.chdir(previous)
        validate(self.root)

    def test_partial_write_failure_restores_previous_files(self):
        build(self.root)
        previous = self.snapshot()
        self.change_home_and_styles()
        self.remove_page()
        copy_file = outputs.copy_atomic
        copies = 0

        def fail_after_one_copy(source, destination):
            nonlocal copies
            copies += 1
            if copies == 2:
                raise OSError('simulated write failure')
            copy_file(source, destination)

        with patch.object(outputs, 'copy_atomic', side_effect=fail_after_one_copy):
            with self.assertRaisesRegex(OSError, 'simulated write failure'):
                build(self.root)
        self.assertEqual(self.snapshot(), previous)
        self.assertEqual(list(self.root.glob('.build-*')), [])

    def test_manifest_failure_restores_obsolete_pages_and_assets(self):
        build(self.root)
        previous = self.snapshot()
        self.change_home_and_styles()
        self.remove_page()
        (self.root / 'src/assets/added.txt').write_text('new file', encoding='utf-8')
        copy_file = outputs.copy_atomic

        def fail_manifest(source, destination):
            if destination.name == outputs.MANIFEST:
                raise OSError('simulated manifest failure')
            copy_file(source, destination)

        with patch.object(outputs, 'copy_atomic', side_effect=fail_manifest):
            with self.assertRaisesRegex(OSError, 'simulated manifest failure'):
                build(self.root)
        self.assertEqual(self.snapshot(), previous)
        self.assertEqual(list(self.root.glob('.build-*')), [])

    def test_file_directory_conflict_is_restored_on_failure(self):
        asset = self.root / 'src/assets/example'
        asset.mkdir()
        (asset / 'old.txt').write_text('old asset', encoding='utf-8')
        build(self.root)
        previous = self.snapshot()
        (asset / 'old.txt').unlink()
        asset.rmdir()
        asset.write_text('replacement file', encoding='utf-8')
        with patch.object(outputs, 'copy_atomic', side_effect=OSError('simulated conflict failure')):
            with self.assertRaisesRegex(OSError, 'simulated conflict failure'):
                build(self.root)
        self.assertEqual(self.snapshot(), previous)
