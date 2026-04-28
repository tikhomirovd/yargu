from __future__ import annotations

import argparse

from yargumark.registry.sync import sync_registry as run_registry_sync


def _sync_registry_cli() -> None:
    run_registry_sync()


def sync_registry_command() -> None:
    parser = argparse.ArgumentParser(description="YarguMark registry utilities")
    parser.add_argument("command", choices=["sync"], help="Registry command to run")
    args = parser.parse_args()
    if args.command == "sync":
        _sync_registry_cli()


if __name__ == "__main__":
    sync_registry_command()
