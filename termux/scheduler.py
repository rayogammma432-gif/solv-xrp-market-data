#!/usr/bin/env python3
import time
from datetime import datetime, timezone

from market_collector import Collector, DEFAULT_CONFIG, logger

OFFSET_SECONDS = 10
INTERVAL_SECONDS = 60

def next_slot_epoch(now=None):
    now = time.time() if now is None else now
    return ((int(now) - OFFSET_SECONDS) // INTERVAL_SECONDS + 1) * INTERVAL_SECONDS + OFFSET_SECONDS

def main():
    collector = Collector(DEFAULT_CONFIG)

    while True:
        try:
            if not collector.bootstrapped:
                logger.info("Scheduler 1m iniciado: ejecutando bootstrap completo.")
                collector.bootstrap(dry_run=False)
            else:
                collector.incremental_cycle(dry_run=False)
        except Exception as exc:
            logger.exception("Error del ciclo: %s", exc)

        target = next_slot_epoch()
        wait = max(2, target - time.time())
        dt = datetime.fromtimestamp(target, tz=timezone.utc).isoformat(timespec="seconds")
        logger.info("Próximo ciclo: %s (en %.0f s)", dt, wait)
        time.sleep(wait)

if __name__ == "__main__":
    main()
