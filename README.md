## ⚡ One-Click Install

```bash
wget https://github.com/sarakmacbook/OKX_Telegram_P2P_Price_Bot/blob/main/install.sh


chmod +x install.sh

./install.sh
```
https://github.com/sarakmacbook/OKX_Telegram_P2P_Price_Bot/blob/main/install.sh


## ⚡ One-Click Uninstall
```bash
wget https://github.com/sarakmacbook/OKX_Telegram_P2P_Price_Bot/blob/main/uninstall.sh


chmod +x uninstall.sh

./uninstall.sh
```


# 🤖 P2P Merchant Price Bot

Telegram bot that watches your favourite **P2P merchants** on **Binance · Bybit · OKX · Bitget** and posts their best **sell** / **buy** prices to your Telegram group — automatically, every time the price changes.

---

## ⚡ One-Click Install

Pick the installer that matches your machine — all four ask for your **bot token** (from [@BotFather](https://t.me/BotFather) → `/newbot`) and your **Telegram ID** (from [@userinfobot](https://t.me/userinfobot)), then start the bot.

| Installer | Best for | What it does |
|---|---|---|
| `install.sh` | Ubuntu/Debian **VPS with systemd** | venv + systemd service (auto-restart & reboot-safe) |
| `install-docker.sh` | Any machine **with Docker**, incl. macOS | Docker Compose container (`restart: unless-stopped`) |
| `install-local.sh` | **macOS / Linux without systemd / WSL** | venv + nohup + launchd (macOS) or cron `@reboot` autostart |
| **python3 one-liner** | **Any machine with Python 3** (no curl / wget needed) | Downloads + runs `install-local.sh` in one command |
| **`vercel.json`** | **Vercel (serverless)** — no server at all | Webhook bot + `/api/cron` endpoint, state in Vercel KV/Upstash — see [Deploy on Vercel](#-deploy-on-vercel) |

> **curl or wget — your choice.** Every one-liner below is shown with both `curl` and `wget`; they are interchangeable. Inside the scripts the same applies: downloads automatically use **curl → wget → python3**, whichever exists on the box, and `git` is optional (a tarball is fetched instead when git is missing). Force a specific tool with `DOWNLOADER=wget`.

### Option A — VPS with systemd (recommended)

Paste this on a fresh Ubuntu VPS (20.04 / 22.04 / 24.04):

```bash
# with curl
curl -fsSL https://raw.githubusercontent.com/sarakmacbook/exchange/main/install.sh | bash

# with wget
wget -qO- https://raw.githubusercontent.com/sarakmacbook/exchange/main/install.sh | bash
```

### Option B — Docker (macOS, Windows, any Linux)

```bash
# with curl
curl -fsSL https://raw.githubusercontent.com/sarakmacbook/exchange/main/install-docker.sh | bash

# with wget
wget -qO- https://raw.githubusercontent.com/sarakmacbook/exchange/main/install-docker.sh | bash
```

The script checks/installs Docker, creates `config.json` + `.env`, and runs `docker compose up -d --build`.

### Option C — Local / no systemd (laptops, WSL, shared hosting)

```bash
# with curl
curl -fsSL https://raw.githubusercontent.com/sarakmacbook/exchange/main/install-local.sh | bash

# with wget
wget -qO- https://raw.githubusercontent.com/sarakmacbook/exchange/main/install-local.sh | bash
```

### Option D — Python 3 (no curl / no wget)

One-click install with nothing but **Python 3** installed. It downloads `install-local.sh` and runs it:

```bash
python3 -c "import urllib.request as u;print(u.urlopen('https://raw.githubusercontent.com/sarakmacbook/exchange/main/install-local.sh').read().decode())" | bash
```

> This is the same local / no-systemd install as **Option C**, just launched by Python instead of `curl` or `wget`.

### Option E — Vercel (serverless, no VPS)

One click, no server to babysit:

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fsarakmacbook%2FOKX_Telegram_P2P_Price_Bot&env=BOT_TOKEN,ADMIN_IDS,CRON_SECRET&envDescription=BOT_TOKEN%20from%20%40BotFather%2C%20ADMIN_IDS%20from%20%40userinfobot%2C%20CRON_SECRET%20protects%20%2Fapi%2Fcron&project-name=p2p-price-bot)

Full walkthrough (environment variables, Redis/KV state, webhook registration and the
free scheduler): **[Deploy on Vercel](#-deploy-on-vercel)**.

<details>
<summary>No curl and no wget? (python3 / PowerShell / manual)</summary>

**python3 (any Linux/macOS with Python 3):** use **Option D** above — one command, no curl/wget needed.

**Windows PowerShell** (then run it with WSL or Git Bash):

```powershell
Invoke-WebRequest https://raw.githubusercontent.com/sarakmacbook/exchange/main/install-local.sh -OutFile install-local.sh
bash install-local.sh
```

**Fully manual — download the archive, no git needed:**

```bash
mkdir -p ~/exchange && wget -qO- https://codeload.github.com/sarakmacbook/exchange/tar.gz/refs/heads/main | tar -xz --strip-components=1 -C ~/exchange
cd ~/exchange && bash install-local.sh        # or: sudo bash install.sh
```

(With curl instead of wget: `curl -fsSL https://codeload.github.com/sarakmacbook/exchange/tar.gz/refs/heads/main | tar -xz --strip-components=1 -C ~/exchange`)
</details>

<details>
<summary>No prompts (for automation) — any installer</summary>

```bash
# curl
curl -fsSL https://raw.githubusercontent.com/sarakmacbook/exchange/main/install.sh | bash -s -- \
  --token "123456:ABC-your-token" --admins "123456789" --asset USDT --fiat USD --interval 60

# wget
wget -qO- https://raw.githubusercontent.com/sarakmacbook/exchange/main/install.sh | bash -s -- \
  --token "123456:ABC-your-token" --admins "123456789" --asset USDT --fiat USD --interval 60
```
</details>

<details>
<summary>Docker without the installer</summary>

```bash
git clone https://github.com/sarakmacbook/exchange.git && cd exchange
cp .env.example .env && nano .env      # BOT_TOKEN + ADMIN_IDS
docker compose up -d --build
```
</details>

---

## 📱 Setup in Telegram (1 minute)

1. Open your bot → `/start`
2. Tap **👥 Set group** → pick your group → done. The bot joins and registers the group automatically.
3. **Paste a merchant URL** into the bot chat to add it:
   - `https://p2p.binance.com/en/advertiserDetail?advertiserNo=…`
   - `https://www.bybit.com/en/fiat/trade/otc/profile/…`
   - `https://www.okx.com/p2p/market?publicUserId=…`
   - `https://www.bitget.com/p2p/merchant/…`
4. Tap **🟢 Auto: ON** — prices are posted whenever they change.

### Panel buttons

| Button | What it does |
|---|---|
| 📊 **Post prices now** | Posts all merchant prices to the group immediately |
| 🟢/🔴 **Auto** | Toggle automatic posting on price change |
| 📋 **Merchants** | List merchants — tap one to remove |
| 👥 **Set group** | One click: choose the group that receives updates |
| ⚙️ **Settings** | Liquidity, Buy/Sell buttons, auto-delete timers, **join/left cleanup** |
| 🟢🔴 **Buy/Sell buttons** | Swap Buy/Sell order and edit their labels + links |
| 📝 **Custom Msg** | Customize the **full** post: header, body (per-merchant template), footer |
| 👁 **Preview** | See exactly how the group post will look |
| 🔄 **Refresh** | Refresh the panel |

### 📝 Custom message — header, body & footer

Tap **📝 Custom Msg** (or ⚙️ Settings → Edit) to fully customize the group post:

- **Header** — shown once on top (default: `📊 P2P {ASSET}/{FIAT}`).
- **Body** — a template repeated **once per merchant**. Leave it default or write your own.
- **Footer** — shown once at the bottom (default: none).

**Body placeholders** (also `{ASSET}`, `{FIAT}`, `{PAIR}` work everywhere):

| Placeholder | Replaced with |
|---|---|
| `{ICON}` | Exchange emoji (🟡 🟣 ⚫ 🔵) |
| `{EXCHANGE}` | Exchange name, e.g. `Binance` |
| `{NICK}` | Merchant nickname |
| `{LINK}` | Clickable merchant name (`<a>` to the profile) |
| `{URL}` | Raw merchant profile URL |
| `{SELL}` / `{BUY}` | Best sell / buy price |
| `{SELL_AMOUNT}` / `{BUY_AMOUNT}` | Available liquidity (if the merchant has ads) |
| `{SELL_URL}` / `{BUY_URL}` | Link to the exact ad behind that price (profile/market fallback) |
| `{SELL_LINK}` / `{BUY_LINK}` | The price itself as a clickable link |
| `{SELL_AD_ID}` / `{BUY_AD_ID}` | The ad ids the prices came from |
| `{ERROR}` | Fetch error text, if any |

HTML (`<b>`, `<i>`, `<code>`, `<a href>`) and new lines are supported. Example 3-line body:

```
{ICON} <b>{EXCHANGE}</b> · {LINK}
🔴 Sell: <b>{SELL}</b> 💧 {SELL_AMOUNT} {ASSET}
🟢 Buy: <b>{BUY}</b> 💧 {BUY_AMOUNT} {ASSET}
```

Use **👁 Preview** to check the result before it goes to the group.

### 🟢🔴 Buy / Sell buttons — order, labels & links

Under every group post the bot shows one row of inline buttons per merchant. By default it is
**🟢 BUY on the left · 🔴 SELL on the right** — and everything about them is editable from the
**private chat with the bot**: tap **🟢🔴 Buy/Sell buttons** on the panel (or ⚙️ Settings →
**🟢🔴 Edit Buy/Sell buttons**).

| Menu item | What it does |
|---|---|
| 🔘 **Buttons: ON/OFF** | Show or hide the buttons in the group post |
| 🔄 **Order** | Switch between `🟢 Buy ⬅️ \| Sell ➡️ 🔴` and `🔴 Sell ⬅️ \| Buy ➡️ 🟢` (the price lines in the text follow the same order) |
| 🟢 **Edit BUY label** | Send your own caption for the Buy button |
| 🔴 **Edit SELL label** | Send your own caption for the Sell button |
| 🎯 **Target** | Switch between **the exact ad** of the shown price (default) and the merchant profile page |
| 🔗 **BUY / SELL link** | Optional custom URL — overrides the target for that side (`{AD_URL}`, `{AD_ID}`, `{PRICE}`, `{URL}`, `{NICK}`, … available) |
| 🔗 **Ad link templates** | Edit the deep-link template of each exchange (Binance / Bybit / OKX / Bitget) |
| ♻️ **Reset buttons to default** | Back to the defaults below |

Defaults:

```
🟢 BUY {PRICE} {NICK}      🔴 SELL {PRICE} {NICK}
```

**Label placeholders**

| Placeholder | Replaced with |
|---|---|
| `{PRICE}` | Best price for that side |
| `{NICK}` / `{FULLNICK}` | Merchant nickname (max 14 chars) / full nickname |
| `{EXCHANGE}` / `{ICON}` | Exchange name / emoji (🟡 🟣 ⚫ 🔵) |
| `{AMOUNT}` | Available liquidity for that side |
| `{ASSET}` / `{FIAT}` / `{PAIR}` | e.g. `USDT`, `USD`, `USDT/USD` |
| `{SIDE}` | `BUY` or `SELL` |

Telegram limits a button caption to ~64 characters — if your template renders longer, the bot drops
the nickname automatically and truncates as a last resort. Link placeholders: `{AD_URL}` (the
exact ad), `{AD_ID}`, `{URL}` (merchant profile), `{PRICE}`, `{NICK}`, `{EXCHANGE}`, `{ASSET}`,
`{FIAT}`, `{SIDE}`. Send `default` while editing to restore the
default label/link, or `/cancel` to abort. Use **👁 Preview** to see the real buttons before posting.

### 🎯 Buy/Sell buttons that open the **exact ad**

Every price in the post comes from one specific ad: the cheapest **SELL** ad and the highest
**BUY** ad of that merchant. The bot remembers those ad ids and turns the buttons (and,
optionally, the prices in the text) into links that open **that very ad**, not just the
merchant's profile.

```
📊 P2P USDT/USD

⚫ Okx · Fast_sonic
   🟢 Best BUY  (you sell): 1.001          ← button → that exact BUY ad
   🔴 Best SELL (you buy):  0.999          ← button → that exact SELL ad
[🟢 BUY 1.001 Fast_sonic] [🔴 SELL 0.999 Fast_sonic]
```

* ⚙️ **Settings → 🎯 Exact ad links** switches the buttons (and prices) between
  **the exact ad** and the **merchant profile page**. Default: exact ad.
* ⚙️ **Settings → 🔗 Link prices** makes the prices inside the post clickable too.
* ⚙️ **Settings → 🔗 Ad link templates** — one template per exchange, editable from Telegram
  (or via the `AD_LINK_TEMPLATES` env var). Placeholders: `{AD_ID}` `{ASSET}` `{ASSET_LOWER}`
  `{FIAT}` `{FIAT_LOWER}` `{SIDE}` `{TAKER_SIDE}` `{ACTION_TYPE}` `{URL}` `{NICK}`.

Built-in templates and how precise they are:

| Exchange | Template | Opens |
|---|---|---|
| 🟡 **Binance** | `c2c.binance.com/en/adv?code={AD_ID}` | **the exact ad** (Binance's documented ad link) |
| ⚫ **OKX** | `okx.com/p2p-markets/{FIAT}/{TAKER_SIDE}-{ASSET}?adId={AD_ID}` | the right market/side/pair + ad hint |
| 🟣 **Bybit** | `bybit.com/en/p2p/{TAKER_SIDE}/{ASSET}/{FIAT}?actionType=…&adId={AD_ID}` | the right market/side/pair + ad hint |
| 🔵 **Bitget** | `bitget.com/p2p-trade?fiatName={FIAT}&coinName={ASSET}&advId={AD_ID}` | the right market/pair + ad hint |

The exchanges that do not document an ad-level parameter simply ignore the extra `adId` / `advId`
hint, so the link still lands on the correct side and pair — and you can paste your own working
template in **🔗 Ad link templates** at any time (no code change, no redeploy). Bybit's own share
links expire after 30 minutes, which is why its default template points at the market page.

### 🚪 Auto-delete “joined / left the group” messages

The bot deletes Telegram’s **“X joined the group”** and **“X left the group”** service messages in your group — including when people join after being **accepted via a join request** — so your price feed stays clean.

- Toggle in ⚙️ **Settings → 🚪 Del Join/Left msgs** (ON by default).
- ⚠️ The bot must be a **group admin** with the **Delete messages** permission, otherwise it can't remove those messages.

---

## ▲ Deploy on Vercel

The bot runs on Vercel as a **webhook** bot: Telegram pushes every update to
`POST /api/telegram`, and a scheduled tick hits `GET /api/cron` to publish prices and do the
housekeeping. No server, no polling process — the price checks run inside the function.

### 1. Deploy

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fsarakmacbook%2FOKX_Telegram_P2P_Price_Bot&env=BOT_TOKEN,ADMIN_IDS,CRON_SECRET&envDescription=BOT_TOKEN%20from%20%40BotFather%2C%20ADMIN_IDS%20from%20%40userinfobot%2C%20CRON_SECRET%20protects%20%2Fapi%2Fcron&project-name=p2p-price-bot)

or from the CLI:

```bash
npm i -g vercel
vercel                      # link / create the project (framework preset: Other)
vercel --prod               # deploy
```

### 2. Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `BOT_TOKEN` | ✅ | Token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | ✅ | Your Telegram id from [@userinfobot](https://t.me/userinfobot) (comma-separated) |
| `ASSET` / `FIAT` | – | Pair to watch, default `USDT` / `USD` |
| `INTERVAL` | – | Seconds between price checks (default `60`) — how often you ping `/api/cron` |
| `CRON_SECRET` | ✅ | Random string that protects `/api/cron` and `/api/setup` |
| `WEBHOOK_SECRET` | recommended | Extra check on incoming Telegram updates |
| `KV_REST_API_URL` + `KV_REST_API_TOKEN` | recommended | Upstash/Redis store so merchants, group and settings survive cold starts |
| `PUBLIC_URL` | – | Only needed if `/api/setup` should register a domain other than the deployment URL |
| `AD_LINK_TEMPLATES` | – | JSON overrides for the exact-ad link templates |

> **Without a Redis/KV store** the bot still runs, but Vercel's filesystem is ephemeral: merchants,
> the group and settings are reset whenever the function cold-starts. In the Vercel dashboard open
> **Storage → Create → Upstash Redis** (or any Upstash database) and the `KV_REST_API_*` variables
> are added to the project automatically.

### 3. Register the webhook (once)

```
https://<your-app>.vercel.app/api/setup?key=<CRON_SECRET>
```

It calls `setWebhook` (with your `WEBHOOK_SECRET` if set), registers the `/start`, `/preview`,
`/setgroup`, `/cancel` commands and prints the result. Re-run it whenever the domain changes.

### 4. Schedule the price updates

`INTERVAL` seconds is only a hint — something has to *call* the endpoint:

| Option | Frequency | Where |
|---|---|---|
| **Vercel Cron** (Pro) | every minute | add to `vercel.json`: `"crons": [{"path": "/api/cron", "schedule": "* * * * *"}]` — Vercel sends `Authorization: Bearer $CRON_SECRET` |
| **cron-job.org / UptimeRobot** (free) | 1–5 min | create a monitor for `https://<your-app>.vercel.app/api/cron?key=<CRON_SECRET>` |
| **GitHub Actions** (free) | ~1 min | use the bundled [`cron-price-update.yml`](.github/workflows/cron-price-update.yml) and add a `CRON_URL` repository secret |
| **Vercel Cron** (Hobby) | once per day | same `crons` entry, but `schedule` must be daily on the free plan — not useful for prices |

The tick is cheap and idempotent: it only posts when prices actually changed, and it also deletes
the previous group message / expires messages that are older than `delete_after_hours`.

### Endpoints

| Endpoint | What it does |
|---|---|
| `GET /` | Status page: pair, storage backend, group, merchant count, setup checklist |
| `GET /api/health` | The same status as JSON |
| `POST /api/telegram` | Telegram webhook (verified with `WEBHOOK_SECRET` when set) |
| `GET /api/cron?key=…` | Scheduler tick (`?force=1` re-posts even if nothing changed) |
| `GET /api/setup?key=…` | Registers the webhook with Telegram |

### Notes & limits

* **Hobby plan**: 60 s max function duration, crons only once per day → use an external pinger (table above).
* Serverless functions sleep when idle: the first update after a while takes ~1 s longer (cold start).
* Long polling (`python bot.py`, Docker, systemd) still works exactly as before — the same codebase
  detects Vercel (`VERCEL=1`) and switches to webhook mode automatically.
* `ADMIN_IDS` is the only thing that can control the bot: keep the deployment URL private-ish, and
  keep `CRON_SECRET`/`WEBHOOK_SECRET` long and random.

---

## 🧪 Tests

```bash
pip install -r requirements.txt pytest
python -m pytest tests -q
```

The suite covers the ad-link templates, the Buy/Sell button targets, clickable prices, the
state backends and the serverless endpoints (including a real HTTP round-trip through
`api/index.py` — no Telegram calls are made).

---

## 🛠️ Manage

**systemd (Option A):**

```bash
sudo systemctl status p2p-bot     # is it running?
sudo journalctl -u p2p-bot -f     # live logs
sudo systemctl restart p2p-bot    # restart
sudo bash install.sh --reconfigure   # change token / pair / interval
sudo bash install.sh --update        # pull latest + restart
```

**Docker (Option B):**

```bash
docker compose ps             # status
docker compose logs -f        # live logs
docker compose restart        # restart
bash install-docker.sh --reconfigure   # change token / pair / interval
bash install-docker.sh --update        # pull latest + rebuild + restart
bash install-docker.sh --down          # stop container (keep data)
```

**Local / no systemd (Option C):**

```bash
tail -f ~/exchange-local/bot.log   # live logs (or $INSTALL_DIR/bot.log)
bash install-local.sh --stop       # stop (start again by re-running install-local.sh)
bash install-local.sh --reconfigure  # change token / pair / interval
bash install-local.sh --update        # pull latest + restart
bash install-local.sh --uninstall     # stop + remove autostart (keep data)
```

**Uninstall (keeps your data):**

```bash
# systemd install
curl -fsSL https://raw.githubusercontent.com/sarakmacbook/exchange/main/uninstall.sh | bash
# …or the same with wget
wget -qO- https://raw.githubusercontent.com/sarakmacbook/exchange/main/uninstall.sh | bash
# docker install
bash install-docker.sh --down
# local install
bash install-local.sh --uninstall
```

---

## 📁 Files

| File | Purpose |
|---|---|
| `bot.py` | Telegram bot (panel, buttons, auto-poster) |
| `exchanges.py` | Binance / Bybit / OKX / Bitget adapters + URL parser |
| `adlinks.py` | Exact-ad deep-link templates (Binance / Bybit / OKX / Bitget) |
| `storage.py` | State backends: `data.json` file, Upstash/Vercel-KV Redis, read-only fallback |
| `api/index.py` | Vercel entry point: Telegram webhook, `/api/cron`, `/api/health`, `/api/setup`, status page |
| `vercel.json` | Vercel routing (all paths → `api/index.py`) |
| `tests/` | pytest suite (links, buttons, storage, serverless endpoints) |
| `.github/workflows/` | CI (tests) + optional free scheduler that pings `/api/cron` |
| `install.sh` | One-click installer — systemd VPS |
| `install-docker.sh` | One-click installer — Docker Compose |
| `install-local.sh` | One-click installer — macOS / no systemd |
| `uninstall.sh` | Remove systemd service (keeps data) |
| `Dockerfile` / `docker-compose.yml` | Docker alternative |
| `config.json` | Auto-created: token, admins, pair, interval |
| `data.json` | Auto-created: group, merchants, last prices |

All three installers download what they need with **curl, wget or python3** (first one found — override with `DOWNLOADER=wget`), and fall back to the GitHub tarball when `git` is not installed.

## 📄 License

MIT
