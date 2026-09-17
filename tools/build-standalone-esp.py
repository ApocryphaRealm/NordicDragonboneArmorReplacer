#!/usr/bin/env python3
r"""Generate the light plugin that ADDS the Nordic dragon armour as its own set, vanilla untouched.

WHY THIS PLUGIN EXISTS
    ShivaOrion43555 on the Nexus page, 2026-09-17: "by standalone i mean not as a replacer but as an
    additional set". The replacer plugin (build-arma-esl.py) points vanilla's dragon armour ADDON
    records at this mod's meshes, so the vanilla armour itself changes. This one leaves vanilla alone
    and adds ten new pieces - Nordic Dragonplate cuirass, boots, gauntlets, helmet and shield, and the
    same five in Nordic Dragonscale - forged and tempered exactly where the vanilla ones are.

WHERE THE RECORDS COME FROM
    Nothing is typed in from memory. Each new piece is the vanilla ARMO record copied out of
    Skyrim.esm at build time with a new FormID, a new name, its ground model moved to this mod's
    folder and its addon list pointed at copies of the vanilla ARMA records - themselves copied with
    only their model paths moved. So the stats, keywords, slots, races, sounds and body-template
    layout are the game's own, record for record. The forge and tempering recipes are the vanilla
    recipes for the same pieces with the created object swapped and the editor ID renamed; the
    Dragon Armor perk condition comes along unchanged.

    Skyrim.esm is a LOCALIZED master: its FULL and DESC are string-table ids, not text. This plugin
    is not localized, so the names are written here and DESC is emptied.

    ONE MODL SUBRECORD PER ADDON, 4 bytes each, the way vanilla carries them (the logic library,
    2026-09-17: a helmet whose four addons were packed into one 16-byte MODL rendered nothing).

MASTERS
    Skyrim.esm only. Every FormID copied in is checked to resolve there, or to be one of ours.

Usage:  python tools/build-standalone-esp.py [output .esp path]
"""
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))

GAME_DATA = os.environ.get("SKYRIM_DATA", r"D:\modlists\Njordlinger\Stock Game\Data")

PLUGIN_NAME = "Nordic Dragonbone Armor - Standalone.esp"
AUTHOR = "ApocryphaRealm"
DESCRIPTION = "Adds NordwarUA's Nordic dragonplate and dragonscale armour as a separate set; vanilla untouched."

ESL_FLAG = 0x00000200
COMPRESSED = 0x00040000
FIRST_NEW = 0x800

# Vanilla folder -> ours, applied to every model path copied in. Same map as the replacer's.
REPATH = {
    "armor/dragonbone/": "NordicDragonbone/dragonbone/",
    "armor/dragonscale/": "NordicDragonbone/dragonscale/",
}

# (vanilla ARMO editor ID, our editor ID, our display name)
PIECES = [
    ("ArmorDragonplateCuirass", "NordicDragonplateCuirass", "Nordic Dragonplate Armor"),
    ("ArmorDragonplateBoots", "NordicDragonplateBoots", "Nordic Dragonplate Boots"),
    ("ArmorDragonplateGauntlets", "NordicDragonplateGauntlets", "Nordic Dragonplate Gauntlets"),
    ("ArmorDragonplateHelmet", "NordicDragonplateHelmet", "Nordic Dragonplate Helmet"),
    ("ArmorDragonplateShield", "NordicDragonplateShield", "Nordic Dragonplate Shield"),
    ("ArmorDragonscaleCuirass", "NordicDragonscaleCuirass", "Nordic Dragonscale Armor"),
    ("ArmorDragonscaleBoots", "NordicDragonscaleBoots", "Nordic Dragonscale Boots"),
    ("ArmorDragonscaleGauntlets", "NordicDragonscaleGauntlets", "Nordic Dragonscale Gauntlets"),
    ("ArmorDragonscaleHelmet", "NordicDragonscaleHelmet", "Nordic Dragonscale Helmet"),
    ("ArmorDragonscaleShield", "NordicDragonscaleShield", "Nordic Dragonscale Shield"),
]

