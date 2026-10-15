# Third-party notices

## CUE4Parse (format reference and adapted algorithms)

Copyright (c) 2020 CUE4Parse contributors. Apache License 2.0.

`src/aion2_global_translator/codec.py` is a Python adaptation of the publicly documented AION 2 DAT, L10N, manifest and archive algorithms in CUE4Parse. It adds serialization, verification and Unicode editing. The original project and license are available at <https://github.com/FabianFG/CUE4Parse> and <https://github.com/FabianFG/CUE4Parse/blob/master/LICENSE>.

## repak

Optional external extraction utility: <https://github.com/trumank/repak>, version 0.2.3, dual MIT / Apache-2.0. Official Windows ZIP SHA-256: `6720d602144d75df477a99d5bedb6ea780997546afc335901d4937cafeaa73fa`.

Local binary distributions include repak and its upstream license texts in `licenses/repak/`. The repository contains no repak executable.

## Python dependencies and executable builds

Python (PSF license), cryptography (Apache-2.0 OR BSD-3-Clause), blake3 (CC0-1.0 OR Apache-2.0), lz4 (BSD), and their transitive native components retain their respective upstream licenses. PyInstaller is GPL-2.0-or-later with an exception permitting redistribution of built applications. See the copied dependency license texts in binary distribution `licenses/`.

## Localization deployment reference

The native loose-file approach was examined independently against the open project <https://github.com/duoluoyuji/Aion2-Steam-CN>. No translated game tables from that project are included here. Our marker and backup transaction implementation is independent.
