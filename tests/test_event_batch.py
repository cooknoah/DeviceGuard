"""Debounce/cooldown batching in core.event_batch.

A fake timer replaces threading.Timer so the debounce window is driven
deterministically (no real sleeping), and log/pick/toast/UI are captured via
injected seams.
"""

import pytest

from core.event_batch import EventBatch


class FakeTimer:
    """Stand-in for threading.Timer that fires only when the test says so.

    Records itself on the class so a test can inspect/cancel/fire the timer
    that `add()` most recently armed.
    """

    last: "FakeTimer | None" = None

    def __init__(self, interval, function, args=()):
        self.interval = interval
        self.function = function
        self.args = args
        self.cancelled = False
        self.started = False
        FakeTimer.last = self

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True

    def fire(self):
        """Simulate the debounce interval elapsing."""
        self.function(*self.args)


@pytest.fixture
def captured():
    """A batch wired with capturing seams; returns (batch, records)."""
    logged, flushed, toasts = [], [], []

    def fake_log(**kwargs):
        logged.append(kwargs)

    def fake_flush(event_type, best):
        flushed.append((event_type, best))

    def fake_notify(name):
        toasts.append(name)

    clock = {"t": 1000.0}

    batch = EventBatch(
        "connect",
        "notify_on_connect",
        fake_notify,
        on_flush=fake_flush,
        log_event=fake_log,
        pick_best=lambda devs: devs[0],   # deterministic: first wins
        clock=lambda: clock["t"],
        timer_factory=FakeTimer,
    )
    return batch, {"logged": logged, "flushed": flushed, "toasts": toasts, "clock": clock}


CONFIG = {"notify_on_connect": True}


def test_single_event_flushes_once(captured):
    batch, rec = captured
    batch.add({"name": "Kbd", "device_id": "id1"}, CONFIG)
    FakeTimer.last.fire()

    assert len(rec["logged"]) == 1
    assert rec["logged"][0]["device_name"] == "Kbd"
    assert rec["flushed"] == [("connect", {"name": "Kbd", "device_id": "id1"})]
    assert rec["toasts"] == ["Kbd"]


def test_burst_collapses_to_one_flush(captured):
    batch, rec = captured
    # Composite device: several raw interface events before the timer fires.
    first = None
    for i in range(4):
        batch.add({"name": f"iface{i}", "device_id": f"id{i}"}, CONFIG)
        if i == 0:
            first = FakeTimer.last
    # Every add after the first must have cancelled the prior timer.
    assert first.cancelled
    # Only the final timer fires (the earlier ones were cancelled).
    FakeTimer.last.fire()

    assert len(rec["logged"]) == 1          # one history row for the whole burst
    assert len(rec["flushed"]) == 1         # one UI update
    assert rec["toasts"] == ["iface0"]      # pick_best picked the first-queued


def test_empty_flush_is_noop(captured):
    batch, rec = captured
    batch.add({"name": "Kbd"}, CONFIG)
    FakeTimer.last.fire()                    # drains the queue
    FakeTimer.last.fire()                    # second fire sees an empty batch

    assert len(rec["logged"]) == 1
    assert len(rec["flushed"]) == 1


def test_unknown_name_falls_back(captured):
    batch, rec = captured
    batch.add({"device_id": "id1"}, CONFIG)  # no "name" key
    FakeTimer.last.fire()
    assert rec["logged"][0]["device_name"] == "Unknown device"
    assert rec["toasts"] == ["Unknown device"]


def test_toast_suppressed_by_config(captured):
    batch, rec = captured
    batch.add({"name": "Kbd"}, {"notify_on_connect": False})
    FakeTimer.last.fire()
    # Logged and shown in UI, but no toast.
    assert len(rec["logged"]) == 1
    assert len(rec["flushed"]) == 1
    assert rec["toasts"] == []


def test_toast_cooldown_between_flushes(captured):
    batch, rec = captured

    batch.add({"name": "First"}, CONFIG)
    FakeTimer.last.fire()                    # t=1000 → toast

    rec["clock"]["t"] = 1002.0               # 2s later, within COOLDOWN (5s)
    batch.add({"name": "Second"}, CONFIG)
    FakeTimer.last.fire()                    # suppressed

    rec["clock"]["t"] = 1010.0               # 10s after the first toast
    batch.add({"name": "Third"}, CONFIG)
    FakeTimer.last.fire()                    # allowed again

    assert rec["toasts"] == ["First", "Third"]
    # All three still produced a history row + UI update.
    assert len(rec["logged"]) == 3
    assert len(rec["flushed"]) == 3


def test_flush_without_on_flush_callback_still_logs():
    """on_flush is optional; a batch without a UI still logs and toasts."""
    logged, toasts = [], []
    batch = EventBatch(
        "disconnect",
        "notify_on_disconnect",
        lambda name: toasts.append(name),
        on_flush=None,
        log_event=lambda **kw: logged.append(kw),
        pick_best=lambda devs: devs[0],
        clock=lambda: 1000.0,   # realistic uptime; first flush clears cooldown
        timer_factory=FakeTimer,
    )
    batch.add({"name": "Mouse"}, {"notify_on_disconnect": True})
    FakeTimer.last.fire()
    assert logged and toasts == ["Mouse"]
