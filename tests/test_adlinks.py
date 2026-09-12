"""Exact-ad deep links."""

import adlinks


def test_taker_side_and_action_type():
    assert adlinks.taker_side("sell") == "buy"      # merchant sells → you buy
    assert adlinks.taker_side("buy") == "sell"
    assert adlinks.action_type("sell") == "1"       # Bybit API side
    assert adlinks.action_type("buy") == "0"


def test_binance_link_is_the_single_ad():
    url = adlinks.ad_link("binance", "243894123", "USDT", "USD", "sell")
    assert url == "https://c2c.binance.com/en/adv?code=243894123"
    assert adlinks.template_is_exact(adlinks.AD_LINK_TEMPLATES["binance"])


def test_bybit_link_uses_taker_side_and_pair():
    url = adlinks.ad_link("bybit", "abc123", "USDT", "USD", "buy")
    assert url.startswith("https://www.bybit.com/en/p2p/sell/USDT/USD?")
    assert "actionType=0" in url and "adId=abc123" in url


def test_okx_link_follows_the_taker_side():
    sell = adlinks.ad_link("okx", "260912150134452", "USDT", "USD", "sell")
    buy = adlinks.ad_link("okx", "260912150134452", "USDT", "USD", "buy")
    assert sell.startswith("https://www.okx.com/p2p-markets/usd/buy-usdt?")
    assert buy.startswith("https://www.okx.com/p2p-markets/usd/sell-usdt?")


def test_bitget_link_keeps_fiat_and_coin():
    url = adlinks.ad_link("bitget", "3784051421", "USDT", "USD", "sell")
    assert "fiatName=USD" in url and "coinName=USDT" in url and "advId=3784051421" in url


def test_no_ad_id_means_no_ad_link():
    assert adlinks.ad_link("okx", None, "USDT", "USD", "sell") is None
    assert adlinks.ad_link("okx", "", "USDT", "USD", "sell") is None
    assert adlinks.ad_link("mexc", "1", "USDT", "USD", "sell") is None


def test_overrides_win_and_keep_defaults():
    templates = adlinks.resolve_templates({"okx": "https://example.com/ad/{AD_ID}"})
    assert templates["okx"] == "https://example.com/ad/{AD_ID}"
    assert templates["binance"] == adlinks.AD_LINK_TEMPLATES["binance"]
    # junk overrides are ignored
    assert adlinks.resolve_templates({"okx": ""})["okx"] == adlinks.AD_LINK_TEMPLATES["okx"]
    assert adlinks.resolve_templates(None)["bitget"] == adlinks.AD_LINK_TEMPLATES["bitget"]


def test_render_template_leaves_unknown_placeholders_alone():
    out = adlinks.render_template("https://x/{AD_ID}?n={NICK}&keep={NOPE}",
                                  adlinks.placeholders("USDT", "USD", "sell", "7", "Bob"))
    assert out == "https://x/7?n=Bob&keep={NOPE}"


def test_market_link_is_not_ad_specific():
    url = adlinks.market_link("binance", "USDT", "USD", "sell")
    assert url.startswith("https://p2p.binance.com/en/trade/buy/USDT?fiat=USD")
    assert "{AD_ID}" not in url
