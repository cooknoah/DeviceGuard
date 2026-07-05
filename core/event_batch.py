"""Debounced batching of raw WMI device events.

A composite device (e.g. a keyboard exposing several HID interfaces) fires one
raw WMI event *per interface*. Collapsing the burst into a single logical event
is what yields one history row, one UI update, and one (cooldown-limited) toast
per physical plug/unplug.

The batching is decoupled from both the UI and the logger via injected
callbacks so it can be exercised in isolation; `main.py` wires in the real
window, toast, and logger.
"""

import threading
import time
from typing import Callable

from core import logger
from core.monitor import pick_best_device

# Wait this long after the last raw event before treating the burst as one
# logical event; each new raw event restarts the timer.
DEBOUNCE_SECS = 0.8
# Minimum spacing between toasts of the same kind, so a rapid series of plugs
# doesn't spam notifications.
COOLDOWN_SECS = 5.0


class EventBatch:
    """Debounces raw events of one type into a single flushed action.

    Args:
        event_type: logged/emitted event kind ("connect" | "disconnect").
        notify_config_key: config flag gating the toast for this event type.
        notify: toast callback, invoked with the resolved device name.
        on_flush: UI callback, invoked with (event_type, best_device_dict).
        log_event / pick_best / clock / timer_factory: injectable seams for
            testing; default to the real logger, name picker, monotonic clock,
            and threading.Timer.
    """

    def __init__(
        self,
        event_type: str,
        notify_config_key: str,
        notify: Callable[[str], None],
        on_flush: Callable[[str, dict], None] | None = None,
        *,
        log_event: Callable[..., None] | None = None,
        pick_best: Callable[[list[dict]], dict] | None = None,
        debounce_secs: float = DEBOUNCE_SECS,
        cooldown_secs: float = COOLDOWN_SECS,
        clock: Callable[[], float] = time.monotonic,
        timer_factory: Callable[..., threading.Timer] = threading.Timer,
    ):
        self._event_type = event_type
        self._notify_config_key = notify_config_key
        self._notify = notify
        self._on_flush = on_flush
        self._log_event = log_event or logger.log_event
        self._pick_best = pick_best or pick_best_device
        self._debounce_secs = debounce_secs
        self._cooldown_secs = cooldown_secs
        self._clock = clock
        self._timer_factory = timer_factory

        self._lock = threading.Lock()
        self._pending: list[dict] = []
        self._timer: threading.Timer | None = None
        self._last_toast: float = 0.0

    def add(self, device_info: dict, config: dict) -> None:
        """Queue a raw event and (re)arm the debounce timer."""
        with self._lock:
            self._pending.append(device_info)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = self._timer_factory(
                self._debounce_secs, self._flush, args=(config,)
            )
            self._timer.daemon = True
            self._timer.start()

    def _flush(self, config: dict) -> None:
        """Collapse the queued burst into one log row, UI update, and toast."""
        with self._lock:
            batch = list(self._pending)
            self._pending.clear()
            self._timer = None
        if not batch:
            return

        best = self._pick_best(batch)
        name = best.get("name") or "Unknown device"
        self._log_event(
            event_type=self._event_type,
            device_name=name,
            device_id=best.get("device_id"),
            device_class=best.get("pnp_class"),
            manufacturer=best.get("manufacturer"),
        )
        if self._on_flush is not None:
            self._on_flush(self._event_type, best)

        now = self._clock()
        if (
            config.get(self._notify_config_key, True)
            and now - self._last_toast >= self._cooldown_secs
        ):
            self._notify(name)
            self._last_toast = now
