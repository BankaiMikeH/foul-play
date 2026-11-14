# Battle database and VGC doubles rebuild

## What this adds

- `fp/battle_db/`: a turn-by-turn battle database in the bot's existing
  SQLite file (`fp/data/battles.db`, new `replay_*` tables only). It stores
  who played, the 6 shown at team preview, the 4 brought, the leads, every
  move with its target (spread and locked-in moves flagged), switches,
  Terastallization, faints and the winner. Raw logs are kept compressed so
  everything can be re-parsed later.
- An importer for public replays from Showdown's own replay site, using the
  documented JSON API (`search.json` + `<id>.json`). One request at a time,
  1.5 s apart by default, backs off on errors, never requests private
  replays, skips what's already stored, and can be stopped and resumed.
- A loader for the bot's own games from `battle_logs/*_client_messages.log`.
- `BattlePriors`: what strong players click per Pokemon, Tera types, Protect
  habits, best lead pairs, common partners, win rates.
- `fp/doubles_v2/`: the start of the doubles rebuild on poke-env's
  DoubleBattle, a two-slot heuristic player that uses those priors.

## Run it on your PC

The import has to run on your own machine (the cloud box this was built on
can't reach Showdown).

```
python -m fp.battle_db import --format gen9vgc2026regi --pages 40 --min-rating 1300
python -m fp.battle_db import --format gen9vgc2026regi --mode new     # later: just the new ones
python -m fp.battle_db local battle_logs                              # your bot's own games
python -m fp.battle_db stats --format gen9vgc2026regi --min-rating 1300
python -m fp.battle_db species "Incineroar" --min-rating 1300
```

40 pages is about 2,000 listed replays and takes roughly an hour at the
default pace. Run it again any time; it continues where it stopped.

## Try the doubles player locally

```
python -m venv .venv-doubles
.venv-doubles/bin/pip install -r requirements-doubles.txt
.venv-doubles/bin/python -m fp.doubles_v2.run --team teams/my_vgc_team.txt --self-play 10
```

It only connects to a local Showdown server (`localhost:8000`). Playing on
the public server needs the bot registered with Showdown staff first
(`/ht` in Showdown chat, then "Something else", then "I want to register
my bot"), and an unregistered bot can be banned.
