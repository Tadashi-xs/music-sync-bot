from unittest.mock import patch
from app.bot.dispatcher import create_bot_and_dispatcher
from aiogram import Bot, Dispatcher


def test_create_bot_and_dispatcher_returns_objects():
    with patch("aiogram.client.bot.validate_token", return_value=True):
        bot, dp = create_bot_and_dispatcher("123456:TEST_TOKEN")

    assert isinstance(bot, Bot)
    assert isinstance(dp, Dispatcher)
