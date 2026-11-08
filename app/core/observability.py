"""Privacy-first Rius tracing. No telemetry is sent without RIUS_API_KEY."""
import logging
from dotenv import load_dotenv
import rius
from app.core.config import get_settings as settings

load_dotenv()

log = logging.getLogger(__name__)


def initialize():
    """Call once, before instrumented app modules are loaded."""

    disabled = settings().rius_disabled
    if rius is None or disabled or not settings().rius_api_key:
        log.info("Rius observability disabled (missing package, no key, or kill switch)")
        return

    try:
        rius.init(service_name=settings().rius_service_name, capture_content=settings().rius_capture_content)
        log.info("Rius observability enabled")
    except Exception:
        log.exception("Rius initialization failed; continuing without telemetry")


def trace(name):
    """Decorate sync/async functions; never export arguments or return values."""

    def decorate(fn):
        return rius.observe(name=name, capture_input=False, capture_output=False)(fn)

    return decorate