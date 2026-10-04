#!/usr/bin/env python3
import json
import math
import pathlib
import subprocess


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "agents" / "XRP_MASTER_MANIFEST.json"


def git_blob(path):
    return subprocess.check_output(
        ["git", "hash-object", str(path)], cwd=ROOT, text=True
    ).strip()


def anti_chase(direction, entry, anchor, mark, atr15m, rr_real):
    values = (entry, anchor, mark, atr15m, rr_real)
    if any(not math.isfinite(float(x)) for x in values) or atr15m <= 0:
        return None, None, "UNKNOWN"
    entry_anchor = abs(entry - anchor) / atr15m
    if direction == "LONG":
        mark_ext = max(0.0, (mark - entry) / atr15m)
    elif direction == "SHORT":
        mark_ext = max(0.0, (entry - mark) / atr15m)
    else:
        raise ValueError(direction)
    passed = entry_anchor <= 0.50 and mark_ext <= 0.50 and rr_real >= 1.5
    return entry_anchor, mark_ext, "YES" if passed else "NO"


def main():
    manifest = json.loads(MANIFEST.read_text())
    assert manifest["rule_version"] == "XRP_V3.6"
    assert manifest["master_mode"] == "composite"
    assert manifest["base_rule_version"] == "XRP_V3.5"

    base = ROOT / manifest["master_path"]
    override = ROOT / manifest["override_path"]
    assert git_blob(base) == manifest["master_git_blob_sha"]
    assert git_blob(override) == manifest["override_git_blob_sha"]
    assert len(base.read_text()) >= 12000
    ov = override.read_text()

    required = [
        "entryAnchorDist = ABS(Entry-SETUP_ANCHOR)/ATR15m",
        "LONG: markEntryExtension = MAX(0,(MarkPrice-Entry)/ATR15m)",
        "SHORT: markEntryExtension = MAX(0,(Entry-MarkPrice)/ATR15m)",
        "NO determinan E2",
        "SIGNALS AN Rule Version=XRP_V3.6",
        "ANALYSES BF=Rule Version=XRP_V3.6",
    ]
    for marker in required:
        assert marker in ov, marker

    ea, me, e2 = anti_chase("LONG", 1.5045, 1.5031, 1.5185, 0.004942, 1.53)
    assert 0.27 < ea < 0.29
    assert 2.82 < me < 2.84
    assert e2 == "NO"

    ea, me, e2 = anti_chase("SHORT", 1.5185, 1.5199, 1.5045, 0.004942, 1.53)
    assert 0.27 < ea < 0.29
    assert 2.82 < me < 2.84
    assert e2 == "NO"

    ea, me, e2 = anti_chase("LONG", 1.5045, 1.5031, 1.5055, 0.004942, 1.53)
    assert ea <= 0.50 and me <= 0.50 and e2 == "YES"

    ea, me, e2 = anti_chase("LONG", 1.5060, 1.5031, 1.5060, 0.004942, 1.53)
    assert ea > 0.50 and e2 == "NO"

    print("PASS XRP_V3_6_NORMATIVE_REGRESSION")


if __name__ == "__main__":
    main()
