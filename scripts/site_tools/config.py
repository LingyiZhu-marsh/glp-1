"""Shared JSON loading with errors that identify the source file."""
import json


def unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=unique_keys)
    except (ValueError, OSError) as error:
        raise ValueError(f'{path}: {error}') from error
