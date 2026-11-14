"""
Command line for the battle database.

    python -m fp.battle_db import --format gen9vgc2026regi --pages 20
    python -m fp.battle_db import --format gen9vgc2026regi --mode new
    python -m fp.battle_db local battle_logs
    python -m fp.battle_db stats --format gen9vgc2026regi
    python -m fp.battle_db species "Calyrex-Shadow"
"""

from __future__ import annotations

import argparse
import logging
import sys

from .importer import ReplayClient, import_replays
from .local_logs import import_local_logs
from .priors import BattlePriors
from .store import BattleStore

DEFAULT_FORMAT = "gen9vgc2026regi"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m fp.battle_db",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--db", help="SQLite file (default: fp/data/battles.db)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    imp = sub.add_parser(
        "import", help="Pull public replays from Showdown's replay site"
    )
    imp.add_argument("--format", default=DEFAULT_FORMAT)
    imp.add_argument(
        "--pages",
        type=int,
        default=20,
        help="Search pages (50 replays each); 0 = no limit",
    )
    imp.add_argument("--min-rating", type=int, default=0)
    imp.add_argument(
        "--mode",
        choices=["backfill", "new"],
        default="backfill",
        help="backfill = keep going further back; new = grab what's new since last run",
    )
    imp.add_argument(
        "--delay", type=float, default=1.5, help="Seconds between requests (min 1.0)"
    )

    loc = sub.add_parser("local", help="Load the bot's own battle_logs")
    loc.add_argument("log_dir", nargs="?", default="battle_logs")
    loc.add_argument("--replace", action="store_true")

    st = sub.add_parser("stats", help="What's in the database")
    st.add_argument("--format", default=None)
    st.add_argument("--min-rating", type=int, default=0)

    sp = sub.add_parser("species", help="What the database knows about one Pokemon")
    sp.add_argument("species")
    sp.add_argument("--format", default=None)
    sp.add_argument("--min-rating", type=int, default=0)

    sub.add_parser("reparse", help="Re-run the parser over every stored log")

    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    store = BattleStore(args.db)

    if args.cmd == "import":
        client = ReplayClient(delay=max(1.0, args.delay))
        stats = import_replays(
            store,
            args.format,
            max_pages=args.pages or None,
            min_rating=args.min_rating,
            mode=args.mode,
            client=client,
            progress=print,
        )
        print("Done:", stats)
        print("Database:", store.summary(args.format))
    elif args.cmd == "local":
        print(import_local_logs(store, args.log_dir, replace=args.replace))
    elif args.cmd == "stats":
        print(store.summary(args.format))
        pri = BattlePriors(store, format_id=args.format, min_rating=args.min_rating)
        for species, n, wr in pri.top_species(25):
            print(f"  {species:<24} brought {n:>5}  win {wr:.0%}")
    elif args.cmd == "species":
        pri = BattlePriors(store, format_id=args.format, min_rating=args.min_rating)
        wr, n = pri.species_win_rate(args.species)
        print(
            f"{args.species}: brought {n} times, win rate {wr:.0%}"
            if n
            else f"{args.species}: no games"
        )
        print(
            "Moves:",
            {k: f"{v:.0%}" for k, v in pri.move_frequencies(args.species).items()},
        )
        print("Tera:", {k: f"{v:.0%}" for k, v in pri.tera_types(args.species).items()})
        print("Partners:", pri.common_partners(args.species))
        print(f"Protect rate: {pri.protect_rate(args.species):.0%}")
    elif args.cmd == "reparse":
        print("Re-parsed", store.reparse_all(), "battles")
    return 0


if __name__ == "__main__":
    sys.exit(main())
