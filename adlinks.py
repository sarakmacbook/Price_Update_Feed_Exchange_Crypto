"""Deep links that open the *exact* P2P advertisement a price came from.

The bot remembers the ad id of the best BUY ad and the best SELL ad it found
for every merchant (see ``exchanges.fetch``).  Those ids are turned into public
web links here so a Buy/Sell button opens that specific ad — the one whose
price is printed in the post — instead of the merchant's profile page.

Templates are plain strings containing placeholders and can be overridden:

* from the bot UI  →  Settings ▸ 🔗 Ad links (per exchange)
* from the env     →  ``AD_LINK_TEMPLATES={"binance": "https://…{AD_ID}"}`` (JSON)

Placeholders
------------
``{AD_ID}``      advertisement id as returned by the exchange API
``{URL}``        merchant profile URL that was pasted into the bot
``{NICK}``       merchant nickname
``{ASSET}``      e.g. ``USDT``      ``{ASSET_LOWER}``  e.g. ``usdt``
``{FIAT}``       e.g. ``USD``       ``{FIAT_LOWER}``   e.g. ``usd``
``{SIDE}``       ``buy`` / ``sell`` from the *merchant's* point of view
``{TAKER_SIDE}`` ``buy`` / ``sell`` from the *bot user's* point of view
``{ACTION_TYPE}`` Bybit style numeric side (``1`` = merchant sells)
"""

from __future__ import annotations

import re

EXCHANGE_NAMES = ("binance", "bybit", "okx", "bitget")

# ── default templates ───────────────────────────────────────────────────────
# binance : documented ad link → https://c2c.binance.com/en/adv?code=<advNo>
# okx     : /p2p-markets/<fiat>/<buy|sell>-<asset>   (taker side) + ad hint
# bybit   : /en/p2p/<buy|sell>/<ASSET>/<FIAT>        (taker side) + ad hint
# bitget  : /p2p-trade?fiatName=<FIAT>&coinName=<ASSET>         + ad hint
# The exchanges that do not document an ad-level parameter simply ignore the
# extra ``adId`` / ``advId`` hint, so the link still lands on the right market,
# side and pair.  Override a template if an exchange ever changes its routes.
AD_LINK_TEMPLATES = {
    "binance": "https://c2c.binance.com/en/adv?code={AD_ID}",
    "bybit":   "https://www.bybit.com/en/p2p/{TAKER_SIDE}/{ASSET}/{FIAT}"
               "?actionType={ACTION_TYPE}&token={ASSET}&fiat={FIAT}&adId={AD_ID}",
    "okx":     "https://www.okx.com/p2p-markets/{FIAT_LOWER}/{TAKER_SIDE}-{ASSET_LOWER}?adId={AD_ID}",
    "bitget":  "https://www.bitget.com/p2p-trade?fiatName={FIAT}&coinName={ASSET}"
               "&side={TAKER_SIDE}&advId={AD_ID}",
}

#: exchanges whose default template really is a single-ad link (not just a hint)
EXACT_AD_EXCHANGES = frozenset(
    ex for ex, tpl in AD_LINK_TEMPLATES.items() if tpl.rstrip().endswith("{AD_ID}")
)

#: market pages used when a merchant has no profile URL stored
MARKET_LINK_TEMPLATES = {
    "binance": "https://p2p.binance.com/en/trade/{TAKER_SIDE}/{ASSET}?fiat={FIAT}",
    "bybit":   "https://www.bybit.com/en/p2p/{TAKER_SIDE}/{ASSET}/{FIAT}",
    "okx":     "https://www.okx.com/p2p-markets/{FIAT_LOWER}/{TAKER_SIDE}-{ASSET_LOWER}",
    "bitget":  "https://www.bitget.com/p2p-trade?fiatName={FIAT}&coinName={ASSET}",
}

_PLACEHOLDER = re.compile(r"\{([A-Z_]+)\}")


def taker_side(side: str) -> str:
    """Merchant side → the side *you* take when clicking the ad."""
    return "buy" if str(side).lower() == "sell" else "sell"


def action_type(side: str) -> str:
    """Bybit numeric side used both by its API and its market page."""
    return "1" if str(side).lower() == "sell" else "0"


def placeholders(asset: str = "", fiat: str = "", side: str = "",
                 ad_id: str = "", nick: str = "", profile_url: str = "") -> dict:
    side = (side or "").lower()
    return {
        "AD_ID": str(ad_id or ""),
        "URL": profile_url or "",
        "NICK": nick or "",
        "ASSET": (asset or "").upper(),
        "ASSET_LOWER": (asset or "").lower(),
        "FIAT": (fiat or "").upper(),
        "FIAT_LOWER": (fiat or "").lower(),
        "SIDE": side,
        "SIDE_UPPER": side.upper(),
        "TAKER_SIDE": taker_side(side),
        "ACTION_TYPE": action_type(side),
    }


def render_template(tpl: str, values: dict) -> str:
    """Single-pass ``{PLACEHOLDER}`` substitution (inserted values are never re-scanned)."""
    if not tpl:
        return ""
    return _PLACEHOLDER.sub(lambda m: str(values.get(m.group(1), m.group(0))), tpl)


def resolve_templates(overrides: dict | None = None) -> dict:
    """Default templates merged with (valid) user overrides."""
    templates = dict(AD_LINK_TEMPLATES)
    if isinstance(overrides, dict):
        for ex, tpl in overrides.items():
            if ex in templates and isinstance(tpl, str) and tpl.strip():
                templates[ex] = tpl.strip()
    return templates


def ad_link(exchange: str, ad_id, asset: str, fiat: str, side: str,
            templates: dict | None = None, nick: str = "", profile_url: str = "") -> str | None:
    """Public URL of one specific ad, or ``None`` when we have no id/template."""
    if ad_id in (None, "", "None"):
        return None
    tpl = (templates or AD_LINK_TEMPLATES).get(str(exchange).lower())
    if not tpl:
        return None
    url = render_template(tpl, placeholders(asset, fiat, side, ad_id, nick, profile_url))
    return url if url.startswith("http") else None


def market_link(exchange: str, asset: str, fiat: str, side: str) -> str | None:
    """Market page for the pair/side — last resort when a merchant has no URL."""
    tpl = MARKET_LINK_TEMPLATES.get(str(exchange).lower())
    if not tpl:
        return None
    return render_template(tpl, placeholders(asset, fiat, side)) or None


def template_is_exact(tpl: str) -> bool:
    """True when a template contains the ad id, i.e. opens one specific ad."""
    return bool(tpl) and "{AD_ID}" in tpl
