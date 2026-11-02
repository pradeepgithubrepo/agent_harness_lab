"""Safe Azure memory connectivity smoke checks; never prints endpoints or keys."""

from agent_harness.memory.config import MemorySettings


def main() -> int:
    status = MemorySettings().connectivity_status()
    for service, configured in status.items():
        print(f"{service}: {'configured' if configured else 'not_configured'}")
    return 0 if all(status.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
