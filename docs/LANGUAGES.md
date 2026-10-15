# Language compatibility

Language availability has three separate parts: the source format the app can read, the translation pair the selected provider offers, and the characters the game can render. Passing one does not verify the others.

## Current coverage

| Component | Current evidence | What remains unverified |
| --- | --- | --- |
| English source, Steam build 25926599 | A 153,042-entry table was decoded and reconstructed; edited Unicode text round-tripped | Every game screen and future updates |
| Turkish text | The complete 153,042-entry patch was installed locally with original backups preserved; structure and encode/decode checks passed. 138,615 entries differ from English and 1,022 keys have human corrections | Rendered text after restarting the game, broad terminology review, and full playthrough |
| Other target languages | Available only when offered by the configured provider for the English source | Native rendering, typography, layout, and game-specific translation quality |
| Other source locales or clients | No compatibility claim | Their table format, keys, file layout, and loader behavior |

The project's name describes its aim. It is not a statement that every language, server region, or game build is supported.

The Turkish work combines machine translation and selected human corrections. Its 4,114 unchanged language-bearing entries are mostly proper names, server names, technical development records, and utterances. Long English quest and achievement text identified during the final review was corrected. Complete table coverage does not imply a full human review or verified in-game appearance.

## Provider language discovery

The selected LibreTranslate-compatible instance supplies its own language list. Its [`GET /languages` response](https://docs.libretranslate.com/api/operations/languages/) includes language codes and the target codes supported from each source. Use the targets available for **English (`en`)**; a language appearing elsewhere in the response does not establish that this source pair is available.

A provider's models, limits, authentication, and language pairs can change. The application checks the server's advertised list before a provider translation starts. A missing target cannot be enabled merely by renaming a locale or choosing a different output filename.

## What a generated language means

The current native workflow replaces English text values while the game's selected text language stays **English**. It does not add a new official entry to the game's language menu. Provider language codes and the game's `en-US` source locale serve different purposes.

The application translates text values in the supported localization table. It does not promise localized audio, image textures, launcher pages, live chat, or text supplied by systems outside that table. Proper names and some technical labels can intentionally remain unchanged.

## Font and layout checks

Before calling a target language compatible, check:

- Characters specific to that language, including uppercase and lowercase forms.
- Menu widths, wrapping, clipped buttons, long item descriptions, and tooltips.
- Highlighted quest terms, inline tags, numbers, and dynamic values.
- Text shaping and direction where applicable; right-to-left rendering is not assumed to work.
- A representative quest, skill description, journal page, and confirmation dialog in-game.

For Turkish, include `ğ Ğ ş Ş ı İ ç Ç ö Ö ü Ü`. Successfully storing these characters in a DAT proves encoding support, not font coverage.

## Reporting a language result

Include the app revision, Steam build, source locale, target code, provider/model if known, and the exact feature you checked. Distinguish **codec checked**, **installed**, **game launched**, **visually checked**, and **playtested**. An absence of crashes is not a visual-language test.

Share short, rights-appropriate examples or synthetic reproductions. Do not attach full game tables, DATs, key manifests, credentials, or unredacted local paths.
