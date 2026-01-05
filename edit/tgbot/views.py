from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from telebot import types, TeleBot


from tasks.models import Booster, UserTask
from tasks.views import get_prize

from django.conf import settings

bot = TeleBot(settings.BOT_TOKEN, parse_mode="HTML")


class WebhookEndpoint(APIView):
    def post(self, request, *args, **kwargs):
        if request.content_type == "application/json":
            json_string = request.body.decode("utf-8")
            update = types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return Response(status=status.HTTP_200_OK)
        return Response(status=status.HTTP_403_FORBIDDEN)


# @app.post("/submitOrder")
# def submit_order():
#     data = request.json
#     init_data = parse_init_data(token=config.BOT_TOKEN, raw_init_data=data["initData"])
#     if init_data is False:
#         return False


#     query_id = init_data["query_id"]

#     result_text = "<b>Order summary:</b>\n\n"
#     for item in data["items"]:
#         name, price, amount = item.values()
#         result_text += f"{name} x{amount} — <b>{price}</b>\n"
#     result_text += "\n" + data["totalPrice"]

#     result = types.InlineQueryResultArticle(
#         id=query_id,
#         title="Order",
#         input_message_content=types.InputTextMessageContent(
#             message_text=result_text, parse_mode="HTML"
#         ),
#     )
#     bot.answer_web_app_query(query_id, result)
#     return ""


def extract_unique_code(text):
    # Extracts the unique_code from the sent /start command.
    return text.split()[1] if len(text.split()) > 1 else None


from core.models import (
    EngineerConfig,
    GenPowerStationConfig,
    StoragePowerStationConfig,
    TimedUserNFT,
    UserProfile,
    WalletInfo,
)

from telebot.types import Message, PreCheckoutQuery


@bot.message_handler(commands=["start"])
def cmd_start(message: types.Message):
    if message.chat.type != "private":
        return
    user = UserProfile.objects.filter(user_id=message.from_user.id).first()
    if user is None:
        user = UserProfile.objects.create(
            user_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            ton_wallet="",  # Initialize with an empty string or appropriate default value
        )
        user.storage_limit = StoragePowerStationConfig.objects.get(
            station_type=user.station_type, level=user.storage_level
        ).storage_limit
        user.generation_rate = GenPowerStationConfig.objects.get(
            station_type=user.station_type, level=user.generation_level
        ).generation_rate
        user.kw_per_tap = EngineerConfig.objects.get(
            level=user.engineer_level
        ).tap_power
        code = extract_unique_code(message.text)
        if code and code.startswith("ref_id"):
            ref_id = int(code.replace("ref_id", ""))
            referrer = UserProfile.objects.filter(user_id=ref_id).first()
            if referrer is not None:
                user.referrer = referrer
                user.referrer_level_2 = referrer.referrer
        user.save()
    markup = types.InlineKeyboardMarkup(
        keyboard=[
            [
                types.InlineKeyboardButton(
                    text="⏩ Видеопрезентация TonBitcoin ⏪",
                    url="https://youtu.be/ZRgFmlEyJo8",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="📣 Telegram канал TonBitcoin 📣", url="https://t.me/ton4btc"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🎙[RU] чат TonBitcoin 🎙", url="https://t.me/ton7btc"
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="🥇 Купить tBTC на DEX бирже DeDust.io 🥇",
                    url="https://dedust.io/swap/TON/EQBDdyCZeFFRoOmvEPZw3q_xuwGAb4qXgE2_q4WdmiBTnZLu",
                )
            ],
            [
                types.InlineKeyboardButton(
                    text="💹 Курс и график монеты tBTC 💹",
                    url="https://www.geckoterminal.com/ton/pools/EQCDcj_aamOeU50EqM0VtERerZEIk0EiMcYkCV4F5TjkGghx",
                )
            ],
        ]
    )
    bot.send_photo(
        message.chat.id,
        types.InputFile("tgbot/photo.jpg"),
        """ℹ️ Подробнее о проекте ℹ️

TonBitcoin — это приложение майнер, где участники могут погрузиться в мир майнинга аналога оригинального Bitcoin на блокчейне TON, токена tBTC, используя функционал экосистемы TON прямо в Telegram Mini Apps.

Облачный Web 3.0 майнинг проекта TonBitcoin позволяет участвовать майнинге утилитарного токена tBTC. Участники смогут управлять собственными электростанциями и NFT-оборудованием, используя энергию, производимую станциями, для майнинга токенов tBTC. Таким образом, проект TonBitcoin предоставляет уникальную возможность принять участие в майнинге криптовалют без необходимости в значительных финансовых и энергетических затратах, открывая новые возможности для широкого круга пользователей.

Подробнее о проекте по ссылкам ниже:""",
        reply_markup=markup,
    )


