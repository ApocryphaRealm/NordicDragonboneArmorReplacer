#!/usr/bin/env python3
r"""Check the standalone plugin against the game's own records before it is ever loaded.

Every record in it was copied from Skyrim.esm with a handful of intended edits. This re-reads the
plugin and insists on exactly those edits and nothing else:

  * the header is light-flagged, form version 44, and masters Skyrim.esm alone;
  * every ARMO is a vanilla dragon piece renamed, with its ground model under NordicDragonbone\
    and ONE 4-byte MODL per addon, every one resolving to an ARMA in this plugin;
  * every ARMA is a vanilla dragon addon with only its model paths moved;
  * every COBJ is a vanilla recipe with only CNAM (the created object) and EDID changed, and each
    piece has one forge and one tempering recipe;
  * every FormID the plugin carries resolves in Skyrim.esm or in the plugin itself;
  * each record keeps the form version of the record it was copied from;
  * with a built package folder given, every mesh the plugin names is under 00 Core.

Usage:  python tools/verify-standalone-esp.py [built package folder]
"""
import os
import struct
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
spec = importlib.util.spec_from_file_location("gen", os.path.join(HERE, "build-standalone-esp.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def fail(msg):
    raise SystemExit("verify-standalone-esp: " + msg)


def main(pkg=None):
    esp = os.path.join(REPO, "plugin", gen.PLUGIN_NAME)
    if not os.path.isfile(esp):
        fail("no plugin at %s - run build-standalone-esp.py" % esp)
    d = open(esp, "rb").read()
    flags = struct.unpack("<I", d[8:12])[0]
    ver = struct.unpack("<H", d[20:22])[0]
    if not flags & gen.ESL_FLAG:
        fail("the plugin is not flagged light; it would take a full load order slot")
    if ver != 44:
        fail("header form version is %d, not 44" % ver)
    ours = gen.Plugin(esp, ["ARMO", "ARMA", "COBJ"])
    if ours.masters != ["Skyrim.esm"]:
        fail("masters are %s, not Skyrim.esm alone" % ours.masters)
    skyrim = gen.Plugin(os.path.join(gen.GAME_DATA, "Skyrim.esm"), ["ARMO", "ARMA", "COBJ"])

    own_fids = set(ours.by_fid)
    def resolves(fid):
        return fid in (0, 0xFFFFFFFF) or fid in own_fids or (fid >> 24 == 0 and fid in skyrim.by_fid) or (fid >> 24 == 0)

    def sub(rec, sig):
        return [v for s, v in rec["subs"] if s == sig]

    # ---- ARMO
    pieces = {our: (van, full) for van, our, full in gen.PIECES}
    armos = [r for r in ours.by_fid.values() if r["type"] == "ARMO"]
    if sorted(r["edid"] for r in armos) != sorted(pieces):
        fail("ARMO set is %s, expected the %d pieces" % (sorted(r["edid"] for r in armos), len(pieces)))
    meshes = set()
    for r in armos:
        van, full = pieces[r["edid"]]
        src = skyrim.get(van)
        if r["ver"] != src["ver"]:
            fail("%s: form version %d, the game's %s is %d" % (r["edid"], r["ver"], van, src["ver"]))
        if sub(r, b"FULL") != [full.encode("latin-1") + b"\x00"]:
            fail("%s: FULL is not '%s'" % (r["edid"], full))
        modls = sub(r, b"MODL")
        if not modls or any(len(m) != 4 for m in modls):
            fail("%s: MODL must be one 4-byte subrecord per addon; got sizes %s" % (r["edid"], [len(m) for m in modls]))
        if len(modls) != len(sub(src, b"MODL")):
            fail("%s: %d addons, the game's %s has %d" % (r["edid"], len(modls), van, len(sub(src, b"MODL"))))
        for m in modls:
            fid = struct.unpack("<I", m)[0]
            if fid not in own_fids or ours.by_fid[fid]["type"] != "ARMA":
                fail("%s: addon %08X is not an ARMA in this plugin" % (r["edid"], fid))
        for sig in (b"MOD2", b"MOD4"):
            for v in sub(r, sig):
                p = v.split(b"\x00")[0].decode("latin-1")
                if not p.lower().startswith("nordicdragonbone\\"):
                    fail("%s: %s '%s' is not under NordicDragonbone\\" % (r["edid"], sig.decode(), p))
                meshes.add(p)
        # everything else byte-identical to vanilla, in order, skipping the intended edits
        ours_rest = [(s, v) for s, v in r["subs"] if s not in (b"EDID", b"FULL", b"DESC", b"MOD2", b"MOD4", b"MODL")]
        van_rest = [(s, v) for s, v in src["subs"] if s not in (b"EDID", b"FULL", b"DESC", b"MOD2", b"MOD4", b"MODL") and s not in gen.HASH_SUBS]
        if ours_rest != van_rest:
            fail("%s: a subrecord other than the intended ones differs from the game's %s" % (r["edid"], van))
        for s, v in r["subs"]:
            spec_ = gen.REFS["ARMO"].get(s.decode("latin-1"))
            if spec_:
                for o in ([0] if spec_ == 1 else range(0, len(v) - 3, 4)):
                    if not resolves(struct.unpack_from("<I", v, o)[0]):
                        fail("%s: %s does not resolve" % (r["edid"], s.decode()))

    # ---- ARMA
    armas = [r for r in ours.by_fid.values() if r["type"] == "ARMA"]
    for r in armas:
        van_edid = r["edid"][len("Nordic"):]
        src = skyrim.by_edid.get(van_edid) or skyrim.by_edid.get(van_edid[:-2])
        if src is None or src["type"] != "ARMA":
            fail("%s: no vanilla addon it was copied from" % r["edid"])
        if r["ver"] != src["ver"]:
            fail("%s: form version %d, the game's is %d" % (r["edid"], r["ver"], src["ver"]))
        ours_rest = [(s, v) for s, v in r["subs"] if s != b"EDID" and s not in gen.MODEL_SUBS]
        van_rest = [(s, v) for s, v in src["subs"] if s != b"EDID" and s not in gen.MODEL_SUBS and s not in gen.HASH_SUBS]
        if ours_rest != van_rest:
            fail("%s: a subrecord other than a model path differs from the game's %s" % (r["edid"], van_edid))
        for s, v in r["subs"]:
            if s in gen.MODEL_SUBS:
                p = v.split(b"\x00")[0].decode("latin-1")
                if not p.lower().startswith("nordicdragonbone\\"):
                    fail("%s: %s '%s' is not under NordicDragonbone\\" % (r["edid"], s.decode(), p))
                meshes.add(p)
    referenced = {struct.unpack("<I", m)[0] for r in armos for m in sub(r, b"MODL")}
    if referenced != {r["fid"] for r in armas}:
        fail("the ARMA set and the addons the pieces reference differ")

    # ---- COBJ
    armo_by_fid = {r["fid"]: r for r in armos}
    forge, temper = {}, {}
    for r in ours.by_fid.values():
        if r["type"] != "COBJ":
            continue
        van_edid = r["edid"][len("Nordic"):]
        src = skyrim.by_edid.get(van_edid)
        if src is None or src["type"] != "COBJ":
            fail("%s: no vanilla recipe it was copied from" % r["edid"])
        if r["ver"] != src["ver"]:
            fail("%s: form version differs from the game's" % r["edid"])
        ours_rest = [(s, v) for s, v in r["subs"] if s not in (b"EDID", b"CNAM")]
        van_rest = [(s, v) for s, v in src["subs"] if s not in (b"EDID", b"CNAM")]
        if ours_rest != van_rest:
            fail("%s: something other than EDID/CNAM differs from the game's %s" % (r["edid"], van_edid))
        cnam = struct.unpack("<I", sub(r, b"CNAM")[0])[0]
        if cnam not in armo_by_fid:
            fail("%s: creates %08X, which is not one of our pieces" % (r["edid"], cnam))
        (temper if van_edid.lower().startswith("temper") else forge).setdefault(cnam, []).append(r["edid"])
    for fid, r in armo_by_fid.items():
        if len(forge.get(fid, [])) != 1 or len(temper.get(fid, [])) != 1:
            fail("%s: %d forge / %d tempering recipes, expected one of each" % (r["edid"], len(forge.get(fid, [])), len(temper.get(fid, []))))

    # ---- meshes in the package
    if pkg:
        core = os.path.join(pkg, "00 Core", "meshes")
        absent = []
        for p in sorted(meshes):
            cands = [p] + ([p[:-6] + "_0.nif"] if p.lower().endswith("_1.nif") else [])
            absent += [c for c in cands if not os.path.isfile(os.path.join(core, c.replace("\\", os.sep)))]
        if absent:
            fail("%d mesh(es) the plugin names are not in the package, e.g. %s" % (len(absent), absent[0]))

    print("verify-standalone-esp: OK - %d pieces, %d addons, %d recipes, %d mesh paths%s" % (
        len(armos), len(armas), sum(len(v) for v in forge.values()) + sum(len(v) for v in temper.values()),
        len(meshes), ", all in the package" if pkg else ""))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
