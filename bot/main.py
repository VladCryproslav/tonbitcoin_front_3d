import asyncio
import config
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import Message, WebAppInfo, UserProfilePhotos
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.deep_linking import create_start_link, decode_payload
from datetime import datetime, timezone

def webapp_builder():
    builder = InlineKeyboardBuilder()
    builder.button(
        text='Start WebApp', web_app=WebAppInfo(
            url=config.WEB_APP,
        )
    )
    return builder.as_markup()

bot = Bot(config.TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message):
    await message.reply(
        '🏭 Welcome to Factory Bot!',
        reply_markup=webapp_builder()
    )


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())