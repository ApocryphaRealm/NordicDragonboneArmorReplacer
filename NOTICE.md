# Whose work this is

**Almost none of this mod is ours.** It is a packaging job: the art belongs to the authors of
Simply Realistic Armor, and what we added is an installer that asks the player one question.

---

## The art - Simply Realistic Armor and Weapons (Custom NordwarUA Edition)

[Nexus 47184](https://www.nexusmods.com/skyrimspecialedition/mods/47184), by **QuestionableKhajiit
and NordWarUA**.

Every mesh and every texture this mod installs comes out of two downloads from that page:

| Download | File ID | What this mod takes from it |
|---|---|---|
| Simply Realistic Armor (NordwarUA Edition) 1.2 | 199602 | the dragon armour meshes, and the Standard textures |
| Simply Realistic Armor - Dragonscale and Dragonbone Armor 1.2 (Black Edition) | 199607 | the Black Edition textures |

Nothing was remodelled, retextured, refitted or resaved. The files are theirs, byte for byte.

**The repository carries none of them.** `tools/build-fomod.py` opens those two archives at build
time and takes only the dragon paths out of them, so cloning this repo gives you the packaging
logic and still sends you to the authors' own page for the art.

**Permissions.** Per the owner's standing policy for our asset mods, set 2026-09-16 - *"for any of
the permissions on this mod and the last few equipment related mods just add links back to the
original mods and the credit section of each mod"* - the mod page names both authors and links back
to Nexus 47184. The permissions block on that page cannot be read from this machine, since Nexus
returns 403 to anything that is not a browser.

## What IS ours

`tools/build-fomod.py`, `fomod/ModuleConfig.xml`, the installer images and the documentation.
Those are GPL-3.0-or-later, Copyright (C) 2026 ApocryphaRealm. They are packaging, not art.

---

## Two decisions worth writing down

**The meshes are shared, not duplicated.** The two downloads ship byte-identical meshes - all 65 of
them - and differ only in 14 textures plus two extras. So the installer lays down one copy of the
meshes for everybody and the finish chooses textures. The build script hashes both sets and refuses
to package if that identity ever stops holding, because the whole layout rests on it.

**Two textures are left out.** The Black Edition ships `dragonplate_alt_silver_mail.dds` (22 MB)
and `lamellarnordhelm2.dds` (5 MB) which no mesh in either finish references - checked by reading
every `.nif` in the package for the file names. They are alternates the author left in the archive.
Shipping them would add 28 MB of files the game never opens. Anyone who wants them has the original
download.

## The game side, checked rather than assumed

Vanilla's dragon armour is reached through 31 distinct mesh paths, counting both body weights, the
first-person meshes, the ground models and the Orc, Khajiit and Argonian helmet variants. All 31
are covered here; nothing falls back to the vanilla BSA and no piece can appear half-new. The list
is in `docs/vanilla-dragon-mesh-paths.txt`, read out of `Skyrim.esm`'s ARMA records, and the build
script checks the package against it.

Dawnguard adds three further records - `ArmorDragonplateBoots`, `Cuirass` and `GauntletsUnplayable`
- which are NPC-only copies. They point at the same meshes, so they change with everything else.

**There is no plugin in this mod at all.** No ESP, no ESL, no BSA: meshes and textures only. It
costs no load-order slot and there is nothing in it to convert.
