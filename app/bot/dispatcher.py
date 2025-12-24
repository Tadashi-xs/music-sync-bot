from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from typing import Tuple

def create_bot_and_dispatcher(token: str) -> Tuple[Bot, Dispatcher]:
    bot = Bot(token=token)
    dp = Dispatcher(storage=MemoryStorage())
    dp["bot"] = bot
    return bot, dp
