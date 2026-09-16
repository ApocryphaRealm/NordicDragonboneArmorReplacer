#!/usr/bin/env python3
r"""Assemble the FOMOD installer for Nordic Dragonbone Armor Replacer.

WHAT THIS PACKAGES
    The dragonbone (dragonplate) and dragonscale armour from Simply Realistic Armor and Weapons
    (Custom NordwarUA Edition), Nexus 47184, offered as a choice between the author's Standard
    finish and his Black Edition. Meshes, textures, nothing else - there is no plugin anywhere in
    this mod, so there is no ESP and nothing to flag as light.

WHY IT READS ARCHIVES INSTEAD OF SHIPPING FILES
    None of the art is ours. The repository therefore carries NONE of it: this script opens the
    two Nexus downloads at build time and takes only the dragon paths out of them. Clone the repo
    and you get the packaging logic; you still have to fetch the mod from its own page, which is
    where the author wants you.

WHAT IT REFUSES TO DO
    * ship if either download is missing, or has no dragon content in it;
    * ship if the two finishes' textures come out byte-identical, which would mean one archive was
      downloaded twice and the installer's question would be a lie;
    * ship if the meshes differ between the two archives - the installer installs ONE shared copy
      of them on the strength of that identity, so if it ever stops holding, the layout is wrong;
    * ship if a vanilla dragon-armour mesh path is left uncovered, which is how a replacer ends up
      showing half-new armour;
    * ship if any folder ModuleConfig.xml installs from came out missing or empty;
    * ship if an installer image the XML points at is not there.

Usage:  python tools/build-fomod.py [output folder]
        Default output is "<repo>/../../7. current test builds/Nordic Dragonbone Armor Replacer <ver>".
"""
import hashlib
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))

# Where the owner's Nexus downloads land. Overridable so a fresh machine can point elsewhere.
DOWNLOADS = os.environ.get("NDAR_DOWNLOADS", r"D:\modlists\Njordlinger\downloads")

SEVENZIP = [r"C:\Program Files\7-Zip\7z.exe", r"C:\Program Files (x86)\7-Zip\7z.exe", "7z"]

# (archive name fragment, the folder it becomes in the installer, what to call it in a message).
# The Standard finish is not a separate download - it is the dragon armour as it ships inside the
# main SRA archive, which is why that one is a gigabyte and this script only wants 90 MB of it.
SOURCES = [
    ("Simply Realistic Armor (NordwarUA Edition)-47184-1-2", "01 Textures - Standard", "Standard"),
    ("Dragonscale and Dragonbone Armor 1.2 (Black Edition)-47184-1-2", "02 Textures - Black", "Black Edition"),
]

# Only these paths are taken out of the archives. Everything else in the main archive is the rest
# of SRA, which is not ours to repackage and not what this mod is.
WANTED = ("meshes/armor/dragonbone/", "meshes/armor/dragonscale/",
          "textures/armor_replacer/dragonplate/", "textures/armor_replacer/dragonscale/",
          "textures/cubemaps/")

# Shipped by the Black Edition, referenced by no mesh in either finish - 28 MB of alternates the
# author left in the archive. Confirmed unreferenced by reading every .nif; see NOTICE.md.
UNREFERENCED = ("dragonplate_alt_silver_mail.dds", "lamellarnordhelm2.dds")

IMAGES = ("header.png", "standard.png", "black.png")


def fail(msg):
    raise SystemExit("build-fomod: " + msg)


def sevenzip():
    for cand in SEVENZIP:
        if os.path.isfile(cand):
            return cand
        if shutil.which(cand):
            return shutil.which(cand)
    fail("7-Zip not found - install it, or put 7z on PATH")


def version():
    """Read the version from fomod/info.xml - the one place version-gate.ps1 stamps for this mod.

    There is no CMake here (no code), so the installer's own info file is the version location the
    gate discovered and now owns. Never type a number into it by hand; use
    `version-gate.ps1 -Action bump -Mod ApocryphaNordicDragonboneArmorReplacer`.
    """
    text = open(os.path.join(REPO, "fomod", "info.xml"), encoding="utf-8").read()
    m = re.search(r"<Version>\s*(\d+\.\d+\.\d+)\s*</Version>", text)
    if not m:
        fail("no <Version>x.y.z</Version> in fomod/info.xml - the version location has moved")
    return m.group(1)


