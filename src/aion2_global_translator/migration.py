"""Incremental translation migration. Only identical key AND source carry over.

Changed English, reused text under a different key, and number-only edits all
require a new translation. No fuzzy matching or inferred numeric replacements.
"""
from __future__ import annotations
from .protection import has_linguistic_content, validate


def plan_migration(previous_source, previous_values, current_source):
    if set(previous_source) != set(previous_values):
        raise ValueError("Previous translation has a different source key set")
    carried, pending, unchanged_literals = {}, {}, {}
    for key, source in current_source.items():
        if key in previous_source and previous_source[key] == source:
            carried[key] = previous_values[key]
        elif not has_linguistic_content(source):
            validate(source, source)
            unchanged_literals[key] = source
        else:
            pending[key] = {"source": source, "previous_source": previous_source.get(key),
                            "previous_translation": previous_values.get(key)}
    return dict(carried=carried, pending=pending, literals=unchanged_literals,
                removed=sorted(set(previous_source) - set(current_source)))


def finish_migration(plan, corrections):
    if set(corrections) != set(plan["pending"]):
        raise ValueError("Update translations must cover exactly the new and changed text keys")
    for key, value in corrections.items():
        if not isinstance(value, str):
            raise ValueError("Updated translations must be strings")
        validate(plan["pending"][key]["source"], value)
    return dict(plan["carried"], **plan["literals"], **corrections)
