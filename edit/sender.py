import logging
import os
import time

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import (
    AutoWithdrawalRequest,
)

import pytoniq_core


from pytoniq_core import Address, begin_cell

from tonutils.client import TonapiClient
from tonutils.jetton import JettonMaster, JettonWallet
from tonutils.wallet import WalletV5R1
from tonutils.wallet.data import TransferJettonData

from django.conf import settings


async def send_staking(info) -> None:
    JETTON_MASTER_ADDRESS = "EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc"
    JETTON_DECIMALS = 4

    client = TonapiClient(
        api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
    )
    wallet, _, _, _ = WalletV5R1.from_mnemonic(
        client, settings.STAKING_MNEMONICS_SECRET.split()
    )

    data_list = []
    for dest, amount, comment in info:
        data_list.append(
            TransferJettonData(
                destination=dest,
                jetton_master_address=JETTON_MASTER_ADDRESS,
                jetton_amount=amount,
                jetton_decimals=JETTON_DECIMALS,
                forward_payload=comment,
            )
        )

    tx_hash = await wallet.batch_jetton_transfer(data_list)

    return tx_hash


async def send_tbtc(info) -> None:
    JETTON_MASTER_ADDRESS = "EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc"
    JETTON_DECIMALS = 4

    client = TonapiClient(
        api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
    )
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, settings.TBTC_MNEMONICS_SECRET.split())

    data_list = []
    for dest, amount, comment in info:
        data_list.append(
            TransferJettonData(
                destination=dest,
                jetton_master_address=JETTON_MASTER_ADDRESS,
                jetton_amount=amount,
                jetton_decimals=JETTON_DECIMALS,
                forward_payload=comment,
            )
        )

    tx_hash = await wallet.batch_jetton_transfer(data_list)

    return tx_hash


async def send_kw(info) -> None:
    JETTON_MASTER_ADDRESS = "EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb"
    JETTON_DECIMALS = 9

    client = TonapiClient(
        api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
    )
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, settings.KW_MNEMONICS_SECRET.split())

    data_list = []
    for dest, amount, comment in info:
        data_list.append(
            TransferJettonData(
                destination=dest,
                jetton_master_address=JETTON_MASTER_ADDRESS,
                jetton_amount=amount,
                jetton_decimals=JETTON_DECIMALS,
                forward_payload=comment,
            )
        )

    tx_hash = await wallet.batch_jetton_transfer(data_list)

    return tx_hash


from asgiref.sync import async_to_sync


def main():
    tx_hash = ""
    info = []
    ids = []
    try:
        qs = AutoWithdrawalRequest.objects.filter(status="wait_auto", token_type="kw")
        if qs.count() > 0:
            qs = qs[:2]

            for req in qs:
                info.append([req.wallet_address, req.token_amount, req.comment])
                ids.append(req.pk)

            AutoWithdrawalRequest.objects.filter(pk__in=ids).update(status="pending")

            # try:
            tx_hash = async_to_sync(send_kw)(info)
            # except Exception as e:
            #     action_logger.exception(f"err send kw try again {info}")
            #     time.sleep(15)
            #     tx_hash = async_to_sync(send_kw)(info)

            AutoWithdrawalRequest.objects.filter(pk__in=ids).update(tx_id=tx_hash)
            action_logger.info(f"AUTOCLAIM {info}, {tx_hash}")
    except Exception:
        action_logger.exception(f"err send kw {info}")

    time.sleep(5)

    tx_hash = ""
    info = []
    ids = []
    try:
        qs = AutoWithdrawalRequest.objects.filter(status="wait_auto", token_type="tbtc")
        if qs.count() > 0:
            qs = qs[:2]

            for req in qs:
                info.append([req.wallet_address, req.token_amount, req.comment])
                ids.append(req.pk)

            AutoWithdrawalRequest.objects.filter(pk__in=ids).update(status="pending")

            # try:
            tx_hash = async_to_sync(send_tbtc)(info)
            # except Exception as e:
            #     action_logger.exception(f"err send tbtc try again {info}")
            #     time.sleep(15)
            #     tx_hash = async_to_sync(send_tbtc)(info)

            AutoWithdrawalRequest.objects.filter(pk__in=ids).update(tx_id=tx_hash)
            action_logger.info(f"AUTOCLAIM {info}, {tx_hash}")
    except Exception:
        action_logger.exception(f"err send kw {info}")

    time.sleep(5)

    tx_hash = ""
    info = []
    ids = []
    try:
        qs = AutoWithdrawalRequest.objects.filter(
            status="wait_auto", token_type="staking"
        )
        if qs.count() > 0:
            qs = qs[:2]

            info = []
            ids = []
            for req in qs:
                info.append([req.wallet_address, req.token_amount, req.comment])
                ids.append(req.pk)

            AutoWithdrawalRequest.objects.filter(pk__in=ids).update(status="pending")

            # try:
            tx_hash = async_to_sync(send_staking)(info)
            # except Exception as e:
            #     action_logger.exception(f"err send staking try again {info}")
            #     time.sleep(15)
            #     tx_hash = async_to_sync(send_staking)(info)

            AutoWithdrawalRequest.objects.filter(pk__in=ids).update(tx_id=tx_hash)
            action_logger.info(f"AUTOCLAIM {info}, {tx_hash}")
    except Exception:
        action_logger.exception(f"err send staking {info}")


from shared import setup_logger

action_logger = setup_logger()

if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception:
            action_logger.exception("err sender")
        finally:
            time.sleep(120)
