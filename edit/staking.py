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
    AsicsCoefs,
    BufferTransaction,
    UserProfile,
    UserStaking,
    WithdrawalConfig,
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
    logger = logging.getLogger("staking")
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


logger = setup_logging("logs/staking.log")

from asgiref.sync import async_to_sync


async def get_trans(addr):
    return await tonapi.blockchain.get_account_transactions(account_id=addr, limit=100)


from django.db.models import F
from django.db import transaction


def main():
    transactions = async_to_sync(get_trans)(
        "UQBeklJltNcujGHOMI_yJsAQKJLxR4QfzAqp9Wu1Rp1Y9TAj"
    )

    logger.info("")
    logger.info("print staking")
    config = WithdrawalConfig.objects.first()
    min_staking = config.min_staking if config is not None else 1000

    for tx in transactions.transactions:
        try:
            if tx.in_msg.decoded_body is None:
                continue
            sender = tx.in_msg.decoded_body.get("sender")
            amount = tx.in_msg.decoded_body.get("amount")
            if sender is None:
                continue

            final_amount = float(amount) / 10000
            if final_amount < min_staking:
                continue

            if UserStaking.objects.filter(tx_id=tx.hash).exists():
                continue
            staking = (
                UserStaking.objects.filter(confirmed=False, user__ton_wallet=sender)
                .exclude(tx_id=tx.hash)
                .order_by("-id")
                .first()
            )
            if staking is None:
                continue

            logger.info(f"{datetime.now()} | !! valid trans {sender} {amount}")
            logger.info(tx)


            final_apr = staking.apr + staking.user.sbt_get_staking(final_amount)
            logger.info(f"{datetime.now()} | !! test {staking.pk} {staking.apr} {staking.user.sbt_get_staking(final_amount)} {final_amount} {final_apr}")
            logger.info(f"{datetime.now()} | !! test {staking.user.has_gold_sbt} {staking.user.has_gold_sbt_nft} {staking.user.has_silver_sbt} {staking.user.has_silver_sbt_nft}")
            UserStaking.objects.filter(pk=staking.pk).update(
                confirmed=True,
                token_amount=final_amount,
                reward=final_amount * staking.days / 365 * final_apr / 100,
                apr=final_apr,
                last_collected=timezone.now(),
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=staking.days),
                wallet_address=sender,
                tx_id=tx.hash,
                status="active",
            )

            logger.info(f"{datetime.now()} | confirmed: {staking.pk}")

        except Exception:
            logger.exception("trans error")


if __name__ == "__main__":
    import asyncio

    # Run the asynchronous function
    # asyncio.run(main())
    while True:
        try:
            main()
            time.sleep(1)
        except Exception:
            logger.exception("err")
        time.sleep(10)
