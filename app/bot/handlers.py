import html
import re
from datetime import datetime

from aiogram import types, F, Dispatcher
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from app.bot.keyboards import main_kb
from app.bot.states import States
from app.spotify.client import SpotifyUserClient
from app.spotify.oauth import get_auth_url
from app.spotify.oauth import ensure_token
from app.storage.memory import (
    USER_SPOTIFY,
    LAST_SHOWN,
    STATS,
    ARTIST_COUNTER,
)


def parse_numbers(text: str, max_n: int):
    nums = set(map(int, re.findall(r"\d+", text)))
    return sorted(n for n in nums if 1 <= n <= max_n)


def human_time(dt: datetime | None):
    if not dt:
        return "—"
    return dt.strftime("%d.%m.%Y %H:%M:%S")


def stats_for(tg: str):
    return STATS.setdefault(
        tg,
        {
            "added": 0,
            "deleted": 0,
            "first_add": None,
            "last_add": None,
        },
    )


async def get_spotify_client(tg: str) -> SpotifyUserClient:
    access_token = await ensure_token(tg)
    return SpotifyUserClient(access_token)


async def collect_tracks(tg: str, limit: int = 15):
    sp = await get_spotify_client(tg)
    meta = sp.get_saved_tracks(limit=1)
    total = meta.get("total", 0) if meta else 0

    tracks = []
    if total:
        offset = max(total - limit, 0)
        data = sp.get_saved_tracks(limit=limit, offset=offset)
        for item in data.get("items", []):
            tr = item["track"]
            tracks.append(
                {
                    "id": tr["id"],
                    "title": tr["name"],
                    "artist": ", ".join(a["name"] for a in tr["artists"]),
                }
            )

    LAST_SHOWN[tg] = tracks
    return tracks, total


async def start_handler(m: types.Message, state: FSMContext):
    await state.clear()
    tg = str(m.from_user.id)
    connected = "✅ подключён" if tg in USER_SPOTIFY else "❌ не подключён"

    await m.answer(
        f"👋 <b>Привет, {html.escape(m.from_user.first_name)}!</b>\n\n"
        f"🎧 Spotify: {connected}\n\n"
        "Я помогу управлять твоей библиотекой Spotify прямо из Telegram.",
        reply_markup=main_kb(),
        parse_mode="HTML",
    )


async def connect_spotify(m: types.Message):
    url = get_auth_url(str(m.from_user.id))
    await m.answer(
        f"🔐 <b>Авторизация Spotify</b>\n\n"
        f"<a href='{url}'>👉 Подключить Spotify</a>",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )



async def add_start(m: types.Message, state: FSMContext):
    if str(m.from_user.id) not in USER_SPOTIFY:
        await m.answer("❌ Сначала подключи Spotify")
        return

    await state.set_state(States.waiting_add)
    await m.answer("🎵 Введи название трека\nПример: Track Name / Artist - Track Name")


async def add_track(m: types.Message, state: FSMContext):
    tg = str(m.from_user.id)
    sp = await get_spotify_client(tg)

    track = sp.search_track_full(m.text)
    if not track:
        await m.answer("⚠️ Трек не найден")
        await state.clear()
        return

    if sp.is_track_saved(track["id"]):
        await m.answer("ℹ️ Этот трек уже есть в библиотеке")
        await state.clear()
        return

    sp.save_tracks([track["id"]])

    s = stats_for(tg)
    now = datetime.now()
    s["added"] += 1
    s["last_add"] = now
    s["first_add"] = s["first_add"] or now

    artist = ", ".join(a["name"] for a in track["artists"])
    ARTIST_COUNTER.setdefault(tg, {})
    ARTIST_COUNTER[tg][artist] = ARTIST_COUNTER[tg].get(artist, 0) + 1

    await m.answer_photo(
        track["album"]["images"][0]["url"],
        caption=(
            "✅ <b>Трек добавлен</b>\n\n"
            f"🎤 {html.escape(artist)}\n"
            f"🎵 <b>{html.escape(track['name'])}</b>"
        ),
        parse_mode="HTML",
    )

    await state.clear()


async def my_tracks(m: types.Message):
    tg = str(m.from_user.id)
    tracks, _ = await collect_tracks(tg)

    if not tracks:
        await m.answer("📭 У тебя нет сохранённых треков")
        return

    text = "🎧 <b>Последние треки:</b>\n\n"
    for i, t in enumerate(tracks, 1):
        text += f"{i}. {t['artist']} — {t['title']}\n"

    await m.answer(text, parse_mode="HTML")


async def delete_menu(m: types.Message, state: FSMContext):
    tg = str(m.from_user.id)
    tracks, _ = await collect_tracks(tg)

    if not tracks:
        await m.answer("📭 Удалять нечего")
        return

    text = "Введи номера треков для удаления:\n\n"
    for i, t in enumerate(tracks, 1):
        text += f"{i}. {t['artist']} — {t['title']}\n"

    await state.set_state(States.waiting_delete)
    await m.answer(text)


async def delete_tracks(m: types.Message, state: FSMContext):
    tg = str(m.from_user.id)
    shown = LAST_SHOWN.get(tg, [])
    nums = parse_numbers(m.text, len(shown))

    if not nums:
        await m.answer("❌ Неверный формат")
        return

    sp = await get_spotify_client(tg)
    deleted = []

    for i in sorted(nums, reverse=True):
        tr = shown[i - 1]
        sp.remove_saved_tracks([tr["id"]])
        stats_for(tg)["deleted"] += 1
        deleted.append(f"{tr['artist']} — {tr['title']}")

    deleted.reverse()

    await m.answer(
        "<b>Удалены треки:</b>\n\n" + "\n".join(deleted),
        parse_mode="HTML",
    )

    await state.clear()


async def statistics(m: types.Message):
    tg = str(m.from_user.id)
    s = stats_for(tg)
    _, total_tracks = await collect_tracks(tg)

    fav_artist = "—"
    if ARTIST_COUNTER.get(tg):
        fav_artist = max(ARTIST_COUNTER[tg], key=ARTIST_COUNTER[tg].get)

    days = max((datetime.now() - s["first_add"]).days, 1) if s["first_add"] else 1
    avg = round(s["added"] / days, 2)

    await m.answer(
        "📊 <b>Твоя статистика</b>\n\n"
        f"➕ Добавлено через бота: {s['added']}\n"
        f"🎶 Всего треков в Spotify: {total_tracks}\n"
        f"🗑 Удалено: {s['deleted']}\n\n"
        f"🎤 Любимый исполнитель: {fav_artist}\n\n"
        f"📅 Первый трек: {human_time(s['first_add'])}\n"
        f"🕒 Последний трек: {human_time(s['last_add'])}\n"
        f"⚡ Добавлений в день: {avg}",
        parse_mode="HTML",
    )


def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command("start"))

    dp.message.register(connect_spotify, F.text == "🔐 Подключить Spotify")

    dp.message.register(add_start, F.text == "🎵 Добавить трек")
    dp.message.register(add_track, States.waiting_add)

    dp.message.register(my_tracks, F.text == "📂 Мои треки")

    dp.message.register(delete_menu, F.text == "🗑 Удалить треки")
    dp.message.register(delete_tracks, States.waiting_delete)

    dp.message.register(statistics, F.text == "📊 Статистика")
