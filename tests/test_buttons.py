"""Buy/Sell buttons and prices must point at the exact ad of the shown price."""


def _buttons(kb):
    return [b for row in kb.inline_keyboard for b in row]


def test_buttons_open_the_exact_ads(bot, merchant, prices):
    bot.state["merchants"][merchant.key] = merchant.__dict__
    kb = bot.report_keyboard(prices)
    urls = {b.text.split()[0]: b.url for b in _buttons(kb)}
    assert urls["🟢"] == "https://www.okx.com/p2p-markets/usd/sell-usdt?adId=260912150134999"
    assert urls["🔴"] == "https://www.okx.com/p2p-markets/usd/buy-usdt?adId=260912150134452"


def test_button_text_shows_the_prices_and_merchant(bot, merchant, prices):
    bot.state["merchants"][merchant.key] = merchant.__dict__
    texts = [b.text for b in _buttons(bot.report_keyboard(prices))]
    assert any("0.999" in t and "Fast_sonic" in t for t in texts)
    assert any("1.001" in t for t in texts)


def test_profile_mode_links_to_the_merchant_page(bot, merchant, prices):
    bot.state["settings"]["btn_link_mode"] = "profile"
    bot.state["merchants"][merchant.key] = merchant.__dict__
    urls = [b.url for b in _buttons(bot.report_keyboard(prices))]
    assert all(u == merchant.url for u in urls)


def test_missing_ad_id_falls_back_to_profile(bot, merchant):
    bot.state["merchants"][merchant.key] = merchant.__dict__
    r = {"sell": 1.0, "buy": 1.1, "sell_amount": None, "buy_amount": None,
         "sell_ad_id": None, "buy_ad_id": None, "error": None}
    url = bot.btn_url("sell", merchant, r)
    assert url == merchant.url


def test_custom_button_url_wins_and_gets_placeholders(bot, merchant, prices):
    bot.state["settings"]["btn_sell_url"] = "https://t.me/support?ad={AD_ID}&p={PRICE}"
    bot.state["merchants"][merchant.key] = merchant.__dict__
    r = prices[merchant.key]
    assert bot.btn_url("sell", merchant, r) == "https://t.me/support?ad=260912150134452&p=0.999"


def test_custom_ad_template_is_used(bot, merchant, prices):
    bot.state["settings"]["ad_link_templates"] = {"okx": "https://my.tld/ad/{AD_ID}/{TAKER_SIDE}"}
    bot.state["merchants"][merchant.key] = merchant.__dict__
    assert bot.btn_url("sell", merchant, prices[merchant.key]) == "https://my.tld/ad/260912150134452/buy"


def test_prices_in_the_post_are_clickable(bot, merchant, prices):
    bot.state["merchants"][merchant.key] = merchant.__dict__
    text = bot.report(prices)
    assert 'href="https://www.okx.com/p2p-markets/usd/sell-usdt?adId=260912150134999">1.001</a>' in text
    assert 'href="https://www.okx.com/p2p-markets/usd/buy-usdt?adId=260912150134452">0.999</a>' in text


def test_price_links_can_be_switched_off(bot, merchant, prices):
    bot.state["settings"]["price_links"] = False
    bot.state["merchants"][merchant.key] = merchant.__dict__
    text = bot.report(prices)
    assert "adId=" not in text
    assert "0.999" in text and "1.001" in text


def test_body_template_placeholders(bot, merchant, prices):
    bot.state["merchants"][merchant.key] = merchant.__dict__
    block = bot.apply_body_template(
        "{EXCHANGE}|{SELL}|{BUY}|{SELL_URL}|{BUY_AD_ID}", merchant, prices[merchant.key])
    assert block.startswith("Okx|0.999|1.001|https://www.okx.com/p2p-markets/usd/buy-usdt?adId=")
    assert block.endswith("|260912150134999")


def test_market_page_fallback_when_no_profile_url(bot, prices):
    from exchanges import Merchant
    m = Merchant("bybit", "123", "Nick", "USDT", "USD", "")
    r = {"sell": 1.0, "buy": None, "sell_amount": None, "buy_amount": None,
         "sell_ad_id": None, "buy_ad_id": None, "error": None}
    assert bot.btn_url("sell", m, r) == "https://www.bybit.com/en/p2p/buy/USDT/USD"


def test_broken_settings_do_not_break_rendering(bot, merchant, prices):
    """State written by an older/hand-edited version must not crash the bot."""
    bot.state["settings"]["ad_link_templates"] = "not-a-dict"
    bot.state["settings"]["btn_link_mode"] = "🎯"
    bot.state["merchants"][merchant.key] = merchant.__dict__
    assert bot.ad_templates()["okx"] == bot.AD_LINK_TEMPLATES["okx"]
    assert bot.link_mode() == "ad"
    assert bot.report(prices)


def test_state_migration_fills_new_keys(bot):
    from bot import DEFAULT_SETTINGS, empty_state
    state = empty_state()
    state["settings"] = {"show_liquidity": True}          # old data.json
    # simulate what load() does with the stored document
    for k, v in DEFAULT_SETTINGS.items():
        state["settings"].setdefault(k, v)
    assert state["settings"]["btn_link_mode"] == "ad"
    assert state["settings"]["show_liquidity"] is True


def test_every_menu_renders(bot, merchant, prices):
    """Every panel/menu screen must build without raising."""
    from telegram import InlineKeyboardMarkup
    bot.state["merchants"][merchant.key] = merchant.__dict__
    bot.state["group"] = -1001234567890
    bot.state["group_title"] = "My P2P group"
    for text in (bot.panel_text(), bot.settings_text(), bot.buttons_menu_text(),
                 bot.adlink_menu_text(), bot.custom_menu_text()):
        assert isinstance(text, str) and text.strip()
    for kb in (bot.panel(), bot.settings_kb(), bot.buttons_menu_kb(),
               bot.adlink_menu_kb(), bot.custom_menu_kb(), bot.list_kb(),
               bot.report_keyboard(prices)):
        assert isinstance(kb, InlineKeyboardMarkup) and kb.inline_keyboard
    # the ad-link screen lists one editor per supported exchange
    callbacks = [b.callback_data for row in bot.adlink_menu_kb().inline_keyboard for b in row]
    for ex in bot.EXCHANGE_NAMES:
        assert f"edit_adlink:{ex}" in callbacks
