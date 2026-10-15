# Contributing

Contributions that improve format correctness, restoration, language handling, and clear reporting are welcome. Keep changes focused and make their behavior reviewable.

## Before opening an issue

Check [language compatibility](docs/LANGUAGES.md) and the [translation workflow](docs/TRANSLATION.md). Include:

- App revision and Windows version.
- Steam build, source locale, and target language code.
- Whether the issue occurs during extraction, translation, validation, installation, restoration, or in-game rendering.
- A small reproduction, expected behavior, and actual behavior.
- For provider issues, its software/model information if available and a redacted error message.

Separate a launch report from visual confirmation and actual playtesting. Do not describe a target language as supported solely because it appears in a provider's language list.

## Keep game data and secrets out

Do not submit game DATs, key manifests, extracted assets, game backups, full source or translated string tables, generated language bundles, translation caches, API keys, account details, or personal filesystem paths.

Use synthetic strings and temporary fixture directories in tests. For a formatting failure, a made-up sentence with the same placeholder/tag pattern is usually enough. If a short real text example is necessary, share only what you have the right to publish; do not attach a complete table to make debugging easier.

## Code changes

1. Describe the concrete behavior being changed and why.
2. Add meaningful tests for the affected failure mode. Tests must not require a real game installation, network provider, or account.
3. For codec changes, check unchanged serialization and edited Unicode round trips.
4. For installer changes, exercise failed writes, exact backup recovery, changed-file refusal, build mismatch, and paths outside the intended game scope using fixtures.
5. For translation changes, preserve placeholders, tag order, controls, numerals, and non-positional printf argument order. Use a mocked provider.
6. Update documentation when compatibility, data handling, or user-visible steps change.

Keep provider access explicit and configurable. Do not add embedded public frontend keys, borrowed credentials, subscription bypasses, or silent external uploads.

## Tests

The v0.1.1 source check passed **96 tests locally**. The suite uses synthetic fixtures and mocked services. Run it from a source installation with:

```powershell
python -m unittest discover -s tests -v
```

The tests do not establish in-game visual compatibility. The Windows GUI was also opened; Turkish/English layout and busy-state controls were checked separately. [docs/check-workflow.yml](docs/check-workflow.yml) provides an optional GitHub Actions workflow example; the test badge reports the local result rather than an active CI run.

## Language contributions

Report the provider and target code separately from font and in-game verification. Review terminology in context; identical English words can require different translations across screens. Passwords, riddles, and letter puzzles need human review.

Contribute tooling, terminology guidance, and synthetic examples publicly. Keep complete game-derived translation maps out of pull requests until a rights-compatible distribution policy has been established. The current project does not distribute those maps.

## Attribution and releases

The AION 2 codec is adapted from [CUE4Parse](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2). Preserve applicable attribution and [Apache-2.0](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE) notices, and identify modified/adapted files. Keep third-party notices with release artifacts.

The external [repak](https://github.com/trumank/repak) tool has its own MIT/Apache-2.0 licensing. Source users obtain it separately; the Windows release ZIP includes version 0.2.3 with its upstream license texts in `licenses/repak/`. Preserve those notices when rebuilding or redistributing the archive.

Before a public release, inspect the actual archive contents for excluded game data, credentials, and local paths. State the exact app revision, tested game build, known limitations, and whether in-game appearance was checked. Do not publish fabricated success badges or imply publisher approval.
