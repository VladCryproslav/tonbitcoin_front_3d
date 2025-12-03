import asyncio
from datetime import datetime, timedelta
import io
from itertools import cycle
import json
import logging
import threading
import traceback

from aiogram import Bot, Dispatcher, executor, types
from aiogram import types
import aiogram
from tgbot.mail.config import ADMINS, BOT_TOKEN
from tgbot.mail.filters import Admin
from tgbot.mail.middlewares import UsersMiddleware
from aiogram.dispatcher import FSMContext
import csv

from aiogram.types import (
    InputFile,
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ContentType,
    BotCommand,
)
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from tgbot.mail.models.settings import Setting
from tgbot.mail.models.user import User
from tgbot.mail.users import count_users, delete_user, get_user, get_user_ids, get_users
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from aiogram.utils.exceptions import BotBlocked

import csv
from datetime import datetime
from django.utils import timezone
import os
import time
import traceback
from pytonapi import AsyncTonapi
import django
import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import UserProfile

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] {%(filename)s:%(funcName)s:%(lineno)d} %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)

jobstores = {"default": SQLAlchemyJobStore(url="sqlite:///tgbot/mail/jobs.sqlite")}
scheduler = AsyncIOScheduler(jobstores=jobstores)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
mail_bot = Bot(token=BOT_TOKEN)

dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(UsersMiddleware())
dp.filters_factory.bind(Admin)


@dp.message_handler(commands=["id"], state="*")
async def get_id(message: types.Message):
    await message.answer(message.from_user.id)


@dp.message_handler(lambda msg: msg.text == "/chat_id", state="*")
async def chat_id_get(message: Message, state: FSMContext):
    await message.answer(message.chat.id)


class MailingStates(StatesGroup):
    msg = State()
    idle = State()
    change_kb = State()
    delete_time = State()
    amount = State()
    step = State()
    fast = State()


class StartMailingStates(StatesGroup):
    # num = State()
    # chat_id = State()
    menu = State()
    # link = State()
    msg = State()
    idle = State()
    change_kb = State()
    delete_date = State()
    after_mail = State()


class AddAdminStates(StatesGroup):
    user_id = State()


class RemoveAdminStates(StatesGroup):
    user_id = State()


def get_admin_markup():
    markup = InlineKeyboardMarkup(row_width=1)

    # markup.add(InlineKeyboardButton("Скачати базу даних 📁", callback_data="get_db"))
    # markup.add(
    #     InlineKeyboardButton("Порахувати користувачів 👥", callback_data="get_users")
    # )
    # markup.add(
    #     InlineKeyboardButton("Почистити неактивних людей", callback_data="clear_users")
    # )
    # markup.add(InlineKeyboardButton("Посчитать пользователей БЫСТРО 👥 (beta)", callback_data="get_users_fast"))
    markup.add(InlineKeyboardButton("Зробити розсилку 📬", callback_data="make_mail"))
    # markup.add(
    #     InlineKeyboardButton("Настройка привітань ✉️", callback_data="settings_start")
    # )
    # markup.add(InlineKeyboardButton("Добавити адміна", callback_data="add_admin"))
    # markup.add(InlineKeyboardButton("Видалити адміна", callback_data="delete_admin"))
    return markup


@dp.callback_query_handler(text="add_admin", is_admin=True)
async def add_admin(call: CallbackQuery):
    await call.answer()
    await AddAdminStates.user_id.set()
    await call.message.answer("Введіть айді користувача", reply_markup=get_quit_kb())


@dp.message_handler(state=AddAdminStates.user_id, is_admin=True)
async def add_admin(message: Message, state: FSMContext):
    if not message.text.isdecimal():
        await message.answer("Це не число")
        return
    user = User.get_or_none(id=int(message.text))
    if user is None:
        await message.answer("Такого користувача немає в БД")
        return
    user.is_admin = True
    user.save()
    await state.finish()
    await message.answer("Успішно")


@dp.callback_query_handler(text="delete_admin", is_admin=True)
async def add_admin(call: CallbackQuery):
    await call.answer()
    await RemoveAdminStates.user_id.set()
    await call.message.answer("Введіть айді користувача", reply_markup=get_quit_kb())


@dp.message_handler(state=RemoveAdminStates.user_id, is_admin=True)
async def add_admin(message: Message, state: FSMContext):
    if not message.text.isdecimal():
        await message.answer("Це не число")
        return
    user = User.get_or_none(id=int(message.text))
    if user is None:
        await message.answer("Такого користувача немає в БД")
        return
    user.is_admin = False
    user.save()
    await state.finish()
    await message.answer("Успішно")


def get_quit_btn(text="Відміна"):
    return InlineKeyboardButton(text, callback_data="quit")


def get_quit_kb(*args, **kwargs):
    return InlineKeyboardMarkup().add(get_quit_btn(*args, **kwargs))