from telebot.types import Message, PreCheckoutQuery


@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query: PreCheckoutQuery):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True, error_message="Error")


from shared import setup_logger

action_logger = setup_logger()

from django.db.models import F
from django.utils import timezone
from django.db import close_old_connections

@bot.message_handler(content_types=["successful_payment"])
def got_payment(message: Message):
    close_old_connections()
    
    payment_info = message.successful_payment
    payload = payment_info.invoice_payload

    user_id = message.from_user.id
    if payload.startswith("engineer:"):
        try:
            user_profile = UserProfile.objects.get(user_id=message.from_user.id)

            level = int(payment_info.invoice_payload.replace("engineer:", ""))
            config = EngineerConfig.objects.get(level=level)
            final_price = int(config.hire_cost_stars * user_profile.sbt_get_stars_discount())

            if final_price > payment_info.total_amount:
                action_logger.info(
                    f"user {user_id} | NOT upgraded eng {level} lvl | {payment_info.total_amount} != {final_price} | {payment_info.telegram_payment_charge_id}"
                )
                return
            UserProfile.objects.filter(user_id=user_id).update(
                engineer_level=level,
                kw_per_tap=config.tap_power,
            )
            action_logger.info(
                f"user {user_id} | upgraded eng {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | NOT upgraded eng {payment_info.invoice_payload} | {payment_info.telegram_payment_charge_id}"
            )

    elif payload == "wheel_stars":
        try:
            user_profile = UserProfile.objects.get(user_id=message.from_user.id)
            prize, _ = get_prize("Stars", user_profile)

            if not prize:
                action_logger.info(
                    f"user {user_id} | NOT!!!-WHEEL FOR {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id} | {prize.id}"
                )
                return

            action_logger.info(
                f"user {user_id} | WHEEL FOR {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id} | {prize.id}"
            )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | NOT!!!-WHEEL FOR {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )

    elif payload.startswith("booster:"):
        try:
            user_profile = UserProfile.objects.get(user_id=message.from_user.id)

            slug, days = payload.split(":")[1:]
            booster = Booster.objects.get(slug=slug)

            if booster.slug == "azot":
                UserProfile.objects.filter(id=user_profile.id).update(
                    azot_counts=F("azot_counts") + 1,
                    overheated_until=None,
                    tap_count_since_overheat=0,
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "jarvis":
                now = timezone.now()
                jarvis_expires = user_profile.jarvis_expires
                is_active = jarvis_expires and jarvis_expires > now

                if not is_active:
                    jarvis_expires = now

                jarvis_expires += timedelta(days=int(days))

                if jarvis_expires > now + timedelta(days=31):
                    jarvis_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    jarvis_expires=jarvis_expires
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.jarvis_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "cryo":
                now = timezone.now()
                cryo_expires = user_profile.cryo_expires
                is_active = cryo_expires and cryo_expires > now

                if not is_active:
                    cryo_expires = now

                cryo_expires += timedelta(days=int(days))

                if cryo_expires > now + timedelta(days=31):
                    cryo_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    cryo_expires=cryo_expires
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.cryo_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "autostart":
                UserProfile.objects.filter(id=user_profile.id).update(
                    autostart_count=F("autostart_count") + int(days)
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.autostart_count} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "magnit":
                now = timezone.now()
                magnit_expires = user_profile.magnit_expires
                is_active = magnit_expires and magnit_expires > now

                if not is_active:
                    magnit_expires = now

                magnit_expires += timedelta(days=int(days))

                if magnit_expires > now + timedelta(days=31):
                    magnit_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    magnit_expires=magnit_expires,
                    magnit_buy_hashrate=F("mining_farm_speed"),
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.magnit_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "asic_manager":
                now = timezone.now()
                manager_expires = user_profile.manager_expires
                is_active = manager_expires and manager_expires > now

                if not is_active:
                    manager_expires = now

                manager_expires += timedelta(days=int(days))

                if manager_expires > now + timedelta(days=31):
                    manager_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    manager_expires=manager_expires,
                    manager_buy_hashrate=F("mining_farm_speed"),
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.manager_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "electrics":
                now = timezone.now()
                electrics_expires = user_profile.electrics_expires
                is_active = electrics_expires and electrics_expires > now

                if not is_active:
                    electrics_expires = now

                electrics_expires += timedelta(days=int(days))

                if electrics_expires > now + timedelta(days=31):
                    electrics_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    electrics_expires=electrics_expires
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.electrics_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "premium_sub":
                now = timezone.now()
                premium_sub_expires = user_profile.premium_sub_expires
                is_active = premium_sub_expires and premium_sub_expires > now

                if not is_active:
                    premium_sub_expires = now

                premium_sub_expires += timedelta(days=int(days))

                if premium_sub_expires > now + timedelta(days=31):
                    premium_sub_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    premium_sub_expires=premium_sub_expires
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.premium_sub_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            elif booster.slug == "repair_kit":
                now = timezone.now()
                repair_kit_expires = user_profile.repair_kit_expires
                is_active = repair_kit_expires and repair_kit_expires > now

                if not is_active:
                    repair_kit_expires = now

                repair_kit_expires += timedelta(days=int(days))

                if repair_kit_expires > now + timedelta(days=31):
                    repair_kit_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    repair_kit_expires=repair_kit_expires,
                    repair_kit_power_level=user_profile.power,
                )
                action_logger.info(
                    f"user {user_id} | bought booster {payload} | was {user_profile.repair_kit_expires} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
            else:
                action_logger.info(
                    f"user {user_id} | UNKNOWN bought booster {payload} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | NOT bought booster {payload} | {payment_info.telegram_payment_charge_id}"
            )
    elif payload == "speed_build":
        try:
            user_profile = UserProfile.objects.get(user_id=message.from_user.id)
            price = user_profile.get_build_price()
            if (
                price is None
                or int(price * user_profile.sbt_get_stars_discount())
                > payment_info.total_amount
            ):
                action_logger.info(
                    f"user {user_id} | NOT bought speed_build | need {price} | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
                )
                return
            UserProfile.objects.filter(user_id=user_id).update(
                building_until=None,
            )
            action_logger.info(
                f"user {user_id} | bought speed_build | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | NOT bought speed_build | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
    elif payload == "speed_rent_unblock":
        try:
            user_profile = UserProfile.objects.get(user_id=message.from_user.id)

            UserProfile.objects.filter(user_id=user_id).update(
                rent_blocked_until=None,
            )
            action_logger.info(
                f"user {user_id} | bought speed_rent_unblock | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | NOT bought speed_rent_unblock | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
    elif payload.startswith("speed_wallet_unblock:"):
        try:
            user_profile = UserProfile.objects.get(user_id=message.from_user.id)
            wallet_info_id = int(payment_info.invoice_payload.replace("speed_wallet_unblock:", ""))

            WalletInfo.objects.filter(id=wallet_info_id).update(
                block_until=None,
            )
            action_logger.info(
                f"user {user_id} | bought speed_wallet_unblock | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | NOT bought speed_wallet_unblock | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
    elif payload.startswith("speed_timed_nft_unblock:"):
        try:
            user_profile = UserProfile.objects.get(user_id=message.from_user.id)
            timed_id = int(payment_info.invoice_payload.replace("speed_timed_nft_unblock:", ""))

            TimedUserNFT.objects.filter(id=timed_id).update(
                block_until=None,
            )
            action_logger.info(
                f"user {user_id} | bought speed_timed_nft_unblock | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
        except Exception as e:
            action_logger.exception(
                f"user {user_id} | NOT bought speed_timed_nft_unblock | {payment_info.total_amount} stars | {payment_info.telegram_payment_charge_id}"
            )
    else:
        action_logger.info(f"user {message.from_user.id} | UNKNOWN payload {payload}")


@bot.message_handler(
    # func=lambda message: message.chat.type in ["group", "supergroup", "channel"]
)
def handle_group_messages(message: types.Message):
    UserTask.objects.filter(
        profile__user_id=message.from_user.id,
        task__condition="chat_message",
        task__n2=str(message.chat.id),
    ).update(completed=True)


# def main():
#     import django

#     django.ready()
#     bot.delete_webhook()
#     bot.set_webhook(settings.WEBHOOK_URL)


# if __name__ == "__main__":
#     main()
