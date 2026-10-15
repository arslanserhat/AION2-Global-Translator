# Translation workflow

This project creates a native localization file from a user's own AION 2 installation. The public repository is a tool and format implementation, not a redistribution of the game's language data.

## From installed files to a local patch

1. **Identify the source.** Record the installed Steam build and verify the expected English localization package. The development reference is build **25926599**.
2. **Extract locally.** The Windows release ZIP includes [repak 0.2.3](https://github.com/trumank/repak/releases/tag/v0.2.3); source users obtain it separately and place it at `tools/repak.exe` or set `REPAK_PATH`. The application uses it to extract the required source localization and key manifest from your installation. **Details… → Export English source…** exports your local table for map preparation. Keep extracted game files outside the public repository.
3. **Check the codec.** Decoding and rewriting an unchanged source must preserve the source container. An edited Unicode sample must encode and decode to the same values before a real translation is installed.
4. **Choose the target and translate values.** Select **Target language / Hedef dil** on the main screen and open **Translation settings… / Çeviri ayarları…**. Keep entry identifiers fixed. Import a complete local JSON map, or submit text to the LibreTranslate-compatible endpoint you configured using an English-to-target pair it actually offers.
5. **Validate and review.** Check formatting, unresolved values, terminology, numerical meaning, and quest clues. Produce a local candidate; generation alone should not be treated as in-game verification.
6. **Back up and install.** Fully close the game. Verify the build and original files, preserve a restorable copy, then select the target and use **Apply translation / Çeviriyi uygula**. **Details… → Install prepared language…** also accepts an explicit stage folder. If no matching stage is ready, Apply opens settings rather than installing a different language.
7. **Check inside the game.** Keep the selected game text language on English. Verify actual rendered characters, menus, tooltips, and representative dialogue before broader use.

The format implementation draws on the AION 2 readers and encryption/container logic in [CUE4Parse](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2), licensed under [Apache-2.0](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE). Its game-specific behavior is version-dependent.

Every target is built from the verified original English table. An installed translation is not used as the source for another language. Selecting English on the main screen restores the original English files through the verified restoration path.

## Translation provider

Enter an endpoint that you are authorized to use. Supply your own API key only when that instance requires it. The [`POST /translate` API](https://docs.libretranslate.com/api/operations/translate/) accepts source and target language codes; provider errors and rate limits must be handled as incomplete work, not silently counted as translated text.

Source text is transmitted to the endpoint during online translation. A self-hosted endpoint keeps that processing under your control, subject to your deployment. See the [LibreTranslate installation documentation](https://docs.libretranslate.com/guides/installation/). This application does not include a hosted translation subscription or a universal provider credential.

Do not put API keys, complete provider responses, source tables, or translation caches into an issue or commit.

The current protection profile preserves technical abbreviations such as HP and MP as well as formatting literals. Provider caching uses a revised profile namespace and validates cached answers against current rules; earlier cache rows are retained without being reused for the new protection profile.

## Formatting contract

A translation must preserve the original key and the protected structure of its value:

- Brace placeholders, including repeated or nested placeholders.
- Rich-text tag literals and their order.
- Non-positional printf argument order and exact format specifiers.
- Numeric literals, signs, percentages, and nondecimal numeric symbols such as circled list labels.
- Required line breaks, control characters, escape sequences, and encoded entities.

Do not delete a failed placeholder, remove a tag, or round a number to make a validator pass. Keep the English value unresolved until a valid repair is available. Validation protects structure; it cannot prove that a skill's effect, item requirement, or direction has been translated correctly.

Repeated identical English values may be reused to reduce provider calls. They can still have different meanings in different contexts. Review short ambiguous labels and use entry-specific corrections where needed.

## Language-specific wording

All targets share the structural and technical-abbreviation protections. A bounded post-edit profile additionally supplies exact short UI action labels and selected terms for `de`, `fr`, `es`, `it`, `pt`, `ru`, `ja`, `ko`, Simplified Chinese `zh`, and `ar`. It acts only in matched field contexts, such as a weapon label or skill name; each target keeps its own UI grammar. It is not a semantic repair pass over every sentence. Other targets retain provider/imported wording.

Turkish uses a separate context profile, and its selected-title display option applies only to Turkish. Neither profile establishes font support. See [review coverage by language](LANGUAGES.md#review-and-corrections-by-language).

## Human review

Give priority to:

1. Main menus, inventory actions, confirmation and cancellation buttons.
2. Skill amounts, durations, costs, conditions, and equipment requirements.
3. Quest targets, directions, names, and item references.
4. Passwords, riddles, acrostics, and highlighted clues. Preserve a literal input answer when the game expects one.
5. Long journal text and passages split around formatting tags.

The Turkish development work combines machine translation with selected edits and reviewed rules. It is not a fully human-reviewed localization. Report structural validation, changed text, unresolved values, and playtesting separately; an unchanged proper name and a failed sentence are different cases.

Commands on buttons and quest objectives use second-person singular imperatives: `Konuş`, `Kullan`, `Topla`, `Üret`, `Tamamla`, `Git`, `Al`, `Teslim et`, `İncele`. Names and titles can remain nouns; skill descriptions keep descriptive grammar. Context rules distinguish weapon `Staff`, ability `Cast`, precision `Snipe`, and the item flag `(Bound)` from their unrelated everyday meanings. See [quality and terminology choices](QUALITY.md).

## Custom maps

The offline path imports a user-supplied JSON translation map. Export the source through **Details… → Export English source…** first; the local export is stored under `private-data/source/25926599/entries.en.json`. Work on a separate copy. Select the target language and open **Translation settings… → Offline JSON** to import it. The import must be a flat object whose complete key set matches the extracted table and whose values contain translated text. The following illustrates the structure using two synthetic keys:

```json
{
  "Example_UI_Confirm": "Onayla",
  "Example_UI_Cancel": "İptal"
}
```

These are synthetic example keys, not a usable game map. A real input must include the entire source key set, preserve protected formatting, and match the source build. Keep complete real maps local; use minimal synthetic fixtures for public bug reports. An offline map can be imported without sending its text to a translation provider. Creation produces a local stage; select its target and use **Apply translation**, or choose it through **Details… → Install prepared language…**, after closing the game.

For a wording correction in any language, change only the affected values in a copy of its complete target map, then import that corrected map and rebuild. Do not rename keys or edit the DAT manually. The release has no in-app per-entry editor; rebuilding from a corrected JSON is the manual correction path. Structural validation still applies, and matched short-label context rules run during the build. Review the resulting text as well as the input.

Each successful build retains the editable canonical map at `private-data/stages/<target>/entries.translated.json`, before any Turkish title-character folding. Use **Details… → Export translation…** for the selected target to save a working copy, then edit that copy and use the offline import. The service equivalent is `export_translation(target_language, destination)`. These complete game-derived maps remain private and are excluded from the public ZIP.

An older Turkish pack may contain localized abbreviation labels such as `Can` for `HP`. During an offline Turkish rebuild, an untouched cell can be carried forward only from an existing same-language pack whose build, source identity, DAT hash, complete keys, and native round trip are verified. Its full text must match that reference, allowing only the established Turkish title-display equivalence; original tags, numbers, macros, and controls remain protected. This compatibility path does not approve the cell's meaning. New or edited cells must retain the current strict abbreviation literals, and provider results always use strict validation. The stage metadata records `carry_forward_legacy_count`, `carry_forward_legacy_keys`, and the reference hashes in `carry_forward_legacy_reference`.

Unchanged language-bearing values are written to `private-data/stages/<target>/unchanged-review.json` and block stage creation until you explicitly confirm their review in the GUI (`review_unchanged=True` in a service call). Confirm only deliberate unchanged values such as proper names; the review does not prove complete translation coverage or semantic accuracy.

## Turkish title compatibility

v0.1.1 addresses missing Turkish glyphs in the game's English display fonts through selected text values. With **font-compatible titles** enabled, selected name/title fields use ASCII counterparts for `Ç ç Ğ ğ İ ı Ö ö Ş ş Ü ü`; for example, `Ödüller` displays as `Oduller`. The option defaults to enabled for Turkish builds (`font_compatible_titles`). It preserves source maps, protected formatting, and Turkish accents in body text. It does not change fonts or game font packages.

This trades the correct orthography of selected titles for readable display. Turning the option off keeps their accented spelling but does not give the original heading fonts missing glyphs. The profile also corrects 31 related skill-name records, including the mistaken bird translation of **Snipe**, which becomes `Keskin Atis` in the compatible title form.

For an existing compatible Turkish installation, select Turkish, fully close the game, and use **Fix headings (Turkish) / Başlıkları düzelt (Türkçe)** (`repair_turkish_headings` in the service). It applies the available bounded context-term and heading-display repairs. The button is disabled for other targets; it is not their grammar or font repair. Keep the original backup and restart the game manually after repair. Verify the affected heading and a body description in-game; serialization and font-map checks do not establish that the repaired screen looks correct.

For a separately prepared compatible replacement stage, use **Apply translation** for its target or **Install prepared language…** to choose it explicitly. The app can replace its own verified installation on the same source build while keeping the original backup. Restore a patch from another tool with that tool first. The public download contains the repair code, not a full game-derived translation or a replacement font.

## Updating and restoring

A generated DAT, source package, and backup must refer to the same verified game build. Close the game before applying or switching a translation. The app can replace its own verified compatible pack without discarding the original backup. Restore original files before updating the game or removing the tool's patch. Do not reuse a stale backup after Steam changes the source build.

If a build or hash check fails, preserve the diagnostic information and prepare a new source from the current official installation. Re-running an old installer is not a compatibility update. If restoration is blocked because official files changed, use the launcher's file-verification process rather than forcing an old backup over them.

## Public repository boundary

Publish code, attribution, documentation, and synthetic tests. Keep game DATs, key manifests, extracted assets, full English or translated tables, backups, generated bundles, credentials, and personal paths private and local. A public release must be checked for these files independently of whether its code tests pass.
