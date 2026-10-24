# v0.1.2 — Steam build 26077854

The October update changed the English text table from 153,042 to 153,185 records. A v0.1.1 pack cannot be installed on this build by changing only its version number: 143 keys were added and 227 existing source strings changed.

- Pins the current Steam build, original locale PAK and English DAT hashes, and the 153,185-record coverage check. Unknown builds and old prepared packs still stop before installation.
- Shows the actual and expected build with an actionable Turkish message.
- Recovers checksum-verified leftovers from this tool's 25926599 installation after Steam updated the original PAK. The current original PAK and signature stay intact. Unchanged container companions are verified against the current depot's contents; all old loose/side files are archived privately before cleanup. Unknown or edited files stop the recovery.
- Uses a new backup namespace for the current build; older backups remain available.
- Includes an optional `AION2-Global-Translator-Admin.exe` launcher for installations where Windows denies permission to rename game files. It opens the ordinary app at the user-approved elevation; the normal executable remains unelevated. Windows elevation approval is manual.
- Extends the existing limited Turkish heading compatibility profile to `â/Â`, which the inspected English heading fonts also lack. This is a spelling fallback in selected fields, not a replacement of the game's fonts or a guarantee that every widget renders Turkish.

119 synthetic/unit/UI checks passed, including current-build checks, recovery refusal on altered files, preservation of current originals, rollback after partial cleanup, concurrent-edit rejection, and the selected-heading regression. Local full-table decoding and rebuilding are checked separately. These checks do not constitute visual validation of every game screen.

The public ZIP contains the application and tooling only. Full game text tables, local translations, original game files, caches and private backups are excluded. Create a pack from your own current English source or import a complete map for this build. Reusing an old full map without reviewing changed/new source entries is unsupported.
