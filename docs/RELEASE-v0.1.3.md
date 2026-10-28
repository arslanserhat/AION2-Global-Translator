# v0.1.3 — Incremental updates for Steam build 26262663

The current English source contains **153,297 records**, compared with 153,185 in build 26077854: **116 added keys, 265 changed English values, and 4 removed keys**. A local Turkish review supplies corrections for all **381 new/changed records**; 152,916 exact key-and-English pairs can retain their previous wording.

This is a native text-patch update. It does not add voice translation, image-text translation, or live-chat coverage.

## Changes

- **Apply translation** can rebuild an older local pack against current original English before installing it.
- Migration carries a translation only when **both key and source English are identical**. Reused English under another key, number-only edits, and other source changes require fresh translations; no fuzzy or numeric-substitution migration is used.
- Future source builds are probed from current locale/startup archives and file fingerprints, with verified caches, complete decoding, and native round trips. Build numbers and entry counts are no longer the sole fixed compatibility gate.
- Each prepared pack retains its English `entries.source.json` baseline, canonical target map, and manifest/source/DAT hashes for subsequent migration.
- A configured LibreTranslate-compatible URL is checked for the target pair and receives only pending new/changed source text. Provider API keys are not persisted; later checks use `AION2_TRANSLATION_API_KEY` from the app process environment when required.
- Without a usable provider, the app writes `private-data/updates/<build>/<language>/<source-DAT-SHA256>/pending.json` for review. A complete `corrections.json` in that source-specific directory resolves the required keys. A same-build source-content change receives a separate review directory. Incomplete or invalid work preserves the previous prepared pack and does not install a partial table.
- **Güncellemelerden sonra otomatik onar / Automatically repair after updates** defaults to enabled after the first successful install. Checks operate while the app is running and wait for an open game to close. No Windows startup task or service is installed. Restoring originals disables repair.
- Existing backup ownership, scoped installation, closed-game checks, and Turkish heading compatibility remain part of the workflow. Old backups are not written over newly updated official source files.

## Validation and limits

Final local automated result: **152 tests passed**. Synthetic/unit checks are separate from private full-table decoding, migration coverage, and actual game rendering.

The 381 local correction records passed protected-format, numeric-counter, newline, and Unicode checks. Their wording was reviewed for this update, including removed faction filters, changed skill percentages/macros, Battle Pass item descriptions, and new UI/cosmetics. This does not mean every one of the 153,297 records was individually human-reviewed.

A compatible serialized file and a successful provider request do not establish complete semantic or in-game visual correctness. Source format, encryption, or container changes may still require a translator update. Other target languages remain conditional on the provider, language pair, and renderer.

## Distribution

The public ZIP contains applications and tooling only. It excludes game DATs, key manifests, complete source/translated maps, the local Turkish correction table, generated packs, private backups, and provider credentials.

Keep your existing `private-data` when replacing the app. It contains the source/translation baseline needed for future migration. See the [translation workflow](TRANSLATION.md) for provider configuration, pending reviews, offline maps, and restoration.
