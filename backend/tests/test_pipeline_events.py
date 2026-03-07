"""Tests for classify_event() and PipelineEventBus ring buffer."""

import asyncio

import pytest

from app.core.pipeline_events import PipelineEventBus, classify_event


# --- classify_event tests ---


class TestClassifyEvent:
    def test_node_started(self):
        event = {"step": {"status": "running", "node_id": "n1"}}
        assert classify_event(event) == "pipeline:node_started"

    def test_node_completed(self):
        event = {"step": {"status": "completed", "node_id": "n1"}}
        assert classify_event(event) == "pipeline:node_completed"

    def test_node_failed(self):
        event = {"step": {"status": "failed", "node_id": "n1"}}
        assert classify_event(event) == "pipeline:node_failed"

    def test_pipeline_done(self):
        assert classify_event({"status": "done"}) == "pipeline:done"

    def test_pipeline_failed(self):
        assert classify_event({"status": "failed"}) == "pipeline:failed"

    def test_pipeline_cancelled(self):
        assert classify_event({"status": "cancelled"}) == "pipeline:cancelled"

    def test_pipeline_started(self):
        event = {"status": "developing", "previous_status": "planning"}
        assert classify_event(event) == "pipeline:started"

    def test_default_status(self):
        assert classify_event({"status": "reviewing"}) == "pipeline:status"

    def test_empty_event(self):
        assert classify_event({}) == "pipeline:status"

    def test_step_takes_priority_over_top_level_status(self):
        event = {"status": "developing", "step": {"status": "running", "node_id": "n1"}}
        assert classify_event(event) == "pipeline:node_started"

    def test_step_non_dict_ignored(self):
        event = {"status": "done", "step": "some string"}
        assert classify_event(event) == "pipeline:done"


# --- Ring buffer tests ---


class TestPipelineEventBusBuffer:
    @pytest.fixture
    def bus(self):
        return PipelineEventBus()

    @pytest.mark.asyncio
    async def test_get_recent_returns_events_in_order(self, bus):
        await bus.publish({"pipeline_key": "a", "status": "planning"})
        await bus.publish({"pipeline_key": "b", "status": "developing"})
        events = bus.get_recent()
        assert len(events) == 2
        assert events[0]["pipeline_key"] == "a"
        assert events[1]["pipeline_key"] == "b"

    @pytest.mark.asyncio
    async def test_overflow_evicts_oldest(self, bus):
        bus._buffer = __import__("collections").deque(maxlen=3)
        for i in range(5):
            await bus.publish({"pipeline_key": f"p{i}", "status": "s"})
        events = bus.get_recent()
        assert len(events) == 3
        assert events[0]["pipeline_key"] == "p2"

    @pytest.mark.asyncio
    async def test_get_recent_filters_by_pipeline_key(self, bus):
        await bus.publish({"pipeline_key": "a", "status": "s"})
        await bus.publish({"pipeline_key": "b", "status": "s"})
        await bus.publish({"pipeline_key": "a", "status": "s2"})
        events = bus.get_recent(pipeline_key="a")
        assert len(events) == 2
        assert all(e["pipeline_key"] == "a" for e in events)

    @pytest.mark.asyncio
    async def test_get_recent_limit(self, bus):
        for i in range(10):
            await bus.publish({"pipeline_key": "a", "status": f"s{i}"})
        events = bus.get_recent(limit=3)
        assert len(events) == 3
        assert events[0]["status"] == "s7"

    @pytest.mark.asyncio
    async def test_events_auto_get_timestamp_and_event_type(self, bus):
        await bus.publish({"pipeline_key": "a", "status": "done"})
        events = bus.get_recent()
        assert "timestamp" in events[0]
        assert events[0]["event_type"] == "pipeline:done"

    @pytest.mark.asyncio
    async def test_publish_does_not_overwrite_existing_event_type(self, bus):
        await bus.publish({"pipeline_key": "a", "status": "s", "event_type": "custom"})
        events = bus.get_recent()
        assert events[0]["event_type"] == "custom"
