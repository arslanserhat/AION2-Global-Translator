<p align="center">
  <img src="assets/banner.svg" alt="AION 2 Global Translator — native game text, a language you choose" width="100%">
</p>

<p align="center">
  <img alt="Platform: Windows" src="https://img.shields.io/badge/platform-Windows-1673b8?style=flat-square">
  <img alt="Status: Experimental" src="https://img.shields.io/badge/status-experimental-c58b29?style=flat-square">
  <img alt="Method: Native text files" src="https://img.shields.io/badge/method-native_text_files-237e79?style=flat-square">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-5965ac?style=flat-square"></a>
  <a href="CONTRIBUTING.md#tests"><img alt="Tests: 152 passed locally" src="https://img.shields.io/badge/tests-152_passed-2ea44f?style=flat-square"></a>
  <a href="https://github.com/arslanserhat/AION2-Global-Translator/releases/latest"><img alt="Download Windows ZIP" src="https://img.shields.io/badge/download-Windows_ZIP-257e65?style=flat-square"></a>
</p>

<p align="center">
  <a href="README.tr.md">Türkçe</a> ·
  <a href="docs/TRANSLATION.md">Translation workflow</a> ·
  <a href="docs/LANGUAGES.md">Language compatibility</a> ·
  <a href="CONTRIBUTING.md">Contribute</a>
</p>

# AION 2 Global Translator

A free, open-source Windows tool that builds **native AION 2 text translations** from your own English game files, preserves original backups, and rebuilds your local language pack after compatible game updates.

**v0.1.3 — Current verified source: Steam build 26262663, 153,297 records.** This update adds 116 keys, changes 265 English values, and removes 4 keys compared with build 26077854. The 381 new or changed records have local Turkish corrections; unchanged translations carry over only when **both the key and English value match**. See the [v0.1.3 release notes](docs/RELEASE-v0.1.3.md).

The application is experimental. File-format checks do not prove every translation's meaning or every screen's appearance. Language availability depends on your provider and the game's renderer; the project does not promise support for every language or future client format.

## Get started

