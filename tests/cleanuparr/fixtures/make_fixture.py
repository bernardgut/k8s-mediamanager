#!/usr/bin/env python3
# Prints the test fixture for a config dir freshly migrated by the new image; see README
# "Upgrading Cleanuparr". Usage: make_fixture.py <config-dir> <version> > fresh-<version>.sql
import sqlite3
import sys


def main(config_dir, version):
    print(f"-- Fresh Cleanuparr {version} databases after a migrate-only start, as sqlite3 iterdump (no secrets).")
    print("-- Regenerate on an image bump; the '-- database:' lines split the three files.")
    for name in ("cleanuparr.db", "events.db", "users.db"):
        con = sqlite3.connect(f"file:{config_dir}/{name}?mode=ro", uri=True)
        try:
            print(f"-- database: {name}")
            for statement in con.iterdump():
                print(statement)
        finally:
            con.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: make_fixture.py <config-dir> <version>")
    main(sys.argv[1], sys.argv[2])
