#!/usr/bin/env python3
r"""Generate the light plugin that points vanilla's armour ADDON records at this mod's meshes.

WHY AN ADDON-ONLY PLUGIN
    A vanilla armour piece exists many times over: the base item plus roughly a hundred
    pre-enchanted variants, each its own ARMO record. None of them carries the worn model path -
    they all reach it through a shared ARMA (armour addon) record. So repointing a handful of ARMA
    records changes every variant at once, where repointing the ARMO records would mean overriding
    hundreds of them and colliding with anything that touches this armour's stats.

    The owner chose this scope deliberately on 2026-09-16, having been shown both counts.

WHAT THAT LEAVES ON FILE REPLACEMENT
    Ground models (the item on the floor) and weapons have no addon record - each ARMO or WEAP
    names its own mesh - so those meshes stay at their vanilla paths and are picked up by every
    variant that way. Nothing ends up looking vanilla; the two halves are simply governed in
    different places, load order for the worn armour and mod priority for the rest.

MASTERS, AND WHY THERE IS NO FORMID TRANSLATION
    The master list is the standard Bethesda one, truncated to the shortest prefix that covers
    every index actually used: Skyrim, Update, Dawnguard, HearthFires, Dragonborn. In that order
    every one of those plugins sits at the same index it occupies in its own master table, so a
    record copied out of any of them keeps its FormIDs unchanged - and so do the references inside
    it. The script asserts that invariant rather than trusting it.

Usage:  python tools/build-arma-esl.py [output .esl path]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))

GAME_DATA = os.environ.get("SKYRIM_DATA", r"D:\modlists\Njordlinger\Stock Game\Data")
DLC_DIR = os.environ.get("SKYRIM_DLC", r"D:\modlists\Njordlinger\mods\Base Game DLC Content")

# The standard load order. Index i here is the index that plugin occupies in every later plugin's
# master table, which is what makes the no-translation invariant hold.
STANDARD = ["Skyrim.esm", "Update.esm", "Dawnguard.esm", "HearthFires.esm", "Dragonborn.esm"]

PLUGIN_NAME = "Nordic Dragonbone Armor Replacer.esp"
AUTHOR = "ApocryphaRealm"
DESCRIPTION = "Points vanilla's dragon armour addons at this mod's meshes."

# Vanilla directory -> ours. Only the worn meshes move; everything else keeps its vanilla path.
REPATH = {
    "armor/dragonbone/": "NordicDragonbone/dragonbone/",
    "armor/dragonscale/": "NordicDragonbone/dragonscale/",
}

ESL_FLAG = 0x00000200
COMPRESSED = 0x00040000
MODEL_SUBS = (b"MOD2", b"MOD3", b"MOD4", b"MOD5")


def fail(msg):
    raise SystemExit("build-arma-esl: " + msg)


def subrecords(data):
    i = 0
    while i + 6 <= len(data):
        sig = data[i:i+4]
        size = struct.unpack("<H", data[i+4:i+6])[0]
        i += 6
        yield sig, data[i:i+size]
        i += size


def plugin_path(name):
    for root in (GAME_DATA, DLC_DIR):
        p = os.path.join(root, name)
        if os.path.isfile(p):
            return p
    return None


def read_arma(path):
    """Every ARMA record in one plugin, as {formid: (raw body, master count)}."""
    import zlib
    d = open(path, "rb").read()
    hs = struct.unpack("<I", d[4:8])[0]
    masters, i = [], 24
    while i + 6 <= 24 + hs:
        s = d[i:i+4]
        n = struct.unpack("<H", d[i+4:i+6])[0]
        i += 6
        if s == b"MAST":
            masters.append(d[i:i+n].split(b"\x00")[0].decode("latin-1"))
        i += n
    out = {}

    def walk(off, end):
        while off < end:
            t = d[off:off+4]
            n = struct.unpack("<I", d[off+4:off+8])[0]
            if t == b"GRUP":
                walk(off + 24, off + n)
                off += n
                continue
            flags = struct.unpack("<I", d[off+8:off+12])[0]
            fid = struct.unpack("<I", d[off+12:off+16])[0]
            vcs = struct.unpack("<I", d[off+16:off+20])[0]
            ver = struct.unpack("<H", d[off+20:off+22])[0]
            body = d[off+24:off+24+n]
            off += 24 + n
            if t != b"ARMA":
                continue
            if flags & COMPRESSED:
                try:
                    body = zlib.decompress(body[4:])
                except Exception:
                    continue
            out[fid] = (body, masters, vcs, ver)
    walk(24 + hs, len(d))
    return out


def model_paths(body):
    paths = {}
    for sig, data in subrecords(body):
        if sig in MODEL_SUBS:
            v = data.split(b"\x00")[0].decode("latin-1")
            if v.lower().endswith(".nif"):
                paths[sig] = v
    return paths


def repath(value):
    low = value.replace("\\", "/").lower()
    for old, new in REPATH.items():
        if low.startswith(old):
            return (new + value.replace("\\", "/")[len(old):]).replace("/", "\\")
    return None


def rebuild(body, remapped):
    """Rewrite the model subrecords in place, leaving every other byte exactly as it was."""
    out = bytearray()
    for sig, data in subrecords(body):
        if sig in remapped:
            new = remapped[sig].encode("latin-1") + b"\x00"
            out += sig + struct.pack("<H", len(new)) + new
        else:
            out += sig + struct.pack("<H", len(data)) + data
    return bytes(out)


def main(out_path=None):
    # ---- collect the winning version of every ARMA whose models we are moving
    winners = {}
    for idx, name in enumerate(STANDARD):
        p = plugin_path(name)
        if p is None:
            continue
        for fid, (body, masters, vcs, ver) in read_arma(p).items():
            if any(repath(v) for v in model_paths(body).values()):
                winners[fid] = (body, name, idx, masters, vcs, ver)
    if not winners:
        fail("no vanilla ARMA record points at %s - the game data is not where this script thinks"
             % ", ".join(REPATH))

    # ---- the shortest master list that keeps every index meaning the same thing
    highest = 0
    for fid, (body, name, idx, masters, vcs, ver) in winners.items():
        owner_idx = fid >> 24
        highest = max(highest, owner_idx)
        for sig, data in subrecords(body):
            if sig in (b"RNAM", b"SNDD", b"MODL", b"NAM0", b"NAM1", b"NAM2", b"NAM3"):
                for off in range(0, len(data) - 3, 4):
                    v = struct.unpack_from("<I", data, off)[0]
                    if v and v != 0xFFFFFFFF:
                        highest = max(highest, v >> 24)
    if highest >= len(STANDARD):
        fail("a record or reference uses master index %d, beyond the standard five - this script's "
             "no-translation assumption does not hold and the plugin would be wrong" % highest)
    masters_out = STANDARD[:highest + 1]

    # ---- the invariant, asserted rather than assumed
    for fid, (body, name, idx, src_masters, vcs, ver) in winners.items():
        owner = src_masters[fid >> 24] if (fid >> 24) < len(src_masters) else name
        if masters_out[fid >> 24].lower() != owner.lower():
            fail("index %d means '%s' in %s but '%s' here - FormIDs would silently point at the "
                 "wrong file" % (fid >> 24, owner, name, masters_out[fid >> 24]))

    # ---- rewrite and emit
    records = bytearray()
    moved = 0
    report = []
    for fid in sorted(winners):
        body, name, idx, _, vcs, ver = winners[fid]
        remapped = {}
        for sig, value in model_paths(body).items():
            new = repath(value)
            if new:
                remapped[sig] = new
                moved += 1
        new_body = rebuild(body, remapped)
        # Carry the record's OWN form version through. Stamping a fixed 44 told the engine to
        # expect the newer 8-byte BOD2 where these records actually carry a 12-byte BODT, so every
        # subrecord after it shifted and the game died resolving the model path. These records are
        # form version 39-40. The timestamp/VCS word is preserved for the same reason: copy the
        # header, change only what has to change.
        records += (b"ARMA" + struct.pack("<IIIIHH", len(new_body), 0, fid, vcs, ver, 0) + new_body)
        report.append((fid, name, len(remapped)))

    grup = b"GRUP" + struct.pack("<I", len(records) + 24) + b"ARMA" + struct.pack("<iii", 0, 0, 0) + records

    body = b""
    body += b"HEDR" + struct.pack("<H", 12) + struct.pack("<fiI", 1.7, len(report), 0x800)
    body += b"CNAM" + struct.pack("<H", len(AUTHOR) + 1) + AUTHOR.encode("latin-1") + b"\x00"
    body += b"SNAM" + struct.pack("<H", len(DESCRIPTION) + 1) + DESCRIPTION.encode("latin-1") + b"\x00"
    for m in masters_out:
        body += b"MAST" + struct.pack("<H", len(m) + 1) + m.encode("latin-1") + b"\x00"
        body += b"DATA" + struct.pack("<H", 8) + struct.pack("<Q", 0)
    header = b"TES4" + struct.pack("<IIIII", len(body), ESL_FLAG, 0, 0, 44) + body

    if out_path is None:
        out_path = os.path.join(REPO, "plugin", PLUGIN_NAME)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(header + grup)

    print("wrote %s" % out_path)
    print("  masters ............... %s" % ", ".join(masters_out))
    print("  addon records ......... %d" % len(report))
    print("  model paths moved ..... %d" % moved)
    for fid, name, n in report:
        print("      %08X  %-14s %d path(s)" % (fid, name, n))
    return out_path


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