# FormID-bearing subrecords, so every reference copied in can be checked against the master list.
# "*" = array of FormIDs, 1 = single, "cnto" = FormID then a count.
REFS = {
    "ARMO": {"MODL": "*", "EITM": 1, "ETYP": 1, "BIDS": 1, "BAMT": 1, "KWDA": "*", "RNAM": 1,
             "TNAM": 1, "YNAM": 1, "ZNAM": 1},
    "ARMA": {"RNAM": 1, "MODL": "*", "SNDD": 1, "NAM0": 1, "NAM1": 1, "NAM2": 1, "NAM3": 1},
    "COBJ": {"CNAM": 1, "BNAM": 1, "CNTO": "cnto"},
}
MODEL_SUBS = (b"MOD2", b"MOD3", b"MOD4", b"MOD5")
HASH_SUBS = (b"MO2T", b"MO3T", b"MO4T", b"MO5T", b"MODT")


def fail(msg):
    raise SystemExit("build-standalone-esp: " + msg)


def subrecords(data):
    i = 0
    while i + 6 <= len(data):
        sig = data[i:i+4]
        n = struct.unpack("<H", data[i+4:i+6])[0]
        i += 6
        yield sig, data[i:i+n]
        i += n


def pack(subs):
    out = bytearray()
    for sig, data in subs:
        out += sig + struct.pack("<H", len(data)) + data
    return bytes(out)


class Plugin(object):
    """Every record of the wanted types, by EDID and by FormID, bodies decompressed."""
    def __init__(self, path, types):
        d = open(path, "rb").read()
        self.path = path
        hs = struct.unpack("<I", d[4:8])[0]
        self.masters, i = [], 24
        while i + 6 <= 24 + hs:
            s = d[i:i+4]
            n = struct.unpack("<H", d[i+4:i+6])[0]
            i += 6
            if s == b"MAST":
                self.masters.append(d[i:i+n].split(b"\x00")[0].decode("latin-1"))
            i += n
        self.by_edid, self.by_fid = {}, {}
        types = set(t.encode() for t in types)

        def walk(off, end):
            while off < end:
                t = d[off:off+4]
                n = struct.unpack("<I", d[off+4:off+8])[0]
                if t == b"GRUP":
                    walk(off + 24, off + n)
                    off += n
                    continue
                if t in types:
                    flags = struct.unpack("<I", d[off+8:off+12])[0]
                    fid = struct.unpack("<I", d[off+12:off+16])[0]
                    ver = struct.unpack("<H", d[off+20:off+22])[0]
                    body = d[off+24:off+24+n]
                    if flags & COMPRESSED:
                        body = zlib.decompress(body[4:])
                    subs = list(subrecords(body))
                    edid = next((v.split(b"\x00")[0].decode("latin-1") for s, v in subs if s == b"EDID"), "")
                    rec = {"type": t.decode(), "fid": fid, "ver": ver, "subs": subs, "edid": edid}
                    self.by_fid[fid] = rec
                    if edid:
                        self.by_edid[edid] = rec
                off += 24 + n
        walk(24 + hs, len(d))

    def get(self, edid):
        rec = self.by_edid.get(edid)
        if rec is None:
            fail("%s has no record '%s'" % (os.path.basename(self.path), edid))
        return rec


def repath(value):
    p = value.split(b"\x00")[0].decode("latin-1")
    low = p.replace("\\", "/").lower()
    for old, new in REPATH.items():
        if low.startswith(old):
            return (new + p.replace("\\", "/")[len(old):]).replace("/", "\\")
    fail("model path '%s' is not under a vanilla dragon armour folder - the layout this script "
         "assumes has changed" % p)