1. Download and extract the Windows ZIP from [the latest release](https://github.com/arslanserhat/AION2-Global-Translator/releases/latest). Run `AION2-Global-Translator.exe`. The ZIP includes `repak` and its license notices; it does not include game DATs or full translated tables.
2. Select your Steam AION 2 folder and **Target language / Hedef dil**. The target is the game's translation language; the app's Turkish/English interface selector is separate.
3. For a first pack, open **Translation settings… / Çeviri ayarları…**. Import a complete local JSON map or configure a LibreTranslate-compatible URL that supports English and your target.
4. Review the prepared translation, fully close AION 2, and select **Apply translation / Çeviriyi uygula**. Keep the game's text language set to **English**.
5. Restart the game normally and check menus, skill effects, quests, and rendered characters.

If Windows denies access to the game directory, the optional `AION2-Global-Translator-Admin.exe` opens the app with a Windows elevation prompt that you approve manually. The ordinary executable remains unelevated.

**Details… / Ayrıntılar…** contains installation checks, English-source export, translation export, logs, and explicit prepared-pack installation. Selecting English offers **Restore original / Orijinale dön**.

## What updates automatically

**Apply translation** detects when the selected local pack belongs to an older source and plans a rebuild against the current original English table. It does not force-install the old DAT.

- Unchanged **key + English value** pairs retain their previous translations.
- New or edited English values require fresh translations, including number-only changes and text reused under another key.
- A configured LibreTranslate-compatible server receives only the new or changed source text. The server's supported English-to-target pair is checked first.
- Without a usable provider, the app writes a private `pending.json` review list. Supply the required `corrections.json` and apply again.
- A complete, validated pack must be ready before installation. Missing translations or invalid formatting preserve the previous prepared pack and stop installation.

After the first successful install, **Automatically repair after updates / Güncellemelerden sonra otomatik onar** is enabled by default. It operates **only while this app is running**. If the game is open, it waits for the game to close before trying to update. It does not add a Windows startup task or background service. Restoring the original files turns this option off.

Future builds are checked from fresh original localization/startup archives, file fingerprints, the decoded source, and native round trips. Compatibility is not granted just by accepting another build number. Changes to encryption, container layout, or the source format may still require a tool update.

Read [the incremental-update workflow](docs/TRANSLATION.md#incremental-game-updates) for review-file locations and provider setup.

## Languages and corrections

Every language uses English as its source; the app does not translate through an already translated language. All targets share protected-format, number, macro, and technical-abbreviation checks.

Turkish has selected contextual corrections and a heading-display profile. Ten additional profiles provide a bounded set of short UI labels and game terms. Those profiles do not certify entire paragraphs, fonts, or gameplay in those languages. See [language compatibility](docs/LANGUAGES.md).

For a wording fix, select the target and use **Details… → Export translation…**. Edit values in that complete JSON map and rebuild through **Translation settings… → Offline JSON**. The editable map retains canonical spelling before display folding. During an update, the smaller `pending.json` / `corrections.json` workflow covers only changed records. See [custom maps](docs/TRANSLATION.md#custom-maps).

An offline map with unchanged language-bearing values requires explicit review of `unchanged-review.json`. Confirm intentional names or labels only; that confirmation is not a complete semantic review.

## Turkish characters

Some English display fonts lack Turkish glyphs. The Turkish compatibility option uses readable basic-Latin spellings in selected name/title fields, such as `Ödüller → Oduller` and `Keskin Atış → Keskin Atis`, while regular body text retains Turkish letters. The selected profile also handles `â/Â`.

**Fix headings (Turkish) / Başlıkları düzelt (Türkçe)** applies the available bounded repair to a verified Turkish pack. It does not replace fonts or repair every widget. Check affected text inside the game after a normal restart. Historical font findings and the earlier review scope are recorded in [v0.1.1 notes](docs/RELEASE-v0.1.1.md) and [QUALITY.md](docs/QUALITY.md).

The native-text workflow does not use screenshot OCR. Voice acting, text embedded in images, and live player chat are outside its coverage.

## Run from source

Use Python **3.12 or newer**:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m aion2_global_translator
```

`Start-Translator.cmd` is also provided. Dependencies include `cryptography`, `blake3`, and `lz4`. For a source installation, obtain Windows [repak 0.2.3](https://github.com/trumank/repak/releases/tag/v0.2.3), place it at `tools/repak.exe`, or set `REPAK_PATH`. The Windows ZIP supplies it.

The application is free. Your translation provider can have its own fees and limits. You can instead [self-host LibreTranslate](https://docs.libretranslate.com/guides/installation/) with the language models you need. Provider API keys are not saved; unattended checks can read `AION2_TRANSLATION_API_KEY` from the app process's environment.

## Backups and local data

Close the game before installing or restoring. Backups belong to their verified source version. Never copy an older backup over updated official files. Unknown patches, changed backups, or unsupported source data stop the operation for review.

Keep `private-data` when replacing the application: it holds your prepared packs, source snapshots, settings, update reviews, and backups. The public repository and ZIP contain application code/tooling only—no game DATs, key manifests, complete English or translated tables, game assets, credentials, or private backups. Online translation sends source text to the endpoint you select.

This is an independent community project without NC affiliation or approval. Client use remains governed by the [game's linked EULA](https://store.steampowered.com/eula/3393110_eula_0).

## Credits

Project code is licensed under [Apache-2.0](LICENSE). The codec adapts [CUE4Parse's AION 2 format work](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2); preserve its [Apache-2.0 notice](https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE). [repak](https://github.com/trumank/repak) uses MIT/Apache-2.0 licensing; upstream notices accompany the Windows ZIP. Provider discovery follows [LibreTranslate's language API](https://docs.libretranslate.com/api/operations/languages/). See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
