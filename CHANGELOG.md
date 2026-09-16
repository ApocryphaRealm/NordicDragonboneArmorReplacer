# Changelog - Nordic Dragonbone Armor Replacer

## 1.0.1

* Adds a light plugin - a `.esp` carrying the light flag, an ESPFE. Not a `.esl` file: the game
  forces those to the top of the load order where nothing can sort below them, which would defeat
  the point of shipping a plugin at all. It points vanilla's twenty dragon armour ADDON records at this mod's own
  mesh folder, so the worn armour is settled by load order and another mod can supersede it in the
  plugins tab rather than only by mod priority.
* Addon records rather than armour records on purpose: 20 instead of 258. Every pre-enchanted
  dragon armour variant reaches its worn model through the shared addon, so twenty overrides change
  all of them, and the plugin does not collide with anything that edits dragon armour stats.
* Ground models keep their vanilla paths and are picked up by every variant that way, so nothing is
  left looking vanilla. The meshes ship at both paths - a few megabytes against a package of 4K
  textures.
* Dawnguard's three Soul Cairn Keeper addons are included, so NPC-worn dragonplate changes too.
* No change to any mesh or texture. A 1.0 install can be updated in place.

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
