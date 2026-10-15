# Translation workflow

This project creates a native localization file from a user's own AION 2 installation. The public repository is a tool and format implementation, not a redistribution of the game's language data.

## From installed files to a local patch

1. **Identify the source.** Record the installed Steam build and verify the expected English localization package. The development reference is build **25926599**.
2. **Extract locally.** The Windows release ZIP includes [repak 0.2.3](https://github.com/trumank/repak/releases/tag/v0.2.3); source users obtain it separately and place it at `tools/repak.exe` or set `REPAK_PATH`. The application uses it to extract the required source localization and key manifest from your installation. The offline translation dialog's **Export English source…** action exports your local table for map preparation. Keep extracted game files outside the public repository.
3. **Check the codec.** Decoding and rewriting an unchanged source must preserve the source container. An edited Unicode sample must encode and decode to the same values before a real translation is installed.
4. **Translate values.** Keep entry identifiers fixed. Import a complete local JSON map, or submit text to the LibreTranslate-compatible endpoint you configured using an English-to-target pair it actually offers.
5. **Validate and review.** Check formatting, unresolved values, terminology, numerical meaning, and quest clues. Produce a local candidate; generation alone should not be treated as in-game verification.
6. **Back up and install.** Fully close the game. Verify the build and original files, preserve a restorable copy, then install the candidate through the application's native-file workflow.
7. **Check inside the game.** Keep the selected game text language on English. Verify actual rendered characters, menus, tooltips, and representative dialogue before broader use.

The format implementation draws on the AION 2 readers and encryption/container logic in [CUE4Parse](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2), licensed under [Apache-2.0](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE). Its game-specific behavior is version-dependent.

## Translation provider

Enter an endpoint that you are authorized to use. Supply your own API key only when that instance requires it. The [`POST /translate` API](https://docs.libretranslate.com/api/operations/translate/) accepts source and target language codes; provider errors and rate limits must be handled as incomplete work, not silently counted as translated text.

Source text is transmitted to the endpoint during online translation. A self-hosted endpoint keeps that processing under your control, subject to your deployment. See the [LibreTranslate installation documentation](https://docs.libretranslate.com/guides/installation/). This application does not include a hosted translation subscription or a universal provider credential.

Do not put API keys, complete provider responses, source tables, or translation caches into an issue or commit.

## Formatting contract

A translation must preserve the original key and the protected structure of its value:

- Brace placeholders, including repeated or nested placeholders.
- Rich-text tag literals and their order.
- Non-positional printf argument order and exact format specifiers.
- Numeric literals, signs, percentages, and nondecimal numeric symbols such as circled list labels.
- Required line breaks, control characters, escape sequences, and encoded entities.

Do not delete a failed placeholder, remove a tag, or round a number to make a validator pass. Keep the English value unresolved until a valid repair is available. Validation protects structure; it cannot prove that a skill's effect, item requirement, or direction has been translated correctly.

Repeated identical English values may be reused to reduce provider calls. They can still have different meanings in different contexts. Review short ambiguous labels and use entry-specific corrections where needed.

## Human review

Give priority to:

1. Main menus, inventory actions, confirmation and cancellation buttons.
2. Skill amounts, durations, costs, conditions, and equipment requirements.
3. Quest targets, directions, names, and item references.
4. Passwords, riddles, acrostics, and highlighted clues. Preserve a literal input answer when the game expects one.
5. Long journal text and passages split around formatting tags.

The Turkish development work combines machine translation with selected human corrections. It is not a fully human-reviewed localization. Report structural validation, changed text, unresolved values, and playtesting separately; an unchanged proper name and a failed sentence are different cases.

## Custom maps

The offline path imports a user-supplied JSON translation map. Export the source through the offline translation dialog first; the local export is stored under `private-data/source/25926599/entries.en.json`. Work on a separate copy. The import must be a flat object whose complete key set matches the extracted table and whose values contain translated text. The following illustrates the structure using two synthetic keys:

```json
{
  "Example_UI_Confirm": "Onayla",
  "Example_UI_Cancel": "İptal"
}
```

These are synthetic example keys, not a usable game map. A real input must include the entire source key set, preserve protected formatting, and match the source build. Keep complete real maps local; use minimal synthetic fixtures for public bug reports. An offline map can be imported without sending its text to a translation provider. Creation produces a local stage; use **Install prepared language…** to install that stage after closing the game.

Unchanged language-bearing values are written to `private-data/stages/<target>/unchanged-review.json` and block stage creation until you explicitly confirm their review in the GUI (`review_unchanged=True` in a service call). Confirm only deliberate unchanged values such as proper names; the review does not prove complete translation coverage or semantic accuracy.

## Updating and restoring

A generated DAT, source package, and backup must refer to the same verified game build. Close the game and restore original files before switching patches. Do not reuse a stale backup after Steam changes the source build.

If a build or hash check fails, preserve the diagnostic information and prepare a new source from the current official installation. Re-running an old installer is not a compatibility update. If restoration is blocked because official files changed, use the launcher's file-verification process rather than forcing an old backup over them.

## Public repository boundary

Publish code, attribution, documentation, and synthetic tests. Keep game DATs, key manifests, extracted assets, full English or translated tables, backups, generated bundles, credentials, and personal paths private and local. A public release must be checked for these files independently of whether its code tests pass.
