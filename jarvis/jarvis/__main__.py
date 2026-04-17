"""Entrypoint Jarvis.

Lance dashboard + bot Telegram + worker bus. L'ordre de démarrage est :
1. config + scope filter (bloque si périmètre invalide)
2. kill switch check
3. bus + queue
4. dashboard (FastAPI)
5. Telegram bot polling
"""
import asyncio
import signal

from jarvis.core.config import get_settings
from jarvis.core.scope import ScopeFilter
from jarvis.observability.logger import configure_logging, get_logger
from jarvis.security.kill_switch import KillSwitch

logger = get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("jarvis.boot", env=settings.env, version="0.1.0")

    ScopeFilter.validate_boot(settings)
    KillSwitch().assert_ok()

    stop = asyncio.Event()

    def _stop(*_: object) -> None:
        logger.info("jarvis.shutdown.signal")
        stop.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _stop)

    # Phase 1.1 : démarrage minimal. Les workers (bus, bot, dashboard)
    # seront attachés ici dans les jalons suivants.
    logger.info("jarvis.ready", dry_run=settings.dry_run)
    await stop.wait()
    logger.info("jarvis.stopped")


if __name__ == "__main__":
    asyncio.run(main())
