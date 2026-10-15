<p align="center">
  <img src="assets/banner.svg" alt="AION 2 Global Translator — native game text, a language you choose" width="100%">
</p>

<p align="center">
  <img alt="Platform: Windows" src="https://img.shields.io/badge/platform-Windows-1673b8?style=flat-square">
  <img alt="Status: Experimental" src="https://img.shields.io/badge/status-experimental-c58b29?style=flat-square">
  <img alt="Method: Native text files" src="https://img.shields.io/badge/method-native_text_files-237e79?style=flat-square">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-5965ac?style=flat-square"></a>
  <a href="CONTRIBUTING.md#tests"><img alt="Tests: 108 passed locally" src="https://img.shields.io/badge/tests-108_passed-2ea44f?style=flat-square"></a>
  <a href="https://github.com/arslanserhat/AION2-Global-Translator/releases/latest"><img alt="Download Windows ZIP" src="https://img.shields.io/badge/download-Windows_ZIP-257e65?style=flat-square"></a>
</p>

<p align="center">
  <a href="README.tr.md">Türkçe</a> ·
  <a href="docs/LANGUAGES.md">Language compatibility</a> ·
  <a href="docs/TRANSLATION.md">Translation workflow</a> ·
  <a href="docs/QUALITY.md">Quality review</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

# AION 2 Global Translator

A free, open-source Windows application for building and managing **native AION 2 text translations** from your own game installation. Choose a translation provider, create a local language patch, and install it with a verified backup and a restore path.

Target-language availability depends on your provider and the game's fonts. The project does **not** claim that every language is supported.

## What it does

- Reads the supported English localization format from your installed game.
- Uses a LibreTranslate-compatible endpoint that you configure, with language discovery from that endpoint.
- Imports a complete local JSON translation map for offline patch generation.
- Lets you select a target language on the main screen and apply a compatible local pack.
- Builds a native text file while preserving entry identifiers and protected formatting.
- Keeps original files for restoration and checks the game build before changing files.
- Separates translation generation from installation, so a result can be checked first.
- Offers Turkish title compatibility for the game's limited heading fonts while preserving Turkish letters in body text.

The game reads the generated text file directly. This workflow does not depend on screenshot OCR. Voice acting, text baked into images, and live player chat are outside its coverage.

## Current status

**Experimental.** The codec has been checked against Windows Steam build **25926599**, whose English text table contains **153,042 entries**. Byte-preserving source round trips and edited Unicode encode/decode checks passed during development. That verifies serialization; it does not establish complete in-game compatibility.

A **153,042-entry Turkish patch has been generated and installed locally**, with the original files backed up. The installed revision includes **18,712 distinct override keys** from selected edits, reviewed context rules, and templates after screening the whole source table. Its complete decoded key/value map and native round trip passed verification, with no unresolved format failures. That correction count does not describe individually human-reviewed sentences or a human review of every entry. Structure validation and native encode/decode checks are recorded separately from meaning and display checks.

A player screenshot confirmed Turkish body text and exposed missing glyphs in a heading. Font inspection identified incomplete Turkish coverage in the game's English display fonts; v0.1.1 addresses selected titles with the compatibility option below. The repaired result still requires an in-game check after restarting. The game-derived table and local correction map are not included in the public download. The packaged Windows application opened successfully; see [local test information](CONTRIBUTING.md#tests) and the [review scope](docs/QUALITY.md).

| Area | Status |
| --- | --- |
| Windows Steam build 25926599 / English source | Codec verified; native installation experimental |
| Turkish | Full local patch installed; body text shown in a player screenshot; heading compatibility repair added in v0.1.1 |
| Other target languages | Depend on the configured provider, language pair, and font/rendering checks |
| Other game builds, regions, or launchers | Unverified |
| Voice, image text, and live chat | Outside this text-patch workflow |

See [language compatibility](docs/LANGUAGES.md) for the difference between a provider offering a language and a translation working inside the game.

The [quality review report](docs/QUALITY.md) records the corpus screening, selected semantic corrections, terminology choices, and singular-command grammar. It separates those checks from full human review and in-game verification.

## Choose a language and apply it

Select **Target language / Hedef dil** on the main screen. Turkish is the default; choose another listed language or enter its code. This chooses the game's translation target; the separate Turkish/English interface selector changes the app's labels. The target list offers convenient choices, not a promise that a pack is bundled or that the provider and game support every choice.

| Control | Action |
| --- | --- |
| **Apply translation / Çeviriyi uygula** | Install a compatible prepared pack for the selected target; if none is ready, open translation settings with that target selected |
| **Restore original / Orijinale dön** | Restore verified original files; selecting English also offers this action |
| **Fix headings (Turkish) / Başlıkları düzelt (Türkçe)** | Apply the available Turkish context-term and heading-display repair; disabled for other targets |

**Translation settings… / Çeviri ayarları…** opens provider/offline-map configuration. **Details… / Ayrıntılar…** contains the log, installation check, English source export, and prepared-pack installation. The public download contains the tool; game-data bundles must be generated locally.

Every target uses the same protected-format, number, macro, and technical-abbreviation checks. Ten additional language profiles provide a small set of exact short UI labels and selected game terms. The broader semantic review and title compatibility described here were developed for Turkish; they do not certify another language's grammar, paragraphs, or fonts. See [language-specific review](docs/LANGUAGES.md#review-and-corrections-by-language).

