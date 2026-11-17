"""Publish a complete generated build directory and validate its inventory."""
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
from tempfile import NamedTemporaryFile, mkdtemp

from .config import load_json

MANIFEST = '.site-build.json'


def checksum(path):
    return sha256(path.read_bytes()).hexdigest()


def files_in(directory):
    return {path.relative_to(directory).as_posix(): path for path in directory.rglob('*') if path.is_file() and path != directory / MANIFEST}


def write_manifest(directory, pages):
    files = {name: checksum(path) for name, path in sorted(files_in(directory).items())}
    data = {'version': 1, 'pages': sorted(pages), 'files': files}
    (directory / MANIFEST).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def ensure_local_directory(path, root):
    """Never recursively remove a source directory, symlink, or junction."""
    if path.parent.resolve() != root or not (path.name == 'build' or path.name.startswith('.build-')):
        raise ValueError(f'Not a generated build directory: {path}')
    if not path.exists():
        if path.is_symlink():
            raise ValueError(f'Build directory must not be a symlink: {path}')
        return
    if not path.is_dir():
        raise ValueError(f'Build output must be a directory: {path}')
    for current, directories, files in os.walk(path, followlinks=False):
        for entry in [Path(current), *(Path(current) / name for name in directories + files)]:
            attributes = getattr(entry.lstat(), 'st_file_attributes', 0)
            if entry.is_symlink() or attributes & 0x400 or not entry.resolve().is_relative_to(root):
                raise ValueError(f'Build output must not contain symlinks or junctions: {entry}')


def remove_temporary(directory, root):
    ensure_local_directory(directory, root)
    if directory.exists():
        shutil.rmtree(directory)


def publish_directory(root, staging):
    target = root / 'build'
    ensure_local_directory(staging, root)
    ensure_local_directory(target, root)
    if target.exists() and any(target.iterdir()):
        marker = target / MANIFEST
        data = load_json(marker) if marker.is_file() else None
        if not isinstance(data, dict) or data.get('version') != 1:
            raise ValueError('Existing build/ is not recognized as generated output; move it aside before building.')
    if not target.exists():
        staging.rename(target)
        return
    # Keep build/ itself stable: Windows preview servers may hold it as their cwd.
    backup = Path(mkdtemp(prefix='.build-backup-', dir=root))
    retain_backup = False
    try:
        # Finish the backup before changing any published file.
        shutil.copytree(target, backup, dirs_exist_ok=True)
        try:
            synchronize_files(staging, target, copy_atomic)
        except OSError as error:
            try:
                # Moving backup files needs no extra disk space if a write failed.
                synchronize_files(backup, target, os.replace)
            except OSError:
                retain_backup = True
                raise RuntimeError(f'Build update and rollback failed. Previous files are saved in {backup}') from error
            raise
    finally:
        if not retain_backup:
            remove_temporary(backup, root)


def remove_empty_directories(target):
    for directory in sorted((path for path in target.rglob('*') if path.is_dir()), key=lambda path: len(path.parts), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()


def synchronize_files(source, target, replace_file):
    """Use the same file plan for publication and rollback, leaving build/ open."""
    current = files_in(target)
    incoming = files_in(source)
    # Only file/directory conflicts must be removed before replacement.
    blockers = {
        old for old in current
        if any(new.startswith(old + '/') or old.startswith(new + '/') for new in incoming)
    }
    for name in blockers:
        current[name].unlink()
    remove_empty_directories(target)
    for name, incoming_path in incoming.items():
        destination = target / name
        if destination.is_file() and checksum(incoming_path) == checksum(destination):
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        replace_file(incoming_path, destination)
    # Keep obsolete pages available until all new files have been written.
    for name in current.keys() - incoming.keys() - blockers:
        current[name].unlink()
    remove_empty_directories(target)
    manifest = source / MANIFEST
    if not (target / MANIFEST).is_file() or checksum(manifest) != checksum(target / MANIFEST):
        replace_file(manifest, target / MANIFEST)


def copy_atomic(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
            temporary = stream.name
        shutil.copyfile(source, temporary)
        os.replace(temporary, destination)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def validate_outputs(directory, expected):
    manifest = directory / MANIFEST
    if not manifest.is_file():
        raise ValueError('Generated build is missing; run python scripts/build.py.')
    data = load_json(manifest)
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('files'), dict):
        raise ValueError('Invalid generated build inventory; rebuild the site.')
    if set(data.get('pages', [])) != set(expected):
        raise ValueError('Generated-page inventory differs from navigation; rebuild the site.')
    actual = files_in(directory)
    if set(actual) != set(data['files']):
        raise ValueError('Build contains missing or unexpected files; rebuild the site.')
    for name, path in actual.items():
        if checksum(path) != data['files'][name]:
            raise ValueError(f'Generated file changed; rebuild the site: {name}')
