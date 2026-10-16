"""CLI: create the schema and (optionally) load sample data.

Usage:
    python -m database.init_db            # schema + sample data
    python -m database.init_db --no-seed  # schema only
    python -m database.init_db --reset    # drop everything first (SQLite file is deleted)
"""
from __future__ import annotations

import argparse
from pathlib import Path

from utils.config import get_settings
from utils.db_connection import get_engine, init_db, reset_engine


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialise the Cricbuzz LiveStats database")
    parser.add_argument("--no-seed", action="store_true", help="create tables only")
    parser.add_argument("--reset", action="store_true", help="delete the SQLite DB first")
    args = parser.parse_args()

    url = get_settings().database_url
    if args.reset and url.startswith("sqlite:///"):
        reset_engine()
        Path(url.replace("sqlite:///", "", 1)).unlink(missing_ok=True)
        print("Existing SQLite database removed.")

    init_db(seed=not args.no_seed)
    print(f"Database ready: {get_engine().url.render_as_string(hide_password=True)}")


if __name__ == "__main__":
    main()