For a wording correction in any language, select its target and use **Details… → Export translation…**. Edit the affected values in that complete JSON, then rebuild through **Translation settings… → Offline JSON**. The editable local map is retained before Turkish title folding. There is no in-app per-entry editor; see [the correction workflow](docs/TRANSLATION.md#custom-maps).

## Turkish heading compatibility

Some English heading fonts lack Turkish glyphs even though the body font supports them. The **font-compatible titles** option is enabled by default for Turkish builds: selected name/title fields use readable ASCII spellings, such as `Ödüller → Oduller` and `Keskin Atış → Keskin Atis`. Body text keeps `ç ğ ı İ ö ş ü` and their uppercase forms. This trades title orthography for readability; it does not add glyphs or replace the game's fonts.

v0.1.1 also repairs an existing compatible Turkish installation and corrects 31 related skill-name entries, including the mistaken bird translation of **Snipe**. Source maps remain intact, and no font assets are distributed or modified. See [the workflow](docs/TRANSLATION.md#turkish-title-compatibility) and [v0.1.1 notes](docs/RELEASE-v0.1.1.md).

## Get started

### Windows download

Download and extract the Windows ZIP from [the latest release](https://github.com/arslanserhat/AION2-Global-Translator/releases/latest), then run `AION2-Global-Translator.exe`. The application executable is approximately **17.7 MB**. The ZIP includes `repak` 0.2.3 and its license notices, so Python and a separate `repak` download are unnecessary for that distribution. It contains no game DAT or full translation table; working files are generated from your own installation. See the [v0.1.1 release notes](docs/RELEASE-v0.1.1.md).

### Run from source

Install Python **3.12 or newer**, then run these commands from the project directory:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m aion2_global_translator
```

Use your installed Python 3.12+ version if it differs from the example. `Start-Translator.cmd` is the provided Windows launch entry. Dependencies include `cryptography`, `blake3`, and `lz4`; installation resolves them through the project package.

The Windows executable is packaged with PyInstaller. The source workflow above remains available for development and review.

### Prepare and install a language

1. Keep an up-to-date, legitimate Steam installation of AION 2. The current workflow uses its **English** text as the source.
2. The Windows release ZIP supplies `repak`. For a source installation, download Windows `repak` **0.2.3** from the [upstream release](https://github.com/trumank/repak/releases/tag/v0.2.3), then put it at `tools/repak.exe` or set `REPAK_PATH` to its location.
3. Open **Details… → Check installation** to verify the source. Use **Details… → Export English source…** to prepare a complete offline map from your local source. Extracted game files and generated tables remain local.
4. Choose **Target language** on the main screen, then open **Translation settings…**. Import a complete local JSON map, or set your LibreTranslate-compatible server URL and, if that server requires one, your own API key. Provider translation checks the target against the server's supported languages and English source pair.
5. Generate and review the translation. Resolve formatting failures and check important menu labels, skills, quest directions, and puzzle clues.
6. Fully close AION 2, select the target and use **Apply translation** once a compatible stage is ready. **Details… → Install prepared language…** also lets you choose a stage folder explicitly. Keep the original backup. Leave the game's text language set to **English**, then check the translated menus in-game.

The application is free. A hosted translation provider can have its own fees, limits, and terms. A self-hosted LibreTranslate server is another option; use its [official installation guide](https://docs.libretranslate.com/guides/installation/) and load the language models you need.

Creating a pack does not install it. Applying a language requires a locally prepared compatible bundle; the public repository does not supply the game's full translated tables. See the [map contract](docs/TRANSLATION.md#custom-maps) before importing a file.

An offline map with unchanged language-bearing values produces an `unchanged-review.json` report and cannot become a stage until you explicitly confirm their review. Confirm only intentional unchanged names or labels; this review and structural validation do not establish complete translation quality.

## Updates and restoration

The app can switch between its own verified compatible packs on the same source build while preserving the original backup. Close AION 2 before applying a pack. Restore the original files before updating the game; if another tool installed a patch, restore it with that tool first. A patch and its backup belong to a particular source build; do not apply an old backup over an updated installation. If build or hash checks fail, stop and prepare a fresh source from the current official files.

Client-file changes may conflict with the game's terms or integrity checks. This independent project has no NC approval or account-safety guarantee. The [game's linked EULA](https://store.steampowered.com/eula/3393110_eula_0) governs use of the client.

## Game data stays out of this repository

This repository distributes application source, documentation, and synthetic test material. It must not contain game DATs, key manifests, complete extracted or translated string tables, game backups, API credentials, or personal filesystem paths. Users generate working files from their own installation.

Source text is sent to the translation endpoint you select when network translation is enabled. Choose a provider whose access rules and handling of submitted text suit your needs. Do not commit provider credentials or generated translation caches.

## Credits

Project source is licensed under [Apache-2.0](LICENSE); see the included third-party notices for adapted code and dependencies.

The localization codec is adapted from the AION 2 format work in [CUE4Parse](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2), which is licensed under [Apache-2.0](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE). `repak` has [MIT and Apache-2.0 licensing](https://github.com/trumank/repak); its upstream notices accompany the Windows ZIP. Language discovery follows the configured server's [LibreTranslate `/languages` API](https://docs.libretranslate.com/api/operations/languages/).

AION 2 and its game content belong to NC and their respective rights holders. This is an independent community tool, with no affiliation or endorsement implied.
