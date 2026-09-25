#!/usr/bin/env python3
import time
from datetime import datetime, timezone

from market_collector import run_once, DEFAULT_CONFIG, logger

OFFSET_SECONDS = 60
INTERVAL_SECONDS = 15 * 60

def next_slot_epoch(now=None):
    now = time.time() if now is None else now
    return ((int(now) - OFFSET_SECONDS) // INTERVAL_SECONDS + 1) * INTERVAL_SECONDS + OFFSET_SECONDS

def main():
    logger.info("Scheduler iniciado. Primera actualización inmediata.")
    while True:
        try:
            code = run_once(DEFAULT_CONFIG, dry_run=False)
            logger.info("Ciclo terminado con código %s", code)
        except Exception as exc:
            logger.exception("Error no controlado del scheduler: %s", exc)

        target = next_slot_epoch()
        wait = max(5, target - time.time())
        dt = datetime.fromtimestamp(target, tz=timezone.utc).isoformat(timespec="seconds")
        logger.info("Próxima ejecución programada para %s (en %.0f s)", dt, wait)
        time.sleep(wait)

if __name__ == "__main__":
    main()
