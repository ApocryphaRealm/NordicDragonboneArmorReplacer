# Nordic Dragonbone Armor Replacer

A FOMOD installer for the dragonbone (dragonplate) and dragonscale armour from
[Simply Realistic Armor and Weapons (Custom NordwarUA Edition)](https://www.nexusmods.com/skyrimspecialedition/mods/47184)
by QuestionableKhajiit and NordWarUA, offering a choice between their Standard finish and their
Black Edition with a picture of each.

**None of the art is in this repository.** `tools/build-fomod.py` opens the two Nexus downloads at
build time and takes only the dragon paths out of them. To build the package you need both files
from that mod page; the script names them and tells you if either is missing.

## Building

```
python tools/build-fomod.py
```

Downloads are looked for in `D:\modlists\Njordlinger\downloads`; set `NDAR_DOWNLOADS` to point
elsewhere. The output lands in `7. current test builds\Nordic Dragonbone Armor Replacer <version>`.

The script refuses to produce a package rather than producing a wrong one. It stops if a download
is missing, if the two finishes turn out identical, if their meshes stop being identical (the
installer ships one shared copy of them), if any vanilla dragon-armour mesh path is left uncovered,
or if an installer image the XML points at is absent.

## Versioning

The version lives in `fomod/info.xml` and is issued by the project's version gate:

```
.MD\scripts\version-gate.ps1 -Action bump -Mod ApocryphaNordicDragonboneArmorReplacer
```

Never type a number into it by hand.

## Licence

The installer, the build script, the images and the documentation are GPL-3.0-or-later,
Copyright (C) 2026 ApocryphaRealm. The armour is its authors' - see `NOTICE.md`.
