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
    api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
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


from asgiref.sync import async_to_sync


async def get_trans(addr):
    return await tonapi.blockchain.get_account_transactions(account_id=addr, limit=30)


from django.db.models import F
from django.db import transaction


def main():

    transactions = async_to_sync(get_trans)(
        "UQDqs70rjikjhisUZj46odx9UpMVJx74kQvvSYCSjUCuqEZ-"
    )

    logger.info("")
    logger.info("print kw")

    for tx in transactions.transactions:
        if not tx.in_msg:
            continue
        tx_id = tx.in_msg.hash
        if not tx_id:
            continue
        try:
            if AutoWithdrawalRequest.objects.filter(tx_id=tx_id, status="pending").update(
                status="ok"
            ) != 0:
                logger.info(f"tx {tx_id} ok")
        except Exception:
            logger.exception(f"trans error {tx_id}")

    # for tx in transactions.events:
    #     # try:
    #     tx_id = tx.event_id
    #     status = tx.actions[0].status
    #     AutoWithdrawalRequest.objects.filter(tx_id=tx_id).update(status=status)

    # status = tx.actions[0].status
    # AutoWithdrawalRequest.objects.filter(tx_id=tx_id).update(status=status)
    # except AutoWithdrawalRequest.DoesNotExist:
    #     continue

    time.sleep(3)
    logger.info("=======================================")

    transactions = async_to_sync(get_trans)(
        "UQD_u1QyRYNcMGxXWBPiTvfJaerlxQ9X9bxESnM8d1-b0tQA"
    )

    logger.info("")
    logger.info("print tbtc")

    for tx in transactions.transactions:
        if not tx.in_msg:
            continue
        tx_id = tx.in_msg.hash
        if not tx_id:
            continue
        try:
            if AutoWithdrawalRequest.objects.filter(tx_id=tx_id, status="pending").update(
                status="ok"
            ) != 0:
                logger.info(f"tx {tx_id} ok")
        except Exception:
            logger.exception(f"trans error {tx_id}")

    time.sleep(3)
    logger.info("=======================================")

    transactions = async_to_sync(get_trans)(
        "UQAWq4gFNXOKSk7ihJ98h31XmJFNokshEizAz2il4v4sGpAJ"
    )

    logger.info("")
    logger.info("print stak")

    for tx in transactions.transactions:
        if not tx.in_msg:
            continue
        tx_id = tx.in_msg.hash
        if not tx_id:
            continue
        try:
            if AutoWithdrawalRequest.objects.filter(tx_id=tx_id, status="pending").update(
                status="ok"
            ) != 0:
                logger.info(f"tx {tx_id} ok")
        except Exception:
            logger.exception(f"trans error {tx_id}")

    time.sleep(3)
    logger.info("=======================================")
    
    # repeat = AutoWithdrawalRequest.objects.filter(
    #     status="pending",
    #     claimed_at__lt=timezone.now() - timezone.timedelta(minutes=10),
    #     claimed_at__gt=timezone.now() - timezone.timedelta(days=1),
    # ).exclude(tx_id="").exclude(tx_id=None)
    # if repeat:
    #     logger.info(f"repeat {repeat.values_list("tx_id",flat=True)}")
    #     repeat.update(status="wait_auto")


if __name__ == "__main__":
    import asyncio

    while True:
        try:
            main()
        except Exception:
            logger.exception("err")
        finally:
            time.sleep(3)
