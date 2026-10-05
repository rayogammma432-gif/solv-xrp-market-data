# XRP Execution Market Archive V1

## Status
Research/shadow execution-market archive. It does not participate in XRP_V3.6 signal generation or gates.

Archive workbook: `XRP_Research_Archive`  
Tab: `XRP_EXECUTION_MARKET_V1`  
Schema: `XRP_EXECUTION_MARKET_V1`

## Cadence and source
The XRP collector records one best-effort snapshot per normal collection cycle from Binance Futures REST:
- premium index / mark price;
- open interest;
- book ticker;
- order-book depth (20 levels).

A failure to fetch book/depth data must not fail the operational collector. Unavailable microstructure values remain blank/None.

## Stored fields
Each row stores:
- Snapshot UTC and schema version;
- Symbol;
- Mark Price / Index Price;
- Basis and Basis bps;
- Funding Rate / Next Funding UTC;
- Open Interest;
- Best Bid / Best Ask;
- absolute Spread / Spread bps;
- best bid/ask quantities;
- bid/ask Top-5 and Top-20 notional depth;
- depth level count;
- source;
- exact Git blob SHA of the running collector file.

## Scientific use
For a decision snapshot, prefer the contemporaneous LIVE_STATE values. Otherwise use the latest archive snapshot at or before Analysis UTC only when age <= 90 seconds. Never use a later snapshot to represent information that was unavailable at decision time.

Fees are not encoded here. Spread/depth are evidence for slippage/execution studies; any fee schedule used later must be versioned separately.