def extract(archive, dest):
    """Pull only the dragon paths out of one archive, flattened to a lowercase layout."""
    os.makedirs(dest, exist_ok=True)
    args = [sevenzip(), "x", "-y", "-o" + dest, archive]
    # The cubemaps are named one by one on purpose. The main SRA archive carries 72 of them for the
    # whole armour set; only these two belong to the dragon armour, and they are exactly the two the
    # Black Edition archive ships. Taking the folder wholesale quietly dragged in the other 70.
    args += ["meshes\\armor\\dragonbone\\*", "meshes\\armor\\dragonscale\\*",
             "textures\\armor_replacer\\dragonplate\\*", "textures\\armor_replacer\\dragonscale\\*",
             "textures\\cubemaps\\dragonplate.dds", "textures\\cubemaps\\dragonscale.dds"]
    args += ["-r"]
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode != 0:
        fail("7-Zip failed on %s:\n%s" % (os.path.basename(archive), p.stdout + p.stderr))


def snapshot(root, prefix=""):
    """{relative lowercase path: sha1} for everything under root/prefix."""
    out = {}
    base = os.path.join(root, prefix) if prefix else root
    for dp, _, fns in os.walk(base):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, root).replace("\\", "/").lower()
            out[rel] = hashlib.sha1(open(p, "rb").read()).hexdigest()
    return out


def copy_tree(src, dest, skip=()):
    n = 0
    for dp, _, fns in os.walk(src):
        for fn in fns:
            if fn.lower() in skip:
                continue
            s = os.path.join(dp, fn)
            rel = os.path.relpath(s, src)
            d = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    return n


def find_archive(fragment):
    for fn in os.listdir(DOWNLOADS):
        if fragment.lower() in fn.lower() and fn.lower().endswith(".7z"):
            return os.path.join(DOWNLOADS, fn)
    fail("no archive matching '%s' in %s - download it from Nexus 47184 first" % (fragment, DOWNLOADS))


def required_mesh_paths():
    """The vanilla mesh paths the replacer has to cover, as recorded when the mod was built.

    These came from reading every dragon ARMA record in Skyrim.esm. They are written down rather
    than re-read from the game so the check works on a machine with no Skyrim installed.
    """
    p = os.path.join(REPO, "docs", "vanilla-dragon-mesh-paths.txt")
    return [l.strip().lower() for l in open(p, encoding="utf-8") if l.strip() and not l.startswith("#")]


