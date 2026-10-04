# XRP V3.6 — Mark-aware anti-chase correction

## Prospective boundary

V3.6 is a prospective successor to V3.5. The live analysis `XRP-20261004T230928Z-ANALIZA` remains V3.5 and is retained as the regression case that exposed the mismatch. No V3.5 row or signal is relabeled.

## Defect

V3.5 defined anti-chase using `ABS(Entry-SETUP_ANCHOR)/ATR15m`. That validates whether the planned Entry is structurally close to its anchor, but it does not measure whether the current market has already run far beyond that Entry.

Regression values:
- Direction LONG
- Entry 1.5045
- SETUP_ANCHOR 1.5031
- Mark 1.5185
- ATR15m 0.004942
- entryAnchorDist ≈ 0.28 ATR
- Mark extension beyond Entry ≈ 2.83 ATR

The correct operational state was WAIT_RETEST, but V3.5 could only justify that result through contextual TV extension fields rather than the canonical E2 formula.

## V3.6 correction

V3.6 keeps the structural distance and adds a directional Mark extension:

```
entryAnchorDist = ABS(Entry-SETUP_ANCHOR)/ATR15m

LONG:
markEntryExtension = MAX(0,(MarkPrice-Entry)/ATR15m)

SHORT:
markEntryExtension = MAX(0,(Entry-MarkPrice)/ATR15m)
```

E2 PASS requires:
- entryAnchorDist <= 0.50;
- markEntryExtension <= 0.50;
- RR_real >= 1.5.

Otherwise E2=NO and the correctable execution state is WAIT_RETEST unless a higher-precedence blocker applies.

## TradingView boundary

TV TECH/PATTERN remains research/context telemetry. TV Pullback Window, Extension Warning and ST15 Dist ATR may agree with the canonical result, but they do not determine E2 or the Execution Gate.

## Architecture

Because V3.5 is already live evidence, it is not edited in place. V3.6 uses a manifest-pinned composite authority:
- immutable full V3.5 master as BASE;
- V3.6 override containing only the prospective clauses.

This preserves the full non-compacted GitHub master, explicit version provenance and deterministic rollback.
