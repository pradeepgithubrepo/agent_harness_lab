"""Print the durable state for a workflow ID."""
import argparse

from agent_harness.durable_orchestration import sqlite_checkpointer, thread_config


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_id")
    parser.add_argument("--database", default="incident-demo.sqlite")
    args = parser.parse_args()
    with sqlite_checkpointer(args.database) as saver:
        snapshot = saver.get_tuple(thread_config(args.workflow_id))
    print(snapshot.checkpoint["channel_values"] if snapshot else "workflow not found")


if __name__ == "__main__":
    main()
