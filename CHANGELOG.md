# Changelog - Nordic Dragonbone Armor Replacer

## 1.0.0

First release.

* Packages the dragonbone (dragonplate) and dragonscale armour from **Simply Realistic Armor and
  Weapons (Custom NordwarUA Edition)**, Nexus 47184, as a FOMOD that asks which finish you want.
* Two finishes: **Standard**, as the authors made it, and **Black Edition**, their darker variant.
  The meshes are byte-identical between them, so the installer lays down one shared copy and the
  choice swaps textures only.
* `tools/build-fomod.py` reads the two Nexus downloads at build time. The repository carries none
  of the authors' files.
* Coverage checked against the game: all 31 mesh paths that a vanilla dragon-armour ARMA record
  points at are replaced, both body weights, first-person, ground models and the Orc, Khajiit and
  Argonian helmets. Nothing falls back to the vanilla BSA.
* Two textures the Black Edition ships but no mesh references - `dragonplate_alt_silver_mail.dds`
  and `lamellarnordhelm2.dds`, 28 MB between them - are left out of the package.
* No plugin. This mod is meshes and textures only, so it has no ESP, takes no load-order slot and
  has nothing to convert to light.
