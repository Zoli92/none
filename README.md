# Discogs watcher (NONE vinyl)

Checks Discogs every ~10 minutes and pushes an alert to your phone the moment a
new copy of a watched release is listed. Runs free on GitHub Actions.

## Setup (about 10 minutes)

### 1. Pick your alert app
**ntfy (easiest):** install the ntfy app (Android/iOS), tap +, and subscribe to a
topic with a long, unguessable name, e.g. `none-vinyl-7fk29qx`. Anyone who knows
the name can read it, so don't use something short.

**Telegram (optional, can use both):**
1. In Telegram, message **@BotFather** → `/newbot` → copy the bot token.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy
   the number after `"chat":{"id":`. That's your chat ID.

### 2. Create the GitHub repo
1. Sign up at github.com if needed, then **New repository**.
2. Make it **Public**. Public repos get unlimited free Actions minutes; a private
   one would run out at this check frequency. Only the release IDs are visible,
   your ntfy topic and tokens stay secret (step 3).
3. **Add file → Upload files** and upload everything from this folder, including
   the `.github/workflows/watch.yml` file (keep the folder structure; if the
   uploader drops the hidden `.github` folder, create the file by hand via
   **Add file → Create new file** and type `.github/workflows/watch.yml` as the name).

### 3. Add your secrets
Repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Value |
|---|---|
| `NTFY_TOPIC` | your ntfy topic name |
| `TELEGRAM_BOT_TOKEN` | (optional) bot token |
| `TELEGRAM_CHAT_ID` | (optional) chat ID |
| `DISCOGS_TOKEN` | (optional) from discogs.com/settings/developers, raises the rate limit |

### 4. Turn it on and test
1. Repo → **Actions** tab → enable workflows if asked.
2. Click **Discogs watcher → Run workflow**, tick **Send a test notification**, run.
   Your phone should buzz within a minute.
3. Run it once more without the tick. It records current counts. Anything
   already listed will alert once on this first run (e.g. the Verdant Grave
   pressing had a copy up recently).

From then on it checks automatically, roughly every 10 minutes (GitHub can
delay scheduled runs a bit at busy times).

## Watching more records
Edit `releases.json` on GitHub and add a line with the release ID (the number in
the Discogs URL, e.g. `discogs.com/release/22072507-...` → `22072507`). Remove
any variants you don't care about. Each release pressing has its own ID, so add
every variant you'd buy.

## How it works
- Asks the Discogs API how many copies are for sale per release.
- Alerts when the count **goes up** (new listing), not on every run.
- Saves the counts in `state.github.json`, committed back to the repo only when they change.
  A copy run on your own computer keeps its counts in `state.json`, which is not committed.
- GitHub pauses schedules after 60 days of no repo activity, so the workflow
  makes an empty "Keepalive" commit every ~50 days.
- If GitHub ever emails you that the workflow was disabled, just re-enable it
  in the Actions tab.
