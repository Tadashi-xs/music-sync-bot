import asyncio
from dotenv import load_dotenv

from app.config import load_config
from app.bot import create_bot_and_dispatcher, register_handlers
from app.spotify.oauth import start_oauth_server


async def main():
    load_dotenv()
    config = load_config()

    bot, dp = create_bot_and_dispatcher(config.telegram.token)
    register_handlers(dp)
    await start_oauth_server()

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
