# Automatic Telegram Alert Research

When a preliminary detector alert is actually sent to Telegram, the Motorola records an event-time research snapshot for SOLV or XRP.

This is research only:
- does not call ChatGPT/OpenAI API;
- does not create or modify SIGNALS;
- does not assign risk;
- does not convert a preliminary alert into a trade.

Sheets:
- ALERT_RESEARCH: event-time snapshot, detector scores and JSON technical context.
- ALERT_FORWARD: direction-adjusted forward returns at 5/15/30/60/240 minutes, written once 240 minutes of data are available.
- ALERT_MFE_MAE: direction-adjusted MFE/MAE at 15/60/240 minutes, written with the completed forward record.

Only events with telegramSent=true create research snapshots. Internal alert lifecycle events remain in ALERTS but are not promoted to ALERT_RESEARCH.

Research version: ALERT_R1.
