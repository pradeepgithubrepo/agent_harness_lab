"""SQLite checkpointer factory and stable LangGraph thread configuration."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from langgraph.checkpoint.sqlite import SqliteSaver


def thread_config(workflow_id: str) -> dict[str, dict[str, str]]:
    return {"configurable": {"thread_id": workflow_id}}


@contextmanager
def sqlite_checkpointer(path: str) -> Iterator[SqliteSaver]:
    with SqliteSaver.from_conn_string(path) as saver:
        yield saver
