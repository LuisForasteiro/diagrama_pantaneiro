from __future__ import annotations

import asyncio

import pytest

from app import main


class _FakeScheduler:
    def start(self) -> None:
        pass

    def shutdown(self, wait: bool = True) -> None:
        pass


async def test_lifespan_cancels_pending_startup_jobs_on_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Startup jobs (catalog sync + price refresh) run in the background. The
    app must hold a reference to that task (a bare create_task can be garbage
    collected mid-flight) and cancel it on shutdown instead of leaking it."""
    started = asyncio.Event()
    cancelled = asyncio.Event()

    async def slow_startup_jobs() -> None:
        started.set()
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            cancelled.set()
            raise

    monkeypatch.setattr(main, "run_startup_jobs", slow_startup_jobs)
    monkeypatch.setattr(main, "build_scheduler", lambda _settings: _FakeScheduler())

    async with main.lifespan(main.app):
        await asyncio.wait_for(started.wait(), timeout=1)

    assert cancelled.is_set()
