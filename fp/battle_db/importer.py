"""
Import public replays from Showdown's replay site into the battle database.

Uses only the JSON API that Showdown documents for this purpose
(https://github.com/smogon/pokemon-showdown-client/blob/master/WEB-API.md):

  * search.json?format=<id>&before=<uploadtime>   (51 results, pages of 50)
  * <replay id>.json                               (one replay, with its log)

It is deliberately slow and polite: one request at a time, a fixed delay
between requests, backoff on errors, a clear User-Agent, and it skips
anything already stored, so it can be stopped and restarted at any time.
Private or password-protected replays are never requested.
"""

from __future__ import annotations

import logging
import time
from typing import Callable, Dict, Iterator, List, Optional

import requests

from .store import BattleStore

logger = logging.getLogger(__name__)

REPLAY_BASE = "https://replay.pokemonshowdown.com"
USER_AGENT = "foul-play-battle-db/1.0 (personal research bot; low request rate)"
PAGE_SIZE = 50


class ReplayClient:
    def __init__(
        self,
        delay: float = 1.5,
        timeout: float = 20.0,
        max_retries: int = 4,
        session: Optional[requests.Session] = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = session or requests.Session()
        self.session.headers.update(
            {"User-Agent": USER_AGENT, "Accept": "application/json"}
        )
        self._sleep = sleep
        self._last_request = 0.0

    def _get_json(self, url: str, params: Optional[dict] = None):
        for attempt in range(self.max_retries + 1):
            wait = self.delay - (time.monotonic() - self._last_request)
            if wait > 0:
                self._sleep(wait)
            self._last_request = time.monotonic()
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as e:
                err = str(e)
            else:
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code == 404:
                    return None
                err = f"HTTP {resp.status_code}"
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        self._sleep(int(retry_after))
            backoff = min(60.0, self.delay * (2 ** (attempt + 1)))
            logger.warning(
                "Request failed (%s) for %s; retrying in %.0fs", err, url, backoff
            )
            self._sleep(backoff)
        raise RuntimeError(f"Giving up on {url} after {self.max_retries + 1} tries")

    def search(self, format_id: str, before: Optional[int] = None) -> List[dict]:
        params: Dict[str, object] = {"format": format_id}
        if before:
            params["before"] = before
        return self._get_json(f"{REPLAY_BASE}/search.json", params) or []

    def replay(self, replay_id: str) -> Optional[dict]:
        return self._get_json(f"{REPLAY_BASE}/{replay_id}.json")

    def iter_listings(
        self,
        format_id: str,
        before: Optional[int] = None,
        max_pages: Optional[int] = None,
    ) -> Iterator[List[dict]]:
        """Yield pages of replay listings, newest first, walking back in time."""
        pages = 0
        while max_pages is None or pages < max_pages:
            batch = self.search(format_id, before)
            if not batch:
                return
            page = batch[:PAGE_SIZE]
            yield page
            pages += 1
            if len(batch) <= PAGE_SIZE:
                return
            before = page[-1]["uploadtime"]


def import_replays(
    store: BattleStore,
    format_id: str,
    max_pages: Optional[int] = 20,
    min_rating: int = 0,
    mode: str = "backfill",
    client: Optional[ReplayClient] = None,
    progress: Optional[Callable[[str], None]] = None,
) -> dict:
    """Import replays for one format.

    mode="new":      start from the newest replays and stop at ones already stored.
    mode="backfill": continue further back in time from the oldest replay seen.
    """
    client = client or ReplayClient()
    say = progress or (lambda msg: logger.info(msg))
    stats = {
        "listed": 0,
        "imported": 0,
        "skipped_existing": 0,
        "skipped_rating": 0,
        "skipped_private": 0,
        "failed": 0,
        "pages": 0,
    }

    before = None
    if mode == "backfill":
        state = store.get_import_state(format_id)
        if state and state["oldest_seen"]:
            before = state["oldest_seen"]

    for page in client.iter_listings(format_id, before=before, max_pages=max_pages):
        stats["pages"] += 1
        hit_known = False
        for entry in page:
            stats["listed"] += 1
            rid = entry.get("id")
            if not rid:
                continue
            if entry.get("private") or entry.get("password"):
                stats["skipped_private"] += 1
                continue
            if store.has_battle(rid):
                stats["skipped_existing"] += 1
                hit_known = True
                continue
            if (entry.get("rating") or 0) < min_rating:
                stats["skipped_rating"] += 1
                continue
            try:
                data = client.replay(rid)
                if not data or not data.get("log"):
                    stats["failed"] += 1
                    continue
                store.add_battle(
                    rid,
                    data["log"],
                    source="showdown_replay",
                    format_id=data.get("formatid") or format_id,
                    uploadtime=data.get("uploadtime") or entry.get("uploadtime"),
                    rating=data.get("rating") or entry.get("rating"),
                )
                stats["imported"] += 1
            except Exception as e:  # keep going; one bad replay shouldn't stop a run
                logger.warning("Could not import %s: %s", rid, e)
                stats["failed"] += 1
        store.update_import_state(format_id, [e.get("uploadtime") for e in page])
        say(
            f"page {stats['pages']}: imported {stats['imported']} so far "
            f"({stats['skipped_existing']} already stored)"
        )
        if mode == "new" and hit_known:
            break
    return stats
