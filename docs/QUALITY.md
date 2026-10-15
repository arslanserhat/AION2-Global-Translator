# Turkish translation quality and review scope

The Turkish work combines machine translation, programmatic checks, reviewed terminology and templates, and selected manual edits. The **153,042-entry** English source table from **Windows Steam build 25926599** was screened for known risks. This is not a statement that a person has read and approved every translated sentence.

The consolidated local correction map contains **18,712 distinct keys**, including earlier selected corrections and the passes below. It was included in the installed local 153,042-entry patch, whose full decoded map and native round trip passed verification with no unresolved format failures. In-game visual verification of that final revision remains separate. The map remains local game-derived data; the public repository distributes the tooling and review methodology.

## What was examined

These figures describe individual development passes. Their scopes and corrections overlap; adding the rows would give an incorrect count of unique corrected entries.

| Pass | Screening scope | Corrections produced |
| --- | --- | --- |
| Global risk screen | All 153,042 entries; polysemy, missing technical abbreviations, and unusually shortened prose | Candidates sent to context-specific review |
| Earlier canonical corrections | Selected labels, skills, and passages from prior development passes | 1,053 keys carried into consolidation, some superseded by later corrections |
| Combat and skills | 31,190 entries / 9,853 distinct source-target pairs | 3,179 entry overrides from reviewed meanings, mechanics, and bounded templates |
| Quests, achievements, guides, and notes | 29,445 entries; 8,656 contain the selected action verbs | 7,680 entry overrides: 3,053 semantic/name/template changes and 4,630 singular-imperative changes, with 3 entries shared between those groups |
| UI, items, labels, and related data | 72,332 entries / 47,105 distinct English values | 6,141 entry overrides / 4,893 source values; 150 exact source-target pairs reviewed individually, with the rest handled by reviewed context rules and schemas |
| NPC dialogue, subtitles, and character descriptions | 21,283 NPC entries, 1,081 subtitle entries, and 16 class descriptions screened | An additional context pass produced 65 corrections across class descriptions, selected NPC/messages, Wind-related skills, and reward headers; these overlap other scopes |
| Dream Crossroad consistency | All 67 keys containing that exact place name / 33 distinct source-target pairs | 55 corrections; 12 references were already compatible |

A final source-context consistency pass corrected **927 keys**: 571 item-binding labels, 333 server names restored exactly, 12 map references, and 11 Santras references. Genuine book-binding descriptions were considered separately from the game's item-binding flag. A final selected review contributed 95 corrections, 47 overlapping earlier keys; the consolidated unique total is 18,712.

The quest command pass examined **8,698 objective fields** whose English source begins with a recognized imperative. It used explicit Turkish verb forms and clause boundaries, with protected-format checks. It did not remove endings from arbitrary names or rewrite polite NPC dialogue as commands.

The UI pass used an **82-entry stat glossary** and **52-entry action glossary**, with bounded parsers for repeated title effects, food, stones, and wings. It did not treat every item name or story passage as individually reviewed. Repeated templates can cover many keys after a single reviewed interpretation.

## Decisions made in context

| Context | Chosen treatment |
| --- | --- |
| Interaction or quest command | `Talk → Konuş`, `Use → Kullan`, `Collect → Topla`, `Craft → Üret`; second-person singular imperative |
| Name or title | A noun or name can remain a noun; command grammar is not applied to every label |
| Skill description | Descriptive grammar such as “hasar verir”; resource, condition, probability, amount, and duration remain distinct |
| Weapon `Staff` | `Asa`; staff meaning employees is kept separate |
| Ability `Cast` / `Casting` | Ability use/preparation, according to the field; not metal casting |
| Ability `caster` | The ability's user; not automatically the Sorcerer class, a wheel, or a foundry worker |
| `MP` | The mana resource; its abbreviation, values, and protected variables are preserved |
| Dungeon or challenge `Clear` | Complete the activity; not “transparent,” “explain,” or an arbitrary cleaning instruction |
| Completion-reward objective | Receive the rewards: `Tamamlama ödüllerini al` |
| Clearing creatures or an area | A suitable clearing/removal verb can remain; `Clear` is not replaced globally |
| Magical `seal` / creature `seal` | `Mühür` / animal terminology according to context |
| Source item flag `(Bound)` | `(Bağlı)`; genuine book-binding language is evaluated separately |
| Precision skill `Snipe` | Canonical `Keskin Atış`; compatible heading display `Keskin Atis` |
| Place reference | One chosen name with appropriate Turkish suffixes: `Rüya Kavşağı'na`, `Rüya Kavşağı'nda` |

