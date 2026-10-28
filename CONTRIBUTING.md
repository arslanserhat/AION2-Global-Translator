# Contributing

Contributions should make native translation, update handling, restoration, and language behavior easier to verify. Keep a change focused on a concrete failure or user need.

## Before opening an issue

Read the [workflow](docs/TRANSLATION.md) and [language notes](docs/LANGUAGES.md). Include the app revision, Windows version, Steam build, source locale, target language, and a minimal reproduction.

For update issues, distinguish source discovery, migration planning, provider translation, pending review, installation, restoration, and rendering. Give expected and actual behavior. Share redacted errors and relevant hashes/counts; do not attach a complete pending file or game table.

A successful launch, a provider language listing, structural validation, and an actual in-game display check are separate evidence.

## Keep game data and secrets private

Do not submit game DATs, key manifests, extracted assets, game backups, complete source/translated maps, generated packs, full update reviews, translation caches, API keys, account details, or personal paths.

Use synthetic strings and temporary fixture directories. Public contributions can include code, terminology guidance, and minimal rights-compatible examples. Complete game-derived maps stay in ignored `private-data` and out of release archives.

Provider configuration may retain a user-selected URL, never the API key. Later checks read `AION2_TRANSLATION_API_KEY` from the process environment. Do not add borrowed credentials, embedded public frontend keys, subscription bypasses, or silent uploads.

## Code and update changes

1. Describe the trigger, resulting behavior, and validation.
2. Use synthetic fixtures and mocked providers; tests must not need a game, account, or live endpoint.
3. For codec changes, cover unchanged byte serialization and edited Unicode round trips.
4. For source discovery, cover archive/startup fingerprints, complete verified caches, changed inputs, extraction failure, and source-format refusal.
5. For migration, require identical **key and English value** for carry-forward. Test number-only changes, reused English under another key, removed keys, invalid corrections, incomplete providers, and preservation of the previous pack.
6. For installation, cover backup ownership, concurrent edits, partial-write rollback, stale-source refusal, scoped paths, and the closed-game requirement.
7. For automatic checks, cover waiting while the game runs and disabling repair when the user restores original files. Do not introduce a Windows startup task or service as an incidental change.
8. For translations, protect macros, tag order, controls, numerals, technical abbreviations, and non-positional printf argument order. A format pass is not a semantic approval.

Fresh builds may be investigated through verified local source fingerprints. Do not remove format or source-identity checks merely to accept a new build number.

## Tests

The v0.1.3 source check passed **152 tests locally**. Run the suite from a source installation:

```powershell
python -m unittest discover -s tests -v
```

These tests use synthetic fixtures and mocked services. They do not prove the appearance or meaning of every game string. Full private-table checks and any real in-game observations must be reported separately.

[docs/check-workflow.yml](docs/check-workflow.yml) is an optional GitHub Actions example. The README badge reports the stated local run; it is not an active CI result.

## Language contributions

State the provider, target code, review scope, font observations, and gameplay checks separately. Identical words can need different translations across contexts. Review skill mechanics, quest directions, passwords, riddles, and acrostics manually.

Turkish button/objective commands use singular imperatives such as `Konuş`, `Kullan`, `Topla`, and `Tamamla`. Names remain names and descriptive skill text remains descriptive. Do not apply Turkish grammar rules to another language.

## Attribution and releases

The codec adapts [CUE4Parse](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2). Preserve applicable copyright and [Apache-2.0](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE) notices.

[repak](https://github.com/trumank/repak) has MIT/Apache-2.0 licensing. Source users obtain it separately; the Windows ZIP includes version 0.2.3 and upstream notices in `licenses/repak/`.

Before publishing, inspect the actual archive for game data, credentials, generated reviews, and local paths. State the exact app revision, tested source build, automated-check scope, and whether game rendering was checked. Do not publish placeholder test counts or imply publisher approval.