# @dp.callback_query_handler(text="settings_start", is_admin=True)
# async def _settings_start(call: CallbackQuery):
#     await call.answer()
#     settings = Setting.select().execute()
#     amount = str(len(settings))
#     kb = get_quit_kb()
#     await call.message.answer(f"У вас сейчас {amount} начальных сообщений\nНапишите ID начального сообщения, которое хотите изменить (доступные: {', '.join([str(s.id) for s in settings])})\nЕсли хотите добавить новое начальное сообщение, напишите 0", reply_markup=kb)
#     await StartMailingStates.num.set()


@dp.callback_query_handler(text="quit", state="*")
async def _quit(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    await call.message.answer("Відмінено")


# @dp.message_handler(lambda msg: msg.text == "0", is_admin=True, state=StartMailingStates.num)
# async def _settings_start(message: Message, state: FSMContext):
#     await StartMailingStates.chat_id.set()
#     await message.answer("Отправьте ID канала или ссылку в формате @username или перешлите пост с канала")


from aiogram.utils.exceptions import ChatNotFound

# @dp.message_handler(is_admin=True, state=StartMailingStates.chat_id)
# async def _settings_start(message: Message, state: FSMContext):
#     if message.is_forward():
#         chat_id = message.forward_from_chat.id
#     else:
#         chat_id = message.text
#     try:
#         link = await bot.create_chat_invite_link(chat_id, name="Bot Link",creates_join_request=True)
#     except ChatNotFound:
#         await message.answer("Чат или канал не найден!")
#         return
#     num = Setting.insert(link=link.invite_link).execute()
#     await message.answer(f"Ссылка для приглашения: {link.invite_link}")
#     await menu_msg(num, message, state)


async def menu_msg(num, message, state, call_user_id):
    setting: Setting = Setting.get_or_none(id=num)
    if setting is None:
        set_id = Setting.insert().execute()
        setting: Setting = Setting.get_or_none(id=set_id)

    await StartMailingStates.menu.set()
    try:
        start_kb = load_kb(setting.start_kb)
        await bot.copy_message(
            call_user_id,
            setting.start_from_user_id,
            setting.start_msg_id,
            reply_markup=start_kb,
        )
    except:
        pass
        # await message.answer("Привітання не настроєно")

    kb = InlineKeyboardMarkup(row_width=1)
    # kb.add(InlineKeyboardButton("Изменить ссылку 🔗", callback_data="change_link"))
    kb.add(
        InlineKeyboardButton("Змінити повідомлення ✉️", callback_data="change_default")
    )
    if num == 1:
        kb.add(
            InlineKeyboardButton(
                "Налаштування 2 привітання ✉️", callback_data="change_mail_after"
            )
        )
    else:
        kb.add(
            InlineKeyboardButton(
                "Налаштувати час надсилання 2 привітання ✉️",
                callback_data="change_mail_date_after",
            )
        )
    kb.add(
        InlineKeyboardButton(
            "Добавити/видалити кнопку ⌨️", callback_data="change_start_kb"
        )
    )
    kb.add(
        InlineKeyboardButton(
            "Настроїти видалення привітання", callback_data="change_delete_kb"
        )
    )
    change_start_text = ""
    if setting.send_start:
        change_start_text = "Виключити привітання"
    else:
        change_start_text = "Включити привітання"
    kb.add(InlineKeyboardButton(change_start_text, callback_data="change_start"))
    kb.add(get_quit_btn("Вихід"))

    await message.answer(f"Меню для привітань {setting.id}", reply_markup=kb)


@dp.callback_query_handler(text="settings_start", is_admin=True)
async def _settings_start(call: CallbackQuery, state: FSMContext):
    await state.update_data(setting_id=1)
    await menu_msg(1, call.message, state, call.from_user.id)


@dp.callback_query_handler(
    text="change_mail_after", state=StartMailingStates.menu, is_admin=True
)
async def _settings_start(call: CallbackQuery, state: FSMContext):
    await state.update_data(setting_id=2)
    await menu_msg(2, call.message, state, call.from_user.id)


@dp.callback_query_handler(
    text="change_mail_date_after", state=StartMailingStates.menu, is_admin=True
)
async def _change_delete_kb(call: CallbackQuery):
    await StartMailingStates.after_mail.set()
    await call.answer()
    await call.message.answer(
        "Введіть час через який відправити розсилку, в форматі гг:хх:сс. Щоб повідомлення відправилось зразу, напишіть 00:00:00"
    )


@dp.message_handler(is_admin=True, state=StartMailingStates.after_mail)
async def _confirm_make_mail(message: Message, state: FSMContext):
    setting: Setting = Setting.get(id=1)
    try:
        if message.text != "0":
            time = datetime.strptime(message.text, "%H:%M:%S")
    except:
        await message.answer("Неправильний формат")
        return
    await StartMailingStates.menu.set()
    setting.mail_after = message.text
    setting.save()
    await message.answer("Успішно!")


@dp.callback_query_handler(
    text="change_delete_kb", state=StartMailingStates.menu, is_admin=True
)
async def _change_delete_kb(call: CallbackQuery):
    await StartMailingStates.delete_date.set()
    await call.answer()
    await call.message.answer(
        "Введіть час, через який видалити повідомлення, в форматі гг:хх:сс. Щоб повідомлення не видалялось, напишіть 0"
    )


@dp.message_handler(is_admin=True, state=StartMailingStates.delete_date)
async def _confirm_make_mail(message: Message, state: FSMContext):
    setting = Setting.get(id=await get_state_set_id(state))
    try:
        if message.text != "0":
            time = datetime.strptime(message.text, "%H:%M:%S")
    except:
        await message.answer("Неправильний формат")
        return
    await StartMailingStates.menu.set()
    setting.start_delete = message.text
    setting.save()
    await message.answer("Успішно!")


# =======


@dp.message_handler(is_admin=True, commands=["test"])
async def _confirm_make_mail(message: Message, state: FSMContext):
    msg = await message.answer(f"Рахуємо..")
    users = get_users()
    active = 0
    count = 0
    for user in users:
        if count % 10 == 0:
            await msg.edit_text(f"Рахуємо.. {count}, {active}")
        count += 1
        try:
            if await bot.send_chat_action(user.id, "typing"):
                active += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            print(e)
            if "Retry" in e.__class__.__name__:
                print(e)

    await message.answer(
        f"Загальна кількість: {count}\nАктивних користувачів: {active}"
    )


@dp.callback_query_handler(
    text="change_start", state=StartMailingStates.menu, is_admin=True
)
async def _change_start(call: CallbackQuery, state: FSMContext):
    setting = Setting.get(id=await get_state_set_id(state))
    setting.send_start = not setting.send_start
    setting.save()
    text = (
        "Ви включили привітання!" if setting.send_start else "Ви виключили привітання!"
    )
    await call.answer()
    await call.message.answer(text)


# @dp.callback_query_handler(text="change_link",  state=StartMailingStates.menu, is_admin=True)
# async def _change_default(call: CallbackQuery):
#     await StartMailingStates.link.set()
#     await call.answer()
#     await call.message.answer("Отправьте ссылку по которой будет приходить начальное сообщение")

# @dp.message_handler(is_admin=True, state=StartMailingStates.link, content_types=ContentType.ANY)
# async def _confirm_make_mail(message: Message, state: FSMContext):
#     set_id = await get_state_set_id(state)
#     setting:Setting = Setting.get(id=set_id)
#     prev_link = setting.link
#     setting.link=message.text
#     setting.save()
#     await StartMailingStates.menu.set()
#     await message.answer(f"Успешно изменено!\nБыло: {prev_link}\nСтало: {setting.link}")


@dp.callback_query_handler(
    text="change_default", state=StartMailingStates.menu, is_admin=True
)
async def _change_default(call: CallbackQuery):
    await StartMailingStates.msg.set()
    await call.answer()
    await call.message.answer("Відправте повідомлення для привітання")


@dp.message_handler(
    is_admin=True, state=StartMailingStates.msg, content_types=ContentType.ANY
)
async def _confirm_make_mail(message: Message, state: FSMContext):
    set_id = await get_state_set_id(state)
    setting = Setting.get(id=set_id)
    setting.start_from_user_id = message.from_user.id
    setting.start_msg_id = message.message_id
    setting.save()
    await StartMailingStates.menu.set()
    await message.answer("Успішно змінено!")


@dp.callback_query_handler(text="change_start_kb", state=StartMailingStates.menu)
async def _process_change_kb(call: CallbackQuery, state: FSMContext):
    await StartMailingStates.change_kb.set()
    await call.answer()
    await call.message.answer(
        """
Відправте кнопки в форматі (приклад):
Кнопка 1 - http://example1.com | Кнопка 2 - http://example2.com
Кнопка 3 - http://example3.com | Кнопка 4 - http://example4.com
Кнопка 1 і Кнопка 2 знаходяться в одному рядку, Кнопка 1 і Кнопка 3 в одному стовпці
    """
    )


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


async def send_msg(user_id, from_user, msg_id, kb, time):
    while True:
        try:
            sent_msg = await bot.copy_message(
                user_id, from_user, msg_id, reply_markup=kb
            )
            try:
                if time is not None:
                    date = datetime.now() + timedelta(
                        seconds=time.second, minutes=time.minute, hours=time.hour
                    )
                    scheduler.add_job(
                        delete_msg,
                        trigger=DateTrigger(date),
                        args=(user_id, sent_msg.message_id),
                        id=f"delete_msg_{user_id}_{msg_id}",
                    )
            except:
                pass
            return
        except aiogram.utils.exceptions.RetryAfter as e:
            await asyncio.sleep(e.timeout)
        except Exception:
            pass


async def get_state_set_id(state: FSMContext):
    return (await state.get_data())["setting_id"]


@dp.message_handler(state=StartMailingStates.change_kb)
async def _process_change_kb_end(message: Message, state: FSMContext):
    text = message.text
    kb = InlineKeyboardMarkup(row_width=1)
    try:
        btns = text.split("\n")
        for row in btns:
            btns = row.split("|")
            btns = [
                InlineKeyboardButton(
                    btn.split("-")[0].strip(), url=btn.split("-")[1].strip()
                )
                for btn in btns
            ]
            kb.row(*btns)
        setting: Setting = Setting.get(await get_state_set_id(state))
        setting.start_kb = kb.as_json()
        setting.save()
        await StartMailingStates.menu.set()
        await bot.copy_message(
            message.from_user.id,
            setting.start_from_user_id,
            setting.start_msg_id,
            reply_markup=kb,
        )
    except:
        await message.answer("Неправильний формат")
        return
    await message.answer("Успішно змінено!")


def load_kb(kb):
    if kb is None:
        return None
    start_kb = json.loads(kb)["inline_keyboard"]
    start_kb = InlineKeyboardMarkup(inline_keyboard=start_kb) if start_kb else None
    return start_kb


async def send_start_msg(send_to, setting_num):
    # if chat_id != 0:
    #     c = UserChannel.get_or_none(user_id=send_to, channel_id=chat_id)
    #     if c is not None:
    #         return
    setting: Setting = Setting.get_or_none(id=setting_num)
    if setting is None or not setting.start_msg_id:
        # await notify_admins("Привітання не настроєно")
        return
    if not setting.send_start:
        return
    delete_time = ""
    if setting.start_delete != "0":
        try:
            delete_time = datetime.strptime(setting.start_delete, "%H:%M:%S")
        except ValueError:
            await notify_admins(
                f"ID: {setting.id}. Неправильний формат видалення повідомлення: {setting.start_delete}"
            )
    mail_after = ""
    if setting.mail_after != "0":
        try:
            mail_after = datetime.strptime(setting.mail_after, "%H:%M:%S")
        except ValueError:
            await notify_admins(
                f"ID: {setting.id}. Неправильний формат дати розсилки повідомлення: {setting.start_delete}"
            )

    start_kb = load_kb(setting.start_kb) if setting.start_kb else None
    try:
        sent_msg = await bot.copy_message(
            send_to,
            setting.start_from_user_id,
            setting.start_msg_id,
            reply_markup=start_kb,
        )
        # User.update(step=User.step + 1).where(User.id == true_user_id).execute()
        # UserChannel.insert(user_id=true_user_id, channel_id=chat_id).execute()
        if setting_num == 1:
            date = datetime.now() + timedelta(
                seconds=mail_after.second,
                minutes=mail_after.minute,
                hours=mail_after.hour,
            )
            scheduler.add_job(
                send_start_msg,
                trigger=DateTrigger(date),
                args=(send_to, 2),
                id=f"mail_after_start_{send_to}_{sent_msg.message_id}",
            )
        if delete_time:
            date = datetime.now() + timedelta(
                seconds=delete_time.second,
                minutes=delete_time.minute,
                hours=delete_time.hour,
            )
            scheduler.add_job(
                delete_msg,
                trigger=DateTrigger(date),
                args=(send_to, sent_msg.message_id),
                id=f"delete_msg_{send_to}_{sent_msg.message_id}",
            )

    except Exception as e:
        logging.error(traceback.format_exc())


# =======


@dp.message_handler(commands=["adm", "admin"], is_admin=True)
async def _start(message: Message):
    await message.answer("Адмінка відкрита", reply_markup=get_admin_markup())


@dp.callback_query_handler(text="get_db", is_admin=True)
async def _export_users(call: CallbackQuery):
    count = count_users()

    with open("users.csv", "w", encoding="UTF8", newline="") as f:
        writer = csv.writer(f)

        writer.writerow(["id", "username", "created_at"])

        for user in get_users():
            writer.writerow([user.id, user.username, user.created_at])

    text_file = InputFile("users.csv", filename="users.csv")
    await call.answer()
    await call.message.answer_document(text_file)
    with open("database.sqlite3", "rb") as f:
        await call.message.answer_document(f)


@dp.callback_query_handler(text="clear_users", is_admin=True)
async def _users_count(call: CallbackQuery):
    msg = await call.message.answer(f"Видаляєм неактивних..")
    users = get_users()
    active = 0
    non_active = 0
    count = 0
    for user in users:
        if count % 50 == 0:
            await msg.edit_text(
                f"Рахуємо.. {count} всього, {active} активних, {non_active} неактивних видалено"
            )
        count += 1
        try:
            if await bot.send_chat_action(user.id, "typing"):
                active += 1
            # await asyncio.sleep(0.05)
        except Exception as e:
            delete_user(user.id)
            non_active += 1

    await call.message.answer(
        f"Загальна кількість: {count}\nАктивних користувачів: {active}, видалено неактивних: {non_active}"
    )


@dp.callback_query_handler(text="get_users", is_admin=True)
async def _users_count(call: CallbackQuery):
    msg = await call.message.answer(f"Рахуємо..")
    users = get_users()
    active = 0
    count = 0
    for user in users:
        if count % 10 == 0:
            await msg.edit_text(f"Рахуємо.. {count} всього, {active} активних")
        count += 1
        try:
            if await bot.send_chat_action(user.id, "typing"):
                active += 1
            await asyncio.sleep(0.1)
        except Exception as e:
            if "Retry" in e.__class__.__name__:
                print(e.__class__.__name__)

    await call.message.answer(
        f"Загальна кількість: {count}\nАктивних користувачів: {active}"
    )


fast_user_count = {"count": 0, "active": 0}


async def check_is_active(user_id):
    try:
        if await bot.send_chat_action(user_id, "typing"):
            fast_user_count["active"] += 1
    except Exception:
        pass
    finally:
        fast_user_count["count"] += 1


@dp.callback_query_handler(text="get_users_fast", is_admin=True)
async def _users_count(call: CallbackQuery):
    await call.answer()
    msg = await call.message.answer(f"Рахуємо..")
    all_users = get_users()

    for users in chunks(all_users, 25):
        for user in users:
            asyncio.create_task(check_is_active(user.id))
        await asyncio.sleep(1)
        await msg.edit_text(
            f"Рахуємо... Всього {fast_user_count['count']}, активних: {fast_user_count['active']}"
        )
    await call.message.answer(
        f"Загальна кількість: {fast_user_count['count']}\nАктивних користувачів: {fast_user_count['active']}"
    )


@dp.callback_query_handler(text="make_mail", is_admin=True)
async def _make_mail(call: CallbackQuery, state: FSMContext):
    await MailingStates.msg.set()
    await call.answer()
    await call.message.answer("Відправте повідомлення для розсилки")


def get_mail_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(
        InlineKeyboardButton("Добавити/видалити кнопки ⌨️", callback_data="change_kb")
    )
    kb.add(
        InlineKeyboardButton(
            "Додати час видалення розсилки 📅", callback_data="add_delete_time"
        )
    )
    kb.add(InlineKeyboardButton("Відмінити розсилку ❌", callback_data="cancel_mail"))
    kb.add(
        InlineKeyboardButton("Підтвердити розсилку ✅", callback_data="confirm_mail")
    )
    return kb


@dp.message_handler(
    is_admin=True, state=MailingStates.msg, content_types=ContentType.ANY
)
async def _confirm_make_mail(message: Message, state: FSMContext):
    await MailingStates.idle.set()
    await state.update_data(msg_id=message.message_id, orig_msg=message)
    kb = get_mail_kb()
    await message.answer("Меню дій", reply_markup=kb)


@dp.callback_query_handler(text="add_delete_time", state=MailingStates.idle)
async def _process_change_kb(call: CallbackQuery, state: FSMContext):
    await MailingStates.delete_time.set()
    await call.message.answer(
        "Введіть час, через яке видалити повідомлення, в форматі гг:хх:сс"
    )


@dp.message_handler(is_admin=True, state=MailingStates.delete_time)
async def _confirm_make_mail(message: Message, state: FSMContext):
    try:
        time = datetime.strptime(message.text, "%H:%M:%S")
    except:
        await message.answer("Неправильний формат")
        return
    await state.update_data(time=time)
    await MailingStates.idle.set()
    kb = get_mail_kb()
    await message.answer("Меню дій", reply_markup=kb)


@dp.callback_query_handler(text="change_kb", state=MailingStates.idle)
async def _process_change_kb(call: CallbackQuery, state: FSMContext):
    await MailingStates.change_kb.set()
    await call.answer()
    await call.message.answer(
        """
Відправте кнопки в форматі (приклад):
Кнопка 1 - http://example1.com | Кнопка 2 - http://example2.com
Кнопка 3 - http://example3.com | Кнопка 4 - http://example4.com
Кнопка 1 і Кнопка 2 знаходяться в одному рядку, Кнопка 1 і Кнопка 3 в одному стовпці
    """
    )


@dp.message_handler(state=MailingStates.change_kb)
async def _process_change_kb_end(message: Message, state: FSMContext):
    text = message.text
    kb = InlineKeyboardMarkup(row_width=1)
    try:
        btns = text.split("\n")
        for row in btns:
            btns = row.split("|")
            btns = [
                InlineKeyboardButton(
                    btn.split("-")[0].strip(), url=btn.split("-")[1].strip()
                )
                for btn in btns
            ]
            kb.row(*btns)
        async with state.proxy() as data:
            new_msg_id = await bot.copy_message(
                message.from_user.id,
                message.from_user.id,
                data["msg_id"],
                reply_markup=kb,
            )
            await MailingStates.idle.set()
            data["msg_id"] = new_msg_id.message_id
            data["kb"] = kb
    except:
        await message.answer("Неправильний формат")
        return
    kb = get_mail_kb()
    await message.answer("Меню дій", reply_markup=kb)


@dp.callback_query_handler(text="cancel_mail", state=MailingStates.idle)
async def _process_cancel_mail(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text("Відмінено", reply_markup=None)


@dp.callback_query_handler(text="confirm_mail", state=MailingStates.idle, is_admin=True)
async def _make_mail(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await MailingStates.amount.set()
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Відправити всім", callback_data="send_all")
    )
    await call.message.answer(
        "Вкажіть кому відправити або натисність відправити всім",
        reply_markup=kb,
    )


async def delete_msg(chat_id, msg_id):
    try:
        await bot.delete_message(chat_id, msg_id)
    except:
        pass


from aiogram.utils.callback_data import CallbackData

fast_cb = CallbackData("fast_mail", "is_fast")


async def choose_fast_or_not(msg: Message):
    # await msg.answer("Введите этап начального сообщения (рассылка будет отправлена только людям на этом этапе). Чтобы отправить всем напишите 0")

    # @dp.message_handler(state=MailingStates.step)
    # async def _process_change_kb_end(message: Message, state: FSMContext):
    # st = message.text

    # if not st.isdigit():
    #     await message.answer("Это не число!")
    #     return

    # st = int(st)
    # if st < 0:
    #     await message.answer("Введите число больше 0")
    #     return
    # await state.update_data(step=st)
    await MailingStates.fast.set()
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton("Підтвердити", callback_data=fast_cb.new("no")),
        InlineKeyboardButton("Відмінити", callback_data="cancel_all"),
        # InlineKeyboardButton("Быстрая (бета)", callback_data=fast_cb.new("yes")),
    )
    await msg.answer(
        "Підтвердіть що вам потрібно зробити розсилку",
        reply_markup=kb,
    )


@dp.callback_query_handler(text="cancel_all", state="*", is_admin=True)
async def _send_all_mail(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.finish()


@dp.callback_query_handler(text="send_all", state=MailingStates.amount, is_admin=True)
async def _send_all_mail(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await choose_fast_or_not(call.message)


@dp.message_handler(state=MailingStates.amount, is_admin=True)
async def _make_mail(message: Message, state: FSMContext):
    users = [int(i) for i in message.text.split()]

    await MailingStates.fast.set()
    await state.update_data(max_amount=None, spec_users=users)
    await choose_fast_or_not(message)


fast_count = {"count": 0, "good": 0, "bad": 0}


async def send_message(user_id: int, from_chat: int, msg_id: int, kb, time) -> bool:
    try:
        sent_msg = await bot.copy_message(user_id, from_chat, msg_id, reply_markup=kb)
    except aiogram.utils.exceptions.RetryAfter as e:
        await asyncio.sleep(e.timeout)
        return await send_message(user_id, from_chat, msg_id, kb, time)
    except Exception as e:
        fast_count["bad"] += 1
    else:
        if time is not None:
            date = datetime.now() + timedelta(
                seconds=time.second, minutes=time.minute, hours=time.hour
            )
            scheduler.add_job(
                delete_msg,
                trigger=DateTrigger(date),
                args=(user_id, sent_msg.message_id),
                id=f"delete_msg_{user_id}_{msg_id}",
            )
        fast_count["good"] += 1
    fast_count["count"] += 1


mail_thread_on = False


async def send_copy(
    msg: Message,
    bot: Bot,
    chat_id,
    message_thread_id=None,
    disable_notification=None,
    protect_content=None,
    disable_web_page_preview=True,
    reply_to_message_id=None,
    allow_sending_without_reply=None,
    reply_markup=None,
    dyn_vars=True,
    replace_download=None,
) -> Message:
    """
    Send copy of current message

    :param chat_id:
    :param message_thread_id:
    :param disable_notification:
    :param protect_content:
    :param disable_web_page_preview: for text messages only
    :param reply_to_message_id:
    :param allow_sending_without_reply:
    :param reply_markup:
    :return:
    """
    kwargs = {
        "chat_id": chat_id,
        "allow_sending_without_reply": allow_sending_without_reply,
        "reply_markup": reply_markup or msg.reply_markup,
        "parse_mode": "html",
        "disable_notification": disable_notification,
        "reply_to_message_id": reply_to_message_id,
    }
    text = msg.html_text if (msg.text or msg.caption) else None
    if dyn_vars and text:
        user = await bot.get_chat_member(chat_id, chat_id)
        user = user.user
        text = text.replace(r"{id}", str(user.id))
        text = text.replace(r"{username}", str(user.username or "unknown"))
        text = text.replace(r"{fname}", str(user.first_name or "unknown"))
        text = text.replace(r"{lname}", str(user.last_name or "unknown"))
        text = text.replace(r"{fullname}", str(user.full_name))
        text = text.replace(r"{anyname}", str(user.username or user.full_name))
    file = io.BytesIO()
    if replace_download:
        Bot.set_current(replace_download)
    else:
        Bot.set_current(bot)
    if msg.text:
        kwargs["disable_web_page_preview"] = disable_web_page_preview
        return await bot.send_message(text=text, **kwargs)
    elif msg.audio:
        await msg.audio.download(destination_file=file)
        return await bot.send_audio(
            audio=file,
            caption=text,
            title=msg.audio.title,
            performer=msg.audio.performer,
            duration=msg.audio.duration,
            **kwargs,
        )
    elif msg.animation:
        await msg.animation.download(destination_file=file)
        return await bot.send_animation(
            animation=InputFile(file), caption=text, **kwargs
        )
    elif msg.document:
        await msg.document.download(destination_file=file)
        return await bot.send_document(document=InputFile(file), caption=text, **kwargs)
    elif msg.photo:
        await msg.photo[-1].download(destination_file=file)
        return await bot.send_photo(photo=InputFile(file), caption=text, **kwargs)
    elif msg.sticker:
        kwargs.pop("parse_mode")
        await msg.sticker.download(destination_file=file)
        return await bot.send_sticker(sticker=file, **kwargs)
    elif msg.video:
        await msg.video.download(destination_file=file)
        return await bot.send_video(video=InputFile(file), caption=text, **kwargs)
    elif msg.video_note:
        kwargs.pop("parse_mode")
        await msg.video_note.download(destination_file=file)
        return await bot.send_video_note(video_note=file, **kwargs)
    elif msg.voice:
        await msg.voice.download(destination_file=file)
        return await bot.send_voice(voice=msg.voice.file_id, caption=text, **kwargs)
    elif msg.contact:
        kwargs.pop("parse_mode")
        return await bot.send_contact(
            phone_number=msg.contact.phone_number,
            first_name=msg.contact.first_name,
            last_name=msg.contact.last_name,
            vcard=msg.contact.vcard,
            **kwargs,
        )
    elif msg.venue:
        kwargs.pop("parse_mode")
        return await bot.send_venue(
            latitude=msg.venue.location.latitude,
            longitude=msg.venue.location.longitude,
            title=msg.venue.title,
            address=msg.venue.address,
            foursquare_id=msg.venue.foursquare_id,
            foursquare_type=msg.venue.foursquare_type,
            **kwargs,
        )
    elif msg.location:
        kwargs.pop("parse_mode")
        return await bot.send_location(
            latitude=msg.location.latitude,
            longitude=msg.location.longitude,
            **kwargs,
        )
    elif msg.poll:
        kwargs.pop("parse_mode")
        return await bot.send_poll(
            question=msg.poll.question,
            options=[option.text for option in msg.poll.options],
            is_anonymous=msg.poll.is_anonymous,
            allows_multiple_answers=msg.poll.allows_multiple_answers,
            **kwargs,
        )
    elif msg.dice:
        kwargs.pop("parse_mode")
        return await bot.send_dice(
            emoji=msg.dice.emoji,
            **kwargs,
        )
    else:
        raise TypeError("This type of message can't be copied.")


from django.conf import settings

main_bot = Bot(settings.BOT_TOKEN, parse_mode="HTML")


async def list_to_async_iterator(lst):
    for item in lst:
        # Simulate async processing (e.g., with await)
        await asyncio.sleep(0)  # Non-blocking
        yield item


async def make_mail(
    user_ids,
    fast,
    from_user,
    msg_id,
    kb,
    time,
    has_limit,
    max_amount,
    msg,
    call,
    all_amount,
    orig_msg,
    spec_users=[],
):
    global mail_thread_on
    count = 0
    good = 0
    bad = 0
    try:
        msg_obj = await send_copy(
            orig_msg,
            main_bot,
            msg.chat.id,
            dyn_vars=False,
            replace_download=bot,
        )
    except Exception as e:
        await bot.send_message(
            f"Помилка: {e}",
            msg.chat.id,
        )
        return

    #     setting.start_msg_id_main_bot = msg.message_id
    # setting.msg_blob = json.dumps(msg.__dict__["_values"], cls=SimpleObject)
    if not spec_users:
        user_ids = UserProfile.objects.aiterator()
    else:
        user_ids = list_to_async_iterator(spec_users)

    async for user_id in user_ids:
        if not spec_users:
            user_id = user_id.user_id
        if not mail_thread_on:
            break
        if count % 50 == 0:
            await bot.edit_message_text(
                f"Відправлено: {count}, успішно {good}",
                msg.chat.id,
                msg.message_id,
            )
        try:
            sent_msg = await send_copy(msg_obj, main_bot, user_id, reply_markup=kb)
            # sent_msg = await bot.copy_message(
            #     user_id, from_user, msg_id, reply_markup=kb
            # )
        except Exception as e:
            bad += 1
        else:
            good += 1
        count += 1
        await asyncio.sleep(0.05)

    await bot.edit_message_text(
        f"Всього: {count}\nВдачно: {good}\nНе прийшло: {bad}",
        msg.chat.id,
        msg.message_id,
    )

    # if fast:
    #     for users in chunks(user_ids, 25):
    #         if not mail_thread_on:
    #             break
    #         for user in users:
    #             asyncio.create_task(send_message(user.id, from_user, msg_id, kb, time))
    #         await asyncio.sleep(1)
    #         try:
    #             await msg.edit_text(
    #                 f"Відправлено: {fast_count['count']}, успішно: {fast_count['good']}, невдачно: {fast_count['bad']}"
    #             )
    #         except:
    #             pass
    #         if has_limit and fast_count["good"] >= max_amount:
    #             break
    #     await call.message.answer(
    #         f"Результати розсилки\nВідправлено: {fast_count['count']}, успішно: {fast_count['good']}, невдачно: {fast_count['bad']}"
    #     )
    # # ====
    # else:
    #     for user_id in user_ids:
    #         if not mail_thread_on:
    #             break
    #         if count % 50 == 0:
    #             await msg.edit_text(
    #                 f"Відправлено: {count}, успішно {good}, всього треба {all_amount}"
    #             )
    #         try:
    #             sent_msg = await bot.copy_message(
    #                 user_id, from_user, msg_id, reply_markup=kb
    #             )
    #             if time is not None:
    #                 date = datetime.now() + timedelta(
    #                     seconds=time.second, minutes=time.minute, hours=time.hour
    #                 )
    #                 scheduler.add_job(
    #                     delete_msg,
    #                     trigger=DateTrigger(date),
    #                     args=(user_id, sent_msg.message_id),
    #                     id=f"delete_msg_{user_id}_{msg_id}",
    #                 )
    #             good += 1
    #         except Exception:
    #             bad += 1
    #         count += 1
    #         if has_limit and good >= max_amount:
    #             break
    #         await asyncio.sleep(0.05)

    #     await msg.edit_text(f"Всього: {count}\nВдачно: {good}\nНе прийшло: {bad}")


@dp.message_handler(commands=["stop"], is_admin=True)
async def _stop_mail(message: Message):
    global mail_thread_on
    mail_thread_on = False


@dp.callback_query_handler(fast_cb.filter(), state=MailingStates.fast)
async def _process_mail(call: CallbackQuery, state: FSMContext, callback_data: dict):
    global mail_thread_on
    msg = await call.message.answer(f"Робимо розсилку..")
    data = await state.get_data()
    await state.finish()
    msg_id = data["msg_id"]
    orig_msg = data["orig_msg"]
    kb = data.get("kb")
    spec_users = data.get("spec_users", [])
    max_amount = data.get("max_amount")
    has_limit = max_amount is not None
    from_user = call.from_user.id
    time: datetime = data.get("time")
    fast = True if callback_data.get("is_fast") == "yes" else False

    user_ids = get_user_ids()
    all_amount = max_amount if has_limit else len(user_ids)
    fast_count["count"] = 0
    fast_count["good"] = 0
    fast_count["bad"] = 0

    mail_thread_on = True
    await make_mail(
        user_ids,
        fast,
        from_user,
        msg_id,
        kb,
        time,
        has_limit,
        max_amount,
        msg,
        call,
        all_amount,
        orig_msg=orig_msg,
        spec_users=spec_users,
    )
    await call.message.answer("Розсилка закінчена!")
    mail_thread_on = False

    # ====


async def notify_admins(text):
    for user_id in ADMINS:
        await bot.send_message(user_id, text)


@dp.message_handler(commands=["start"])
async def process_update(message: Message):
    send_to = message.from_user.id
    await message.answer("Start")
    # link = chat_member.invite_link.invite_link
    # if setting is None:
    #     await notify_admins(f"Неизвестная ссылка: {link}")
    #     return
    await send_start_msg(send_to, 1)


async def main():
    # await main2()
    scheduler.start()
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