Selected repairs also restored omitted speakers, lost solo-contribution requirements, quest directions, and highlighted clues. Passwords and letter puzzles need individual treatment; protected formatting alone cannot preserve their meaning.

## Class terminology reference

The project chose familiar names documented in Gameforge's **older AION 4.5 Turkish patch notes**: Gladyatör, Tapınakçı, Avcı, Suikastçı, Sihirbaz, Ruh Çağırıcı, Ruhban, and Kantor. These are a historical terminology reference, not evidence of an official Turkish localization for AION 2. [Gameforge Turkish patch notes, skill tables](https://cmsstatic.aion.gameforge.com/Patchnotes_4_5_1002v_TR_final.pdf#page=11).

Gameforge's [Basic Classes Information](https://forum.aion.gameforge.com/forum/thread/745-basic-classes-information/) provides additional historical role context, including Ranger's bow and Chanter's mantras. The project's AION 2 class-description corrections were written from the user's English game text; they were not copied from those older descriptions.

## What verification establishes

The native workflow checks the complete key set and entry order, protected placeholders, literal tags and their order, numeric/control structure, and encode/decode agreement. Source round trips, installation hashes, and backups provide separate file-integrity evidence. Passing these checks establishes those properties; it does not establish that every sentence accurately describes the game's mechanics or story.

Technical game abbreviations, including **HP** and **MP**, are protected before provider translation and checked afterwards. Provider caching uses a revised protection profile; legacy rows are retained but are not reused as results for that new profile. Cached answers must pass current validation. This prevents a protection upgrade from silently inheriting incompatible old cached text; it does not certify the meaning of every valid provider answer.

Turkish font compatibility is another separate concern. Local font character maps explain why accented body text can work while a heading lacks glyphs. The optional title compatibility profile uses ASCII spellings in selected names/titles while preserving body accents and the source maps. See [language compatibility](LANGUAGES.md#turkish-heading-compatibility-in-v011) and [translation workflow](TRANSLATION.md#turkish-title-compatibility). No game font assets are distributed.

A player screenshot is evidence for the particular screen it shows. It does not establish every screen, a full playthrough, or the appearance of a later repaired build. Automated checks, schema review, selected sentence review, installation, and in-game visual checks are recorded as different forms of evidence.

## Remaining scope

Unflagged text can still contain mistakes. Names, idioms, paragraphs split around tags, and context shared across quests can need further review. The review figures above must not be described as complete human review of the full table.

Other target languages have not received this Turkish corpus-level semantic review. All targets share the format, number, macro, and technical-abbreviation checks. Ten other target profiles provide a small glossary of 35 short actions and 4 selected terms each, applied only in bounded fields. This is not review of their paragraphs, native-language specialist approval, or a whole-language accuracy claim. Their generation depends on the configured provider's English-to-target pair, or a complete local JSON map, and their usability depends on the game's fonts, layout, and rendering. See [language-specific review coverage](LANGUAGES.md#review-and-corrections-by-language).

Wording can be corrected in any target through a complete edited JSON map and a new build. The app does not apply Turkish grammar to those languages, and its Turkish heading repair is disabled for other targets. The project does not claim that every language works.

When reporting a problem, include the build, entry key if known, the relevant screen or short text, and the intended meaning. Explain whether the problem is meaning, grammar, a number/condition, a name, or display. Keep full game tables, DATs, manifests, credentials, and personal paths out of public issues.
