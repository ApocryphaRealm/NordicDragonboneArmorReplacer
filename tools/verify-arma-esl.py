#!/usr/bin/env python3
r"""Check the generated plugin against the game's own records before it is ever loaded.

A plugin that is subtly wrong loads happily and shows the wrong thing, so this compares every
record it contains against the vanilla record it was copied from, byte for byte, and insists that
the ONLY differences are the model paths we meant to change. It also checks that every path the
plugin now names is actually in the built package - a repointed addon aiming at a mesh that was
never shipped is an invisible piece of armour.

Usage:  python tools/verify-arma-esl.py [built package folder]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import importlib.util
spec = importlib.util.spec_from_file_location("gen", os.path.join(HERE, "build-arma-esl.py"))
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def fail(msg):
    raise SystemExit("verify-arma-esl: " + msg)


def read_plugin(path):
    d = open(path, "rb").read()
    hs = struct.unpack("<I", d[4:8])[0]
    flags = struct.unpack("<I", d[8:12])[0]
    masters, i = [], 24
    while i + 6 <= 24 + hs:
        s = d[i:i+4]
        n = struct.unpack("<H", d[i+4:i+6])[0]
        i += 6
        if s == b"MAST":
            masters.append(d[i:i+n].split(b"\x00")[0].decode("latin-1"))
        i += n
    recs = {}

    def walk(off, end):
        while off < end:
            t = d[off:off+4]
            n = struct.unpack("<I", d[off+4:off+8])[0]
            if t == b"GRUP":
                walk(off + 24, off + n)
                off += n
                continue
            fid = struct.unpack("<I", d[off+12:off+16])[0]
            recs[fid] = (t, d[off+24:off+24+n])
            off += 24 + n
    walk(24 + hs, len(d))
    return flags, masters, recs


def main(pkg=None):
    esl = os.path.join(REPO, "plugin", gen.PLUGIN_NAME)
    if not os.path.isfile(esl):
        fail("no plugin at %s - run build-arma-esl.py" % esl)
    flags, masters, recs = read_plugin(esl)

    if not flags & gen.ESL_FLAG:
        fail("the plugin is not flagged light; it would take a full load order slot")
    if masters != gen.STANDARD[:len(masters)]:
        fail("masters are %s, which is not a prefix of the standard load order - FormID indices "
             "would not mean what the records assume" % masters)

    # the vanilla side, rebuilt the same way the generator saw it
    winners = {}
    for name in gen.STANDARD:
        p = gen.plugin_path(name)
        if p is None:
            continue
        for fid, (body, _) in gen.read_arma(p).items():
            if any(gen.repath(v) for v in gen.model_paths(body).values()):
                winners[fid] = (body, name)

    if set(recs) != set(winners):
        missing = sorted(set(winners) - set(recs))
        extra = sorted(set(recs) - set(winners))
        fail("record set differs from the game's: %d missing (%s), %d unexpected (%s)"
             % (len(missing), ", ".join("%08X" % f for f in missing[:4]),
                len(extra), ", ".join("%08X" % f for f in extra[:4])))

    wanted = set()
    for fid, (t, body) in sorted(recs.items()):
        src, plug = winners[fid]
        src_subs = list(gen.subrecords(src))
        new_subs = list(gen.subrecords(body))
        if len(src_subs) != len(new_subs):
            fail("%08X has %d subrecords, the game's has %d - something other than a path changed"
                 % (fid, len(new_subs), len(src_subs)))
        for (s1, d1), (s2, d2) in zip(src_subs, new_subs):
            if s1 != s2:
                fail("%08X subrecord order changed: %s became %s" % (fid, s1, s2))
            if d1 == d2:
                continue
            if s1 not in gen.MODEL_SUBS:
                fail("%08X changed a %s subrecord, which this plugin has no business touching"
                     % (fid, s1.decode()))
            old = d1.split(b"\x00")[0].decode("latin-1")
            new = d2.split(b"\x00")[0].decode("latin-1")
            if gen.repath(old) != new:
                fail("%08X %s became '%s', which is not where '%s' was supposed to move"
                     % (fid, s1.decode(), new, old))
            wanted.add(new.replace("\\", "/").lower())

    print("plugin %s" % os.path.basename(esl))
    print("  light flag ............ set")
    print("  masters ............... %s" % ", ".join(masters))
    print("  records ............... %d, all matching the game's own" % len(recs))
    print("  every difference ...... a model path, and only where one was meant to move")

    if pkg is None:
        cand = os.path.normpath(os.path.join(REPO, "..", "..", "7. current test builds"))
        hits = [os.path.join(cand, d) for d in os.listdir(cand)
                if d.startswith("Nordic Dragonbone Armor Replacer")] if os.path.isdir(cand) else []
        pkg = hits[0] if hits else None
    if pkg is None:
        print("  package ............... not checked (no built package given)")
        return
    have = set()
    for dp, _, fns in os.walk(pkg):
        for fn in fns:
            rel = os.path.relpath(os.path.join(dp, fn), pkg).replace("\\", "/").lower()
            have.add(rel.split("meshes/", 1)[1] if "meshes/" in rel else rel)
    absent = sorted(w for w in wanted if w not in have and
                    w.replace("_1.nif", "_0.nif") not in have)
    if absent:
        fail("%d repointed path(s) are not in the package, so that armour would be invisible:\n  %s"
             % (len(absent), "\n  ".join(absent[:6])))
    print("  repointed meshes ...... %d, every one present in the package" % len(wanted))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
