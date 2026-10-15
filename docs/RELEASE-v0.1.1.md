# v0.1.1 — Language selection and translation corrections

A target-language chooser, a shared apply workflow, editable translation exports, and stronger technical-text protection. Turkish receives contextual terminology and heading compatibility; ten additional targets receive bounded short-label terminology. The Turkish quality pass screened the **153,042-entry** source table and consolidated **18,712 distinct override keys** from selected edits and reviewed rules/templates. This is not a claim that every entry was individually human-reviewed.

## Select, build, and apply a language

Choose **Hedef dil / Target language** on the main screen. Turkish is selected initially; choose another common language or enter a code. The chooser does not claim that every target is bundled, offered by the provider, or renderable in the game.

| Control | Purpose |
| --- | --- |
| **Çeviriyi uygula / Apply translation** | Apply a compatible prepared pack for the selected language; open settings with that target selected if no stage is ready |
| **Orijinale dön / Restore original** | Restore verified original files; selecting English offers this action |
| **Başlıkları düzelt (Türkçe) / Fix headings (Turkish)** | Apply available Turkish terminology and heading repairs; disabled for other target languages |

**Çeviri ayarları… / Translation settings…** opens provider/offline-map configuration. **Ayrıntılar… / Details…** contains logs, installation checks, source and translation export, and explicit prepared-pack installation. Generation remains separate from installation. Each target is generated from verified original English, rather than from an installed translation.

## Correct wording in any target

A successful build keeps the complete editable map at `private-data/stages/<target>/entries.translated.json`, before Turkish heading-character folding. Use **Details… → Export translation…** for the selected target, change the relevant text values, and rebuild through **Translation settings… → Offline JSON**. The complete key set and protected formatting must remain valid. There is no in-app per-entry editor.

All targets share key, tag, macro, number, technical-abbreviation, and native encode/decode checks. German, French, Spanish, Italian, Portuguese, Russian, Japanese, Korean, Simplified Chinese, and Arabic each have a bounded profile with 35 short UI actions and 4 selected context terms. These profiles follow their own UI conventions; they are not full sentence translation, native-language specialist approval, or full semantic review. Provider availability, fonts, and rendering remain target-specific. [Language review coverage](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/docs/LANGUAGES.md#review-and-corrections-by-language).

## Turkish translation changes

- Button and quest commands use singular imperatives: **Talk → Konuş**, Use → Kullan, Collect → Topla, Craft → Üret. Names remain names; descriptive skill text keeps descriptive grammar.
- **HP, MP, and other game abbreviations** are protected before provider translation and validated afterwards. A renewed cache profile avoids reusing results from the earlier protection version; legacy cache rows are retained.
- Context rules distinguish class labels, weapon **Staff → Asa**, ability **Cast/Casting**, precision **Snipe → Keskin Atış**, and item **(Bound) → (Bağlı)**. Employee, animal, and genuine book-binding meanings are handled separately.
- Selected repairs address lost skill conditions, resource/unit meaning, quest actions and reward verbs, omitted speakers, and inconsistent place or NPC names. Server names retain their source spelling.

The consolidated correction map is local game-derived data. The public release contains the application and bounded terminology/validation rules, not that full map or a translated game table. [Quality report and exact review scopes](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/docs/QUALITY.md).

## Turkish heading compatibility

Some English display fonts lack Turkish glyphs although body text can display them. **Adapt Turkish titles to the game font** is enabled by default for Turkish builds: selected names/titles use compatible spellings, such as `Ödüller → Oduller` and `Keskin Atış → Keskin Atis`. Body accents, source maps, protected variables, and tags are preserved.

This trades the orthography of selected titles for readability. It does not replace fonts or add glyphs. Local character-map inspection found only `ı` among the 12 Turkish-specific forms in `Aion2Atreia_EN_Bold`, none in `Aion2Yoon_EN_B`, and all 12 in `NotoSans-Bold`. A player screenshot exposed the heading issue; the repaired screen still needs an in-game check after restarting. [Font compatibility evidence](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/docs/LANGUAGES.md).

## Upgrade and use

Download and extract the [v0.1.1 Windows release](https://github.com/arslanserhat/AION2-Global-Translator/releases/tag/v0.1.1). The archive includes the app, `repak` 0.2.3, and license notices. It contains no game DAT, key manifest, full string table, game font asset, provider credential, or paid-provider asset. Users generate private working files from their own installation.

For an existing compatible Turkish installation, select Turkish, close AION 2, run **Başlıkları düzelt (Türkçe) / Fix headings (Turkish)**, and restart manually. Keep the original backup. For another target, prepare and review its pack, close the game, and use **Apply translation**. Restore a patch installed by another tool through that tool's restoration path first.

## Verification and scope

The supported client remains **Windows Steam build 25926599**. The public source passed **108 tests locally**. The compact Windows GUI's Turkish/English layout and busy-state controls were checked separately. The final local Turkish patch was installed: all **153,042 entries**, the **18,712-key** consolidated correction set, full decoded values, native round trip, and zero unresolved formatting failures were checked. Key/format validation, installation checks, selected semantic review, and in-game appearance remain separate evidence.

A full local export/edit/rebuild probe preserved all 153,042 keys and their order, one controlled NPC-text edit, and 601 untouched legacy cells, with an exact expected decoded map; the live game DAT and original local bundle hashes remained unchanged. Legacy carry-forward requires a verified reference and does not approve meaning; new or changed cells retain strict abbreviation checks.

A full playthrough and complete human proofreading are not claimed. Other targets have the shared validation and, for the ten listed targets, a short-label context profile. They have not received the Turkish corpus-level semantic review. Online generation depends on the provider's English-to-target pair; usability also depends on the game's fonts/rendering.

Source remains [Apache-2.0](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/LICENSE), with [third-party notices](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/THIRD_PARTY_NOTICES.md) for the adapted codec and packaged tools.

[English README](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/README.md) · [Türkçe README](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/README.tr.md) · [v0.1.0 notes](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.1/docs/RELEASE-v0.1.0.md)
