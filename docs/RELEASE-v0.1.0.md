# v0.1.0 — Experimental Windows release

AION 2 Global Translator builds and manages native text translations from a user's own game installation. This first release supports the verified English source format in **Windows Steam build 25926599**, containing **153,042 entries**. Other builds and clients remain unverified.

## Download and run

Download the Windows ZIP from [the v0.1.0 release](https://github.com/arslanserhat/AION2-Global-Translator/releases/tag/v0.1.0), extract it into a writable folder, and run `AION2-Global-Translator.exe`. The executable is approximately **17.6 MB**. Python is unnecessary for the packaged application.

The archive includes the application, `repak` **0.2.3**, project licensing, and upstream `repak` license notices. It includes no game DAT, key manifest, full source table, full translated table, provider credential, or paid translation-provider asset. Users generate private working files from their own installed game.

## Included

- English and Turkish application interfaces.
- Inspection of the supported game build and original English package.
- Local English source export and complete offline JSON map import.
- A user-configured LibreTranslate-compatible endpoint with language-pair discovery.
- Protected-format validation and native Unicode encode/decode checks.
- Separate translation generation and installation actions.
- Verified original-file backups and restoration, with changed-file and build checks.

Offline maps that retain language-bearing English values produce an `unchanged-review.json` report. Stage creation requires explicit confirmation that those values were reviewed; this is a review record, not proof of full translation quality.

## Verification and limits

The supported source passed byte-preserving serialization and edited Unicode round trips. The packaged Windows GUI opened successfully, and **34 synthetic tests passed locally**. These checks do not replace testing the game's rendered text or a full playthrough.

A complete **153,042-entry Turkish patch was generated and installed locally**, with the original backup preserved. Structure validation and the native encode/decode round trip passed. **138,615 entries differ from English**, and **1,022 keys received human corrections**. The remaining 4,114 unchanged language-bearing entries are mostly proper names, server names, technical development records, and utterances; long English quest and achievement text identified during final review was corrected. This remains machine translation with selected corrections, not a fully human-reviewed localization.

The installed full patch loads on the next game restart; its in-game rendering has not been independently verified. Its game-derived table is not distributed in this release.

Target-language availability depends on the chosen provider's English-to-target pair and the game's font, layout, and rendering behavior. This release does not claim support for every language.

Voice acting, image-embedded text, live player chat, and text outside the supported table are outside this workflow. Machine-translated text needs human review, especially skill effects, quest directions, passwords, and riddles.

Close the game before installing or restoring. Keep its selected text language on **English**. Restore original files before switching patches or updating the game, and do not apply a stale backup over a newer build. Client changes remain subject to the [game's linked EULA](https://store.steampowered.com/eula/3393110_eula_0); the project has no publisher approval or account-safety guarantee.

## Licensing

Application source is [Apache-2.0](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.0/LICENSE). The codec adapts [CUE4Parse's AION 2 work](https://github.com/FabianFG/CUE4Parse/tree/master/CUE4Parse/GameTypes/Aion2), also Apache-2.0. `repak` is [MIT/Apache-2.0 licensed](https://github.com/trumank/repak); its notices accompany the Windows distribution. See [THIRD_PARTY_NOTICES.md](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.0/THIRD_PARTY_NOTICES.md).

[English README](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.0/README.md) · [Türkçe README](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.0/README.tr.md) · [Translation workflow](https://github.com/arslanserhat/AION2-Global-Translator/blob/v0.1.0/docs/TRANSLATION.md) · [Report an issue](https://github.com/arslanserhat/AION2-Global-Translator/issues)
