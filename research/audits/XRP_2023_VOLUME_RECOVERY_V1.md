# XRP 2023 Volume Data-Quality Recovery V1

## Finding

Binance USD-M XRPUSDT monthly 1m kline:
- open time: 2023-11-30 12:35:00 UTC
- official monthly ZIP checksum: valid

Published kline values:
- OHLC: 0.6038 / 0.6038 / 0.6034 / 0.6036
- base volume: **91,695.7**
- quote volume: 200,298.79368
- trades: 470
- taker buy base: 132,462.5
- taker buy quote: 79,957.28937

The published base-volume value is internally impossible because taker-buy base exceeds total base volume.

## Independent official reconstruction

Source:
- Binance daily USD-M `aggTrades`
- `XRPUSDT-aggTrades-2023-11-30.zip`
- SHA-256: `e5fd4262256cd854b5272b257838d32e5030c886706cb5e38400688d5e53b751`

For 12:35:00–12:35:59.999 UTC:
- aggTrade rows: 97
- reconstructed individual trades: 470
- OHLC: 0.6038 / 0.6038 / 0.6034 / 0.6036
- reconstructed base volume: **331,858.0**
- reconstructed quote volume: 200,298.79368000012
- reconstructed taker buy base: 132,462.5
- reconstructed taker buy quote: 79,957.28937
- reconstructed taker buy ratio: **0.3991541563**

Everything except the monthly kline base-volume field agrees.

## Canonical policy

For exactly:
- XRPUSDT
- 2023-11-30 12:35 UTC

`HIST_NORM_V1` replaces the full 1m row with the deterministic official aggTrades reconstruction.

Provenance:
- `source_granularity=aggtrade_recovery`
- source file and source SHA-256 are retained.
- normalization event: `AGGTRADE_VOLUME_RECOVERY`

This repair is based only on source-data integrity and was defined before the 2023 discovery outcomes were produced.

No threshold, hypothesis, direction or outcome was used to define the repair.
