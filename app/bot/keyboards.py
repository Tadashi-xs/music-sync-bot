from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Подключить Spotify")],
            [KeyboardButton(text="🎵 Добавить трек")],
            [KeyboardButton(text="📂 Мои треки"), KeyboardButton(text="🗑 Удалить треки")],
            [KeyboardButton(text="📊 Статистика")],
        ],
        resize_keyboard=True,
    )