def main(out_path=None):
    skyrim = Plugin(os.path.join(GAME_DATA, "Skyrim.esm"), ["ARMO", "ARMA", "COBJ"])
    sky_ix = skyrim.masters + ["Skyrim.esm"]

    masters = ["Skyrim.esm"]
    own = len(masters)
    nxt = FIRST_NEW
    records = []
    new_fid = {}

    def allot(edid):
        nonlocal nxt
        if nxt > 0xFFF:
            fail("more than 2048 new records - not a light plugin any more")
        if edid in new_fid:
            fail("editor ID '%s' allotted twice - two records would share a name and one would "
                 "vanish from the reference check" % edid)
        fid = (own << 24) | nxt
        nxt += 1
        new_fid[edid] = fid
        return fid

    def check_refs(rtype, subs, where):
        for s, v in subs:
            spec = REFS[rtype].get(s.decode("latin-1"))
            if not spec:
                continue
            offs = [0] if spec in (1, "cnto") else list(range(0, len(v) - 3, 4))
            for o in offs:
                fid = struct.unpack_from("<I", v, o)[0]
                if fid in (0, 0xFFFFFFFF):
                    continue
                if (fid >> 24) == own and fid in new_fid.values():
                    continue
                idx = fid >> 24
                if idx >= len(sky_ix) or sky_ix[idx].lower() != "skyrim.esm":
                    fail("%s: %s carries %08X, which is not a Skyrim.esm record" % (where, s.decode(), fid))

    meshes_needed = set()

    # ---- 1. the addons every piece uses, copied once each with the models moved
    arma_new = {}      # vanilla ARMA fid -> our fid
    for van_edid, our_edid, full in PIECES:
        src = skyrim.get(van_edid)
        for s, v in src["subs"]:
            if s != b"MODL":
                continue
            if len(v) != 4:
                fail("%s: a MODL of %d bytes - one addon per subrecord is what vanilla carries" % (van_edid, len(v)))
            van = struct.unpack("<I", v)[0]
            if van in arma_new:
                continue
            addon = skyrim.by_fid.get(van)
            if addon is None or addon["type"] != "ARMA":
                fail("%s points at %08X, which is not an ARMA in Skyrim.esm" % (van_edid, van))
            # Some vanilla addons are named exactly like their armour ("DragonscaleCuirass"), so the
            # copy always carries the AA suffix to stay distinct from the piece's own editor ID.
            base = addon["edid"] or ("Addon%06X" % (van & 0xFFFFFF))
            new_edid = "Nordic" + (base if base.endswith("AA") else base + "AA")
            fid = allot(new_edid)
            arma_new[van] = fid
            subs = []
            for s2, v2 in addon["subs"]:
                if s2 == b"EDID":
                    v2 = new_edid.encode("latin-1") + b"\x00"
                elif s2 in MODEL_SUBS:
                    p = repath(v2)
                    meshes_needed.add(p)
                    v2 = p.encode("latin-1") + b"\x00"
                elif s2 in HASH_SUBS:
                    continue
                subs.append((s2, v2))
            check_refs("ARMA", subs, new_edid)
            records.append(("ARMA", fid, addon["ver"], subs))

    # ---- 2. the pieces: vanilla bodies renamed, ground model moved, addon list pointed at ours
    armo_new = {}      # vanilla ARMO fid -> our fid
    for van_edid, our_edid, full in PIECES:
        src = skyrim.get(van_edid)
        fid = allot(our_edid)
        armo_new[src["fid"]] = fid
        subs = []
        for s, v in src["subs"]:
            if s == b"EDID":
                v = our_edid.encode("latin-1") + b"\x00"
            elif s == b"FULL":
                v = full.encode("latin-1") + b"\x00"
            elif s == b"DESC":
                v = b"\x00"
            elif s in (b"MOD2", b"MOD4"):
                p = repath(v)
                meshes_needed.add(p)
                v = p.encode("latin-1") + b"\x00"
            elif s in HASH_SUBS:
                continue
            elif s == b"MODL":
                v = struct.pack("<I", arma_new[struct.unpack("<I", v)[0]])
            subs.append((s, v))
        if not any(s == b"MODL" for s, v in subs):
            fail("%s has no MODL - nothing to point at our addons" % van_edid)
        check_refs("ARMO", subs, our_edid)
        records.append(("ARMO", fid, src["ver"], subs))

    # ---- 3. recipes: every vanilla COBJ that creates one of the pieces, created object swapped
    n_forge = n_temper = 0
    for rec in sorted(skyrim.by_fid.values(), key=lambda r: r["fid"]):
        if rec["type"] != "COBJ":
            continue
        cnam = next((struct.unpack("<I", v)[0] for s, v in rec["subs"] if s == b"CNAM"), None)
        if cnam not in armo_new:
            continue
        edid = rec["edid"] or ("Recipe%06X" % (rec["fid"] & 0xFFFFFF))
        new_edid = "Nordic" + edid
        fid = allot(new_edid)
        subs = []
        for s, v in rec["subs"]:
            if s == b"EDID":
                v = new_edid.encode("latin-1") + b"\x00"
            elif s == b"CNAM":
                v = struct.pack("<I", armo_new[cnam])
            subs.append((s, v))
        check_refs("COBJ", subs, new_edid)
        records.append(("COBJ", fid, rec["ver"], subs))
        if edid.lower().startswith("temper"):
            n_temper += 1
        else:
            n_forge += 1
    if n_forge != len(PIECES) or n_temper != len(PIECES):
        fail("expected %d forge and %d tempering recipes, found %d and %d - a piece would be "
             "uncraftable or untemperable" % (len(PIECES), len(PIECES), n_forge, n_temper))

    # ---- emit, one group per type
    order = ["ARMA", "ARMO", "COBJ"]
    groups = bytearray()
    counts = {}
    for rtype in order:
        payload = bytearray()
        for t, fid, ver, subs in sorted((r for r in records if r[0] == rtype), key=lambda r: r[1]):
            body = pack(subs)
            payload += (t.encode("latin-1") + struct.pack("<IIIIHH", len(body), 0, fid, 0, ver, 0) + body)
            counts[rtype] = counts.get(rtype, 0) + 1
        groups += (b"GRUP" + struct.pack("<I", len(payload) + 24) + rtype.encode("latin-1")
                   + struct.pack("<iii", 0, 0, 0) + payload)

    head = bytearray()
    head += b"HEDR" + struct.pack("<H", 12) + struct.pack("<fiI", 1.7, len(records), nxt)
    head += b"CNAM" + struct.pack("<H", len(AUTHOR) + 1) + AUTHOR.encode("latin-1") + b"\x00"
    head += b"SNAM" + struct.pack("<H", len(DESCRIPTION) + 1) + DESCRIPTION.encode("latin-1") + b"\x00"
    for m in masters:
        head += b"MAST" + struct.pack("<H", len(m) + 1) + m.encode("latin-1") + b"\x00"
        head += b"DATA" + struct.pack("<H", 8) + struct.pack("<Q", 0)
    tes4 = b"TES4" + struct.pack("<IIIIHH", len(head), ESL_FLAG, 0, 0, 44, 0) + bytes(head)

    out = out_path or os.path.join(REPO, "plugin", PLUGIN_NAME)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    open(out, "wb").write(tes4 + bytes(groups))

    with open(os.path.join(REPO, "plugin", "standalone-meshes-needed.txt"), "w", encoding="utf-8") as f:
        for m in sorted(meshes_needed):
            f.write(m + "\n")

    print("wrote %s" % out)
    print("  masters ............... %s" % ", ".join(masters))
    print("  records ............... %s" % ", ".join("%s %d" % (k, counts[k]) for k in order))
    print("  pieces ................ %d, addons %d, recipes %d forge + %d temper" % (len(PIECES), len(arma_new), n_forge, n_temper))
    print("  new FormIDs ........... 0x%06X-0x%06X" % (FIRST_NEW, nxt - 1))
    print("  meshes the package owes  %d (plugin/standalone-meshes-needed.txt)" % len(meshes_needed))
    print("  light flag ............ set")
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
