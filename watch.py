#!/usr/bin/env python3
"""Discogs release watcher: pings you when a new copy of a watched release is listed.

Reads releases.json, asks the Discogs API how many copies of each release are
for sale, compares with state.json from the previous run, and sends an ntfy
and/or Telegram alert when the count goes up. Standard library only.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


HERE = os.path.dirname(os.path.abspath(__file__))
try:
    import dotenv
    dotenv.load_dotenv(os.path.join(HERE, ".env"))
except ImportError:
    pass
RELEASES_FILE = os.path.join(HERE, "releases.json")
STATE_FILE = os.path.join(HERE, os.environ.get("STATE_FILE", "state.json"))

USER_AGENT = "NoneVinylWatcher/1.0 +https://github.com"
CURRENCY = os.environ.get("CURRENCY", "EUR")
DISCOGS_TOKEN = os.environ.get("DISCOGS_TOKEN", "").strip()
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh").rstrip("/")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "").strip()


def http(url, data=None, headers=None, method=None):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8")


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def fetch_stats(release_id):
    """Return (num_for_sale, lowest_price_str_or_None) for a release."""
    url = f"https://api.discogs.com/marketplace/stats/{release_id}?curr_abbr={CURRENCY}"
    headers = {"User-Agent": USER_AGENT}
    if DISCOGS_TOKEN:
        headers["Authorization"] = f"Discogs token={DISCOGS_TOKEN}"
    for attempt in range(3):
        try:
            data = json.loads(http(url, headers=headers))
            break
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 2:  # rate limited, back off
                time.sleep(10 * (attempt + 1))
                continue
            raise
    count = int(data.get("num_for_sale") or 0)
    low = data.get("lowest_price")
    price = f"{low['value']:.2f} {low['currency']}" if low and low.get("value") is not None else None
    return count, price


def notify(title, message, link):
    sent = False
    if NTFY_TOPIC:
        try:
            http(
                f"{NTFY_SERVER}/{urllib.parse.quote(NTFY_TOPIC)}",
                data=message.encode("utf-8"),
                headers={
                    "Title": title.encode("ascii", "ignore").decode(),
                    "Click": link,
                    "Priority": "urgent",
                    "Tags": "rotating_light,cd",
                },
                method="POST",
            )
            sent = True
        except Exception as e:  # keep going, try Telegram too
            print(f"  ntfy failed: {e}", file=sys.stderr)
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            body = urllib.parse.urlencode({
                "chat_id": TELEGRAM_CHAT_ID,
                "text": f"{title}\n{message}\n{link}",
                "disable_web_page_preview": "false",
            }).encode()
            http(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", data=body)
            sent = True
        except Exception as e:
            print(f"  Telegram failed: {e}", file=sys.stderr)
    if not (NTFY_TOPIC or (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)):
        print("  (no NTFY_TOPIC or Telegram secrets set, alert only printed)")
    return sent


def main():
    releases = load_json(RELEASES_FILE, [])
    state = load_json(STATE_FILE, {})
    new_state = dict(state)

    if "--test" in sys.argv:
        ok = notify("Discogs watcher test", "If you see this, alerts work.", "https://www.discogs.com/sell/mywants")
        print("Test alert sent." if ok else "Test alert NOT sent, check your secrets.")
        return

    for r in releases:
        rid = str(r["id"])
        name = r.get("name", rid)
        link = f"https://www.discogs.com/sell/release/{rid}"
        try:
            count, price = fetch_stats(rid)
        except Exception as e:
            print(f"[{rid}] {name}: lookup failed ({e}), keeping previous state")
            continue
        prev = state.get(rid, {}).get("count", 0)
        print(f"[{rid}] {name}: {count} for sale (was {prev})" + (f", lowest {price}" if price else ""))
        if count > prev:
            extra = count - prev
            msg = f"{extra} new cop{'y' if extra == 1 else 'ies'} listed, {count} for sale now"
            if price:
                msg += f", lowest {price}"
            notify(f"FOR SALE: {name}", msg, link)
        new_state[rid] = {"count": count, "checked": int(time.time())}
        time.sleep(1.5)  # stay well under Discogs' rate limit

    # Only rewrite the file when a count changed, so the repo isn't spammed with commits.
    counts = lambda s: {k: v.get("count") for k, v in s.items()}
    if counts(new_state) != counts(state):
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(new_state, f, indent=2, sort_keys=True)
            f.write("\n")
        print(f"State changed, {os.path.basename(STATE_FILE)} updated.")


if __name__ == "__main__":
    main()
