# Translation workflow

The tool builds a native localization file from a user's own English AION 2 installation. The public project distributes application code and format tooling, not the game's complete language data.

The current verified reference is **Steam build 26262663 / 153,297 records**. Future build numbers are not accepted on their number alone: current source archives, fingerprints, decoding, and native round trips determine whether the format remains usable.

## From installed source to a pack

1. Select the Steam AION 2 folder. Keep the game's text language on English.
2. The app reads the original locale and startup archives locally. The Windows ZIP supplies [repak 0.2.3](https://github.com/trumank/repak/releases/tag/v0.2.3); source users place it at `tools/repak.exe` or set `REPAK_PATH`.
3. Source discovery records archive fingerprints and verifies the extracted DAT, key manifest, namespace, entries, and unchanged native round trip. Cached sources are reused only when their identity and complete contents verify.
4. Choose **Target language / Hedef dil** and **Translation settings… / Çeviri ayarları…**. Import a complete local map or use a configured LibreTranslate-compatible endpoint.
5. Validate and review the result. Generation creates a local stage; a separate installation step applies it.
6. Fully close AION 2, then use **Apply translation / Çeviriyi uygula**, or **Details… → Install prepared language…** for an explicit stage.
7. Restart the game normally and check actual menus, glyphs, mechanics, and representative dialogue.

The codec draws on [CUE4Parse's AION 2 format implementation](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2), licensed under [Apache-2.0](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE). A changed container, encryption scheme, or serialization format can still require a tool update.

All target languages use the verified original English source. Translation through an already translated language is not part of the workflow.

## Incremental game updates

When the selected prepared pack belongs to an older source, **Apply translation** plans and builds a replacement against the current source before installation.

| Source comparison | Action |
| --- | --- |
| Same key and identical English value | Carry the verified previous translation |
| Existing key with changed English, including only a number change | Require a fresh translation |
| New key, even if its English exists elsewhere | Require a fresh translation |
| Removed key | Omit it from the new table |
| New/changed value containing only protected nonlinguistic literals | Preserve the literal value after validation |

There is no fuzzy matching, cross-key translation reuse, or inferred replacement of numbers in old Turkish text. Changes to skill costs or durations must follow the new source rather than an old sentence's appearance.

Each new stage retains `entries.source.json` as its English baseline, `entries.translated.json` as the editable canonical target map, and manifest/source/DAT hashes in its metadata. That lets the next comparison establish both source identity and translation ownership. Older packs without a verifiable English baseline cannot be migrated merely by trusting their target map.

Previous prepared packs are archived privately when a complete replacement is committed. Incomplete translation, invalid formatting, or changed source data stops the operation. The tool does not install a partially translated table or overwrite a new official source with an older backup.

### Automatic checks while the app is open

After the first successful install, **Automatically repair after updates / Güncellemelerden sonra otomatik onar** defaults to enabled. The app checks while it is running. If AION 2 is open, it waits until the game closes before attempting changes. It does not register a Windows startup task or install a service.

**Restore original / Orijinale dön** also disables automatic repair, so the app does not immediately reinstall a translation the user removed. The app must be running for checks; closing the app stops this activity.

Automatic migration preserves existing wording only for exact source pairs. It does not make provider output semantically perfect, install missing language models, or add missing font glyphs.

### Pending review without a provider

If new language-bearing text needs translation and no usable provider is configured, review files are placed under:

```text
private-data/updates/<build>/<language>/<source-DAT-SHA256>/pending.json
private-data/updates/<build>/<language>/<source-DAT-SHA256>/corrections.json
```

The source-DAT SHA256 scopes each review to the exact current English content. A source change within the same Steam build creates a separate review directory; corrections from an older source are not reused. The app writes `pending.json`. It lists each required key's new `source` with its `previous_source` and `previous_translation` when available. Create `corrections.json` as a flat map covering exactly the pending keys. These synthetic examples show the two shapes:

```json
{
  "Example_New_Action": {
    "source": "Open",
    "previous_source": null,
    "previous_translation": null
  }
}
```

```json
{
  "Example_New_Action": "Aç"
}
```

Translate from the new English value; use old wording as context. Preserve protected literals and any server-input passwords. Apply the selected language again after the corrections are complete. The previous prepared pack remains available if review or validation fails; this does not imply that an old pack works on the updated client.

Never publish a full pending review or corrections map: they contain game-derived text. Use synthetic examples for issues.

## Translation provider

Use a LibreTranslate-compatible URL you are authorized to access. Language discovery must confirm that the instance offers English and the selected target pair. Its [translate API](https://docs.libretranslate.com/api/operations/translate/) receives source and target codes.

During an incremental update, only pending new/changed source text is sent. Source values are protected before transmission and validated after restoration. Failed requests, invalid placeholders, and rate limits remain failures; they are not silently accepted as translated output.

The app can retain the selected provider type and URL for later checks. **It does not save the API key.** If the provider requires a key for a later app session or automatic check, supply `AION2_TRANSLATION_API_KEY` in the app process's environment. Entering a key for one build does not set the environment for later sessions: set it in the environment used to launch the app. Do not commit credentials, complete responses, caches, or language tables.

A hosted provider can charge fees or impose limits. A [self-hosted LibreTranslate server](https://docs.libretranslate.com/guides/installation/) needs the appropriate models. A server listing a language does not establish that the game's fonts render it.

## Formatting contract

Keep entry identifiers fixed and preserve:

- Brace placeholders, including repeated/nested forms.
- Rich-text tag literals and their order.
- Non-positional printf argument order and exact specifiers.
- Numeric literals, signs, percentages, and symbols such as circled list labels.
- Required newlines, control characters, escape sequences, and encoded entities.
- Technical abbreviations such as HP and MP.

Do not remove a tag, change a numeral, or delete a placeholder to pass a validator. Structural validation cannot prove a skill's effect, a direction, an item requirement, or a puzzle clue is correct.

Human review should prioritize menu actions; skill amounts, durations and costs; quest targets and places; passwords and acrostics; and long journal passages split around tags. Turkish commands use singular imperatives: `Konuş`, `Kullan`, `Topla`, `Üret`, `Tamamla`, `Git`, `Al`, `Teslim et`, `İncele`. Names/titles can remain nouns; skill effects use descriptive grammar.

All languages share formatting protection. Ten additional context profiles offer a bounded set of short UI labels and terms for `de`, `fr`, `es`, `it`, `pt`, `ru`, `ja`, `ko`, `zh`, and `ar`. They do not review every sentence. Turkish terminology and display rules are separate; see [language-specific review](LANGUAGES.md#review-and-corrections-by-language).

## Custom maps

For a complete offline map, use **Details… → Export English source…** and work on a separate copy. The export is stored locally under `private-data/source/<build>/entries.en.json`. The import must be a flat string-to-string JSON object with the complete current source key set:

```json
{
  "Example_UI_Confirm": "Onayla",
  "Example_UI_Cancel": "İptal"
}
```

These are synthetic examples, not a usable game map. Keep complete real maps local. **Translation settings… → Offline JSON** builds the stage without sending the map to a provider.

For an existing target, use **Details… → Export translation…**, edit only values, and rebuild through the offline path. Canonical spelling is saved in `private-data/stages/<language>/entries.translated.json` before Turkish display folding. There is no in-app per-entry editor.

An older Turkish pack can contain localized abbreviation labels such as `Can` for `HP`. Untouched cells can be retained only against a verified same-language pack, matching source/key identity, complete map, native DAT, and allowed title-display equivalence. This compatibility path does not approve their meaning. New/edited cells and provider results retain strict abbreviation protection.

Unchanged language-bearing values in a complete offline map are written to `unchanged-review.json` and block stage creation until their review is explicitly confirmed (`review_unchanged=True` in the service). Confirm intentional names or labels only; this is not a complete semantic certificate.

## Turkish title compatibility

The Turkish display profile addresses limited English heading fonts through selected name/title values. With `font_compatible_titles` enabled, `Ç ç Ğ ğ İ ı Ö ö Ş ş Ü ü â Â` receive readable basic-Latin counterparts in those fields, for example `Ödüller → Oduller`. Regular body text retains Turkish letters. The canonical map and formatting literals are preserved.

This trades selected-title orthography for readability; it does not install replacement fonts or repair every widget. Turning it off preserves accented titles without adding missing glyphs to the game's fonts.

For a verified Turkish pack, **Fix headings (Turkish) / Başlıkları düzelt (Türkçe)** applies the available bounded terminology/display repair. The control is disabled for other targets. Keep the original backup and restart the game normally after installation, then check both an affected heading and a body description in-game.

## Restoration and local files

Restoration uses originals verified for their source version and disables automatic repair. Do not force a stale backup over updated official files. Unknown ownership, altered backups, concurrent edits, or an unreadable source stop the operation for review.

Keep `private-data` when updating the app. Source snapshots, key manifests, canonical maps, stages, history, provider URLs, pending reviews, and backups stay local and outside the public ZIP. If official files were changed independently, verify them through Steam rather than forcing an older backup.

## Public boundary

Publish code, attribution, documentation, and synthetic tests. Exclude game DATs, key manifests, extracted assets, complete English or translated tables, generated packs, update reviews, backups, credentials, and personal paths. Check the actual release archive separately from the code tests.
