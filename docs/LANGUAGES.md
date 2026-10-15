# Language compatibility

Language availability has three separate parts: the source format the app can read, the translation pair the selected provider offers, and the characters the game can render. Passing one does not verify the others.

## Current coverage

| Component | Current evidence | What remains unverified |
| --- | --- | --- |
| English source, Steam build 25926599 | A 153,042-entry table was decoded and reconstructed; edited Unicode text round-tripped | Every game screen and future updates |
| Turkish text | The complete patch was installed locally; structure and encode/decode checks passed. A player screenshot shows Turkish body text and missing heading glyphs. v0.1.1 adds selected-title compatibility | The repaired titles after restarting, broad terminology review, and full playthrough |
| Other target languages | Provider generation requires an advertised English-to-target pair; a complete local JSON map can also be imported | Native rendering, typography, layout, and broad game-specific translation quality |
| Other source locales or clients | No compatibility claim | Their table format, keys, file layout, and loader behavior |

The project's name describes its aim. It is not a statement that every language, server region, or game build is supported.

The Turkish work combines machine translation, selected edits, and reviewed context/template rules. The source contains 153,042 entries, all screened for known risks; the current consolidated local correction map contains 18,712 distinct keys. This does not mean all entries, or all correction keys, were individually proofread by a person. See the [quality report](QUALITY.md) for scopes and overlapping counts.

## Provider language discovery

Choose **Target language / Hedef dil** on the main screen. Turkish is initially selected; the editable chooser also offers common language codes. This is separate from the app's Turkish/English interface selector. A listed choice is not an installed pack or a compatibility result. **Apply translation / Çeviriyi uygula** applies a compatible local stage for that target; if no stage is ready, it opens translation settings with the selected target. Choosing English offers restoration of the original files.

The selected LibreTranslate-compatible instance supplies its own language list. Its [`GET /languages` response](https://docs.libretranslate.com/api/operations/languages/) includes language codes and the target codes supported from each source. Use the targets available for **English (`en`)**; a language appearing elsewhere in the response does not establish that this source pair is available.

A provider's models, limits, authentication, and language pairs can change. The application checks the server's advertised list before a provider translation starts. A missing target cannot be enabled merely by renaming a locale or choosing a different output filename.

An offline map does not require a provider language pair. It still requires the complete verified source key set, structural validation, and independent checks of that language's meaning and rendering.

## Review and corrections by language

| Check or correction | Targets covered | Limit |
| --- | --- | --- |
| Complete keys, protected tags/macros, numerals, technical abbreviations, and native encode/decode | Every generated target | Protects structure; does not establish correct meaning |
| Exact short UI actions and selected game terms in bounded fields | German (`de`), French (`fr`), Spanish (`es`), Italian (`it`), Portuguese (`pt`), Russian (`ru`), Japanese (`ja`), Korean (`ko`), Simplified Chinese (`zh`), Arabic (`ar`) | A small context glossary; not paragraph translation, full semantic review, or a font guarantee |
| Turkish context rules and selected local semantic edits | Turkish (`tr`) | The [documented Turkish review](QUALITY.md), not human review of all 153,042 values |
| Selected-title font compatibility | Turkish only | ASCII spelling in selected names/titles; does not repair other languages' fonts |

Each of the ten additional profiles contains 35 action labels and 4 selected terms. These are glossary definitions, not counts of game entries reviewed. The short-label rules use each language's UI conventions rather than imposing Turkish command grammar; they have not been certified by native-language specialists, checked against official terminology for every target, or verified inside the game. Simplified Chinese terminology is not applied to Traditional Chinese targets; Portuguese labels are general rather than a reviewed regional localization. Unlisted languages retain provider/imported wording and share the structural checks. The machine-readable [context-profile coverage record](CONTEXT-COVERAGE.json) lists the exact scope and limits.

To correct wording in any target, select it and use **Details… → Export translation…**, edit that language's complete local JSON map, and rebuild it through **Translation settings… → Offline JSON**. Keep entry keys, variables, tags, and numbers intact. Review the prepared result, close the game, and apply the matching target. There is no in-app per-entry text editor in this release. See [custom maps and corrections](TRANSLATION.md#custom-maps).

## What a generated language means

The current native workflow replaces English text values while the game's selected text language stays **English**. It does not add a new official entry to the game's language menu. Provider language codes and the game's `en-US` source locale serve different purposes.

Each target is built from the verified original English source, including when another translation is already installed. The app does not translate one generated language into another.

The application translates text values in the supported localization table. It does not promise localized audio, image textures, launcher pages, live chat, or text supplied by systems outside that table. Proper names and some technical labels can intentionally remain unchanged.

## Font and layout checks

Before calling a target language compatible, check:

- Characters specific to that language, including uppercase and lowercase forms.
- Menu widths, wrapping, clipped buttons, long item descriptions, and tooltips.
- Highlighted quest terms, inline tags, numbers, and dynamic values.
- Text shaping and direction where applicable; right-to-left rendering is not assumed to work.
- A representative quest, skill description, journal page, and confirmation dialog in-game.

For Turkish, include `ğ Ğ ş Ş ı İ ç Ç ö Ö ü Ü`. Successfully storing these characters in a DAT proves encoding support, not font coverage.

## Turkish heading compatibility in v0.1.1

Read-only character-map inspection of three fonts from the supported game build found different coverage for the 12 Turkish-specific uppercase/lowercase characters:

| Font examined locally | Turkish characters present |
| --- | --- |
| `Aion2Atreia_EN_Bold` | 1 of 12: only `ı` |
| `Aion2Yoon_EN_B` | 0 of 12 |
| `NotoSans-Bold` | All 12 |

The final DAT stores these characters correctly. A user screenshot exposed missing heading glyphs while Turkish body text remained readable. Font coverage is separate from encoding; Unreal can select fonts through character-range and font-family rules, as described in the [official Font Asset documentation](https://dev.epicgames.com/documentation/en-us/unreal-engine/font-asset-and-editor-in-unreal-engine).

For Turkish builds, **font-compatible titles** is enabled by default. It changes Turkish-specific letters to their ASCII counterparts only in selected name/title fields, for example `Ödüller → Oduller`. Descriptions and other body text retain Turkish spelling; placeholders and tag literals remain protected. The underlying source maps are retained. This is a deliberate readability tradeoff, not expanded font coverage or a claim of correct Turkish typography in titles.

The compatibility profile also corrects 31 related skill-name entries, including **Snipe → Keskin Atis**. It neither changes nor distributes the game's fonts, font assets, or font packages. The repaired result still needs an in-game check after restarting. See the [repair workflow](TRANSLATION.md#turkish-title-compatibility).

## Reporting a language result

Include the app revision, Steam build, source locale, target code, provider/model if known, and the exact feature you checked. Distinguish **codec checked**, **installed**, **game launched**, **visually checked**, and **playtested**. An absence of crashes is not a visual-language test.

Share short, rights-appropriate examples or synthetic reproductions. Do not attach full game tables, DATs, key manifests, credentials, or unredacted local paths.
