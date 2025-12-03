# import os
# import time
# import traceback
# from pytonapi import AsyncTonapi
# import django


# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
# django.setup()
# from core.models import AsicsCoefs, BufferTransaction, UserProfile
# from django.utils import timezone

# import logging
# from django.db.models import F

# for user in UserProfile.objects.all():
#     if (
#         user.referrer_level_2
#         and user.referrer_level_2.user_id != user.referrer.referrer.user_id
#     ):
#         print(1, user)
#     if (
#         user.referrer
#         and user.referrer.referrer
#         and user.referrer_level_2.user_id != user.referrer.referrer.user_id
#     ):
#         print(2, user)


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
from core.models import (
    AutoWithdrawalRequest,
)

tonapi = AsyncTonapi(
    api_key="AFC7OVBKMNFMWMQAAAAMQ6FQASZILJAFPGKO5WEMZHUKBP42UCGI5DJ265YWUPH4H7WFNNQ"
)

# read data from asics.csv


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,  # Set the minimum logging level for the root logger
        format="%(asctime)s - %(filename)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Log to the specified file
            logging.StreamHandler(),  # Log to the console
        ],
    )

    # Create a custom logger
    logger = logging.getLogger("checker")
    logger.setLevel(logging.DEBUG)  # Set the minimum logging level

    logger.propagate = False

    # Create handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    # Set logging levels for handlers
    file_handler.setLevel(logging.DEBUG)
    console_handler.setLevel(logging.INFO)

    # Create formatters and add them to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging("logs/checker.log")

csv_data = """Rarity,Name,Hash Rate,Measurement,Consumption (kW),Mining speed (tBTC),Price (TON)
Common,Asic S1,100,Hour,1,"0,02",2
Common,Asic S3,200,Hour,2,"0,04",4
Rare,Asic S5+,400,Hour,4,"0,08",8
Rare,Asic S7+,1000,Hour,10,"0,21",16
Rare,Asic S9+,2500,Hour,20,"0,52",32
Epic,Asic S11 XP,6000,Hour,44,"1,25",64
Epic,Asic S15 XP,15000,Hour,92,"3,13",128
Epic,Asic S17 XP,40000,Hour,192,"8,33",256
Legendary,Asic S19 XP+,100000,Hour,400,"20,83",512
Legendary,Asic S21 XP+,250000,Hour,800,"52,08",1024
Mythic,Asic SX Ultra Pro,600000,Hour,1664,"125,00",2048
"""

asics_data = parse_csv_to_dicts(csv_data)

from asgiref.sync import async_to_sync


async def get_trans(addr):
    return await tonapi.accounts.get_events(account_id=addr, limit=50)


from django.db.models import F
from django.db import transaction


def main():

    # transactions = async_to_sync(get_trans)(
    #     "UQBG5L_8ygKAxX2Avyg6n7uvP93bcb-yk0Ia3YuuH9XbZkcX"
    # )
    transactions = async_to_sync(get_trans)(
        "UQDO5XaE7tAz2WfT2fN3abpR04EEjmCOcUTvMxRZXBxh6jy6"
    )

    logger.info("")
    logger.info("print kw")

    for tx in transactions.events:
        try:
            tx_id = tx.event_id
            buffer_tx = AutoWithdrawalRequest.objects.get(tx_id=tx_id)
            status = tx.actions[0].status
            AutoWithdrawalRequest.objects.filter(tx_id=tx_id).update(status=status)
        except AutoWithdrawalRequest.DoesNotExist:
            continue

    time.sleep(3)
    print("=======================================")

    # transactions = async_to_sync(get_trans)(
    #     "UQBG5L_8ygKAxX2Avyg6n7uvP93bcb-yk0Ia3YuuH9XbZkcX"
    # )
    transactions = async_to_sync(get_trans)(
        "UQDO5XaE7tAz2WfT2fN3abpR04EEjmCOcUTvMxRZXBxh6jy6"
    )

    logger.info("")
    logger.info("print tbtc")

    for tx in transactions.events:
        try:
            tx_id = tx.event_id
            buffer_tx = AutoWithdrawalRequest.objects.get(tx_id=tx_id)
            status = tx.actions[0].status
            AutoWithdrawalRequest.objects.filter(tx_id=tx_id).update(status=status)
        except AutoWithdrawalRequest.DoesNotExist:
            continue

    time.sleep(3)
    print("=======================================")

    # transactions = async_to_sync(get_trans)(
    #     "UQB0ukWTZXHQhlhztL91277hD8xbFFKXiHVvSBNw-gcBKHfO"
    # )

    # logger.info("")
    # logger.info("print tbtc")
    # for tx in transactions.transactions:
    #     try:
    #         buffer_tx = BufferTransaction.objects.get(tx_hash=tx.hash)
    #     except BufferTransaction.DoesNotExist:
    #         if tx.in_msg.decoded_body is None:
    #             continue
    #         sender = tx.in_msg.decoded_body.get("sender")
    #         amount = tx.in_msg.decoded_body.get("amount")
    #         if sender is None:
    #             continue
    #         logger.info(f"{datetime.now()} | !! valid trans {sender} {amount}")
    #         logger.info(tx)
    #         with transaction.atomic():
    #             user = (
    #                 UserProfile.objects.select_for_update()
    #                 .filter(ton_wallet=sender)
    #                 .first()
    #             )

    #             if user is None:
    #                 continue
    #             logger.info(
    #                 f"{datetime.now()} | !!! found trans {user.user_id} +{float(amount)/10000} tbtc"
    #             )
    #             BufferTransaction.objects.create(
    #                 tx_hash=tx.hash, address=sender, success=True
    #             )
    #             logger.info(
    #                 f"{datetime.now()} | USER {user.user_id} BALANCE BEFORE: {user.tbtc_wallet}"
    #             )
    #             UserProfile.objects.select_for_update().filter(
    #                 ton_wallet=sender
    #             ).update(tbtc_wallet=F("tbtc_wallet") + (float(amount) / 10000))
    #         user = UserProfile.objects.filter(ton_wallet=sender).first()
    #         logger.info(
    #             f"{datetime.now()} | USER {user.user_id} BALANCE AFTER: {user.tbtc_wallet}"
    #         )

    #     except Exception:
    #         logger.exception("trans error")


if __name__ == "__main__":
    import asyncio

    while True:
        try:
            main()
        except Exception:
            logger.exception("err")
        finally:
            time.sleep(1)