def main(out_root=None):
    ver = version()
    if out_root is None:
        out_root = os.path.normpath(os.path.join(
            REPO, "..", "..", "7. current test builds",
            "Nordic Dragonbone Armor Replacer %s" % ver))
    work = os.path.join(out_root, "_work")
    if os.path.isdir(out_root):
        shutil.rmtree(out_root)

    # ---- extract both archives before anything is assembled
    staged = {}
    for fragment, folder, label in SOURCES:
        archive = find_archive(fragment)
        dest = os.path.join(work, folder)
        extract(archive, dest)
        files = snapshot(dest)
        if not any(f.startswith("meshes/") for f in files):
            fail("'%s' (%s) came out with no dragon meshes - wrong archive, or its layout changed"
                 % (os.path.basename(archive), label))
        staged[folder] = (dest, files, label, os.path.basename(archive))

    (std_dir, std, _, std_name), (blk_dir, blk, _, blk_name) = \
        staged["01 Textures - Standard"], staged["02 Textures - Black"]

    # ---- the two claims the installer's layout rests on
    std_meshes = {k: v for k, v in std.items() if k.startswith("meshes/")}
    blk_meshes = {k: v for k, v in blk.items() if k.startswith("meshes/")}
    if std_meshes != blk_meshes:
        differing = sorted(set(std_meshes) ^ set(blk_meshes)) or \
            sorted(k for k in std_meshes if std_meshes[k] != blk_meshes.get(k))
        fail("the two finishes no longer share their meshes (%d differ, e.g. %s) - the installer "
             "ships ONE copy of them, so the package layout has to change before this can go out"
             % (len(differing), differing[0]))

    std_tex = {k: v for k, v in std.items() if k.startswith("textures/")}
    blk_tex = {k: v for k, v in blk.items() if k.startswith("textures/")}
    if std_tex == blk_tex:
        fail("the two finishes' textures are byte-identical - the same archive has been downloaded "
             "twice, and the installer would offer a choice that makes no difference\n  %s\n  %s"
             % (std_name, blk_name))

    # ---- every vanilla path covered, or a player sees half-new armour
    have = set(std_meshes)
    missing = []
    for want in required_mesh_paths():
        cands = [want] + ([want[:-6] + "_0.nif"] if want.endswith("_1.nif") else [])
        missing += [c for c in cands if "meshes/" + c not in have]
    if missing:
        fail("%d vanilla dragon-armour mesh paths are not covered, starting with %s - a player "
             "would see the new armour on some pieces and the old on others" % (len(missing), missing[0]))

    # ---- assemble
    # Core takes the meshes AND every texture that is the same in both finishes - 4K DDS files are
    # tens of megabytes each, and shipping the shared ones twice doubles the download for nothing.
    # Only the textures that actually differ go in the two choice folders.
    core = os.path.join(out_root, "00 Core")
    n_meshes = copy_tree(os.path.join(std_dir, "meshes"), os.path.join(core, "meshes"))

    shared = {k for k in set(std_tex) & set(blk_tex) if std_tex[k] == blk_tex[k]}
    n_core_tex = 0
    for rel in sorted(shared):
        s = os.path.join(std_dir, rel.replace("/", os.sep))
        d = os.path.join(core, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(s, d)
        n_core_tex += 1

    n_tex = {}
    for folder in ("01 Textures - Standard", "02 Textures - Black"):
        src_root = staged[folder][0]
        rels = [k for k in staged[folder][1]
                if k.startswith("textures/") and k not in shared
                and os.path.basename(k) not in UNREFERENCED]
        for rel in sorted(rels):
            s = os.path.join(src_root, rel.replace("/", os.sep))
            d = os.path.join(out_root, folder, rel.replace("/", os.sep))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
        n_tex[folder] = len(rels)

    # ---- fomod
    fomod = os.path.join(out_root, "fomod")
    os.makedirs(os.path.join(fomod, "images"), exist_ok=True)
    shutil.copy2(os.path.join(REPO, "fomod", "ModuleConfig.xml"), fomod)
    for img in IMAGES:
        src = os.path.join(REPO, "fomod", "images", img)
        if not os.path.isfile(src):
            fail("installer image '%s' is missing - the FOMOD is supposed to show the player what "
                 "he is choosing between" % img)
        shutil.copy2(src, os.path.join(fomod, "images", img))
    shutil.copy2(os.path.join(REPO, "fomod", "info.xml"), fomod)

    # ---- documents
    for name in ("NOTICE.md", "CHANGELOG.md", "LICENSE"):
        shutil.copy2(os.path.join(REPO, name), os.path.join(out_root, name))

    # ---- and the check that catches a packaging mistake rather than a source one
    root = ET.parse(os.path.join(fomod, "ModuleConfig.xml")).getroot()
    sources = sorted({e.get("source") for e in root.iter("folder") if e.get("source")})
    for s in sources:
        p = os.path.join(out_root, s.replace("\\", os.sep).replace("/", os.sep))
        if not os.path.isdir(p) or not any(
                os.path.isfile(os.path.join(dp, f)) for dp, _, fs in os.walk(p) for f in fs):
            fail("ModuleConfig.xml installs from '%s', but the package has nothing there" % s)
    for e in list(root.iter("image")) + list(root.iter("moduleImage")):
        rel = e.get("path").replace("\\", os.sep).replace("/", os.sep)
        if not os.path.isfile(os.path.join(out_root, rel)):
            fail("ModuleConfig.xml shows '%s', which is not in the package" % e.get("path"))

    shutil.rmtree(work)
    total = sum(len(fs) for _, _, fs in os.walk(out_root))
    print("built %s" % out_root)
    print("  version ............... %s" % ver)
    print("  shared meshes ......... %d" % n_meshes)
    print("  shared textures ....... %d (in Core, not duplicated)" % n_core_tex)
    print("  Standard-only ......... %d" % n_tex["01 Textures - Standard"])
    print("  Black-only ............ %d" % n_tex["02 Textures - Black"])
    print("  dropped as unused ..... %s" % ", ".join(UNREFERENCED))
    print("  installer sources ..... %d, every one present" % len(sources))
    print("  files ................. %d" % total)
    return out_root


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
