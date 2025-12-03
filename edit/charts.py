import csv
from datetime import datetime
from django.utils import timezone
import os
import time
import traceback
import django
import logging
from pytonapi import Tonapi

import requests

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import (
    AsicsCoefs,
    BoosterRefund,
    BufferTransaction,
    GlobalStats,
    NFTDatabase,
    Notification,
    StationLevelStat,
    StationNFTOwner,
    UserProfile,
    NFTRentalAgreement,
)

tonapi = Tonapi(
    api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
)

from django.db.models import F, Sum
from django.utils import timezone
from core.models import UserProfile, ChartData
from datetime import date
from django.db.models import Q


def get_gecko(path):
    url = f"https://api.geckoterminal.com/api/{path}"

    try:
        headers = {
            'Accept': 'application/json',
        }
        response = requests.get(url, headers=headers)
        return response.json()

    except Exception as e:
        pass

def get_tbtc_remaining():
    # Адрес главного трежери-гаманця tBTC
    resp = tonapi.accounts.get_jetton_balance("0:15e23c5949c7ecff3b8b8dec9f641e4a9dd974d75738912181103bfd0787f27a", "0:4ea81880ad1e391949627f1773678d196a1755863b54ec68d8fa556daabb87bd")
    return int(resp.balance) / 10**4

def get_tbtc_staking():
    # Адрес главного трежери-гаманця tBTC
    resp = tonapi.accounts.get_jetton_balance("0:5e925265b4d72e8c61ce308ff226c0102892f147841fcc0aa9f56bb5469d58f5", "0:4ea81880ad1e391949627f1773678d196a1755863b54ec68d8fa556daabb87bd")
    return int(resp.balance) / 10**4

from django.db import transaction

def get_trans(addr):
    return tonapi.blockchain.get_account_transactions(account_id=addr, limit=100)

def add_chart_burnt(value: float):
    today = timezone.now().date()
    with transaction.atomic():
        if ChartData.objects.filter(date=today, chart_type="energy_burned").first():
            ChartData.objects.filter(date=today, chart_type="energy_burned").update(value=F("value") + value)
        else:
            ChartData.objects.create(date=today, chart_type="energy_burned", value=value)
            

def main():
    today = timezone.now().date()
    now = timezone.now()

    ChartData.objects.update_or_create(
        chart_type="station_power",
        date=today,
        defaults={"value": UserProfile.objects
        .filter(
            Q(storage__lt=F("storage_limit"))  # Станція ще не заповнена
            | (
                Q(jarvis_expires__gt=now)
                & Q(jarvis_expires__isnull=False)
                & (Q(building_until__lt=now) | Q(building_until__isnull=True))
            )
        )
        .aggregate(total=Sum(F("generation_rate")*F("power")/100))["total"] or 0},
    )
    
    mining_user_ids = UserProfile.objects.filter(is_mining=True).values_list("id", flat=True)
    total_hashrate = NFTRentalAgreement.objects.filter(
        renter_id__in=mining_user_ids
    ).aggregate(total=Sum("hashrate"))["total"] or 0
    total_hashrate_minus = NFTRentalAgreement.objects.filter(
        owner_id__in=mining_user_ids
    ).aggregate(total=Sum("hashrate"))["total"] or 0
    ChartData.objects.update_or_create(
        chart_type="network_hashrate",
        date=today,
        defaults={
            "value": total_hashrate/1000-total_hashrate_minus/1000 +(UserProfile.objects
            .filter(
                is_mining=True
            )
            .aggregate(total=Sum("mining_farm_speed"))["total"] or 0)
        },
    )
    
    ChartData.objects.update_or_create(
        chart_type="active_stations",
        date=today,
        defaults={"value": UserProfile.objects.filter(
            Q(storage__lt=F("storage_limit"))  # Станція ще не заповнена
            | (
                Q(jarvis_expires__gt=now)
                & Q(jarvis_expires__isnull=False)
                & (Q(building_until__lt=now) | Q(building_until__isnull=True))
            )
        ).count()},
        )
    
    ChartData.objects.update_or_create(
        chart_type="active_asics",
        date=today,
        defaults={
            "value": UserProfile.objects
        .filter(
            ton_wallet__isnull=False,
            ton_wallet__gt="",
            is_mining=True
        )
        .aggregate(total=Sum("nft_count"))["total"] or 0
        },
    )
    
    gecko_data = get_gecko("v2/networks/ton/pools/EQAHxCJBgyH8aXBizy3zLnHfZPYBQ4DAlkVXYZ3yrKNHcrX2/")
    ChartData.objects.update_or_create(
        chart_type="kw_price",
        date=today,
        defaults={
            "value": float(gecko_data["data"]["attributes"]["base_token_price_usd"])*1000,
        },
    )
    
    gecko_data = get_gecko("v2/networks/ton/pools/EQDRJ6wZJeaYYcR3FrqaShDgV2SyDtKBwoGI_wChiTrXL9mr/")
    ChartData.objects.update_or_create(
        chart_type="tbtc_price",
        date=today,
        defaults={
            "value": float(gecko_data["data"]["attributes"]["base_token_price_usd"]),
        },
    )

    ChartData.objects.update_or_create(
        chart_type="tbtc_remaining",
        date=today,
        defaults={"value": get_tbtc_remaining()},
    )

    ChartData.objects.update_or_create(
        chart_type="tbtc_staked",
        date=today,
        defaults={"value": get_tbtc_staking()},
    )
    
    transactions = get_trans(
        "UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJKZ"
    )

    for tx in transactions.transactions:
        try:
            buffer_tx = BufferTransaction.objects.get(tx_hash=tx.hash)
        except BufferTransaction.DoesNotExist:
            if tx.in_msg.decoded_body is None:
                continue
            sender = tx.in_msg.decoded_body.get("sender")
            amount = tx.in_msg.decoded_body.get("amount")
            if sender is None:
                continue
            if (
                tx.in_msg.source.address.root
                != "0:209a346dc1b4b4115593b0dfa9a33d0c2435115499033a99b788fa5924426e1c"
            ):
                continue
            
            add_chart_burnt(float(amount) / 1000000000)
            # logger.info(f"{datetime.now()} | !! valid trans {sender} {amount}")
            # logger.info(tx)
            # with transaction.atomic():
            #     user = (
            #         UserProfile.objects.select_for_update()
            #         .filter(ton_wallet=sender)
            #         .first()
            #     )
            #     if user is None:
            #         continue
            #     logger.info(
            #         f"{datetime.now()} | !!! found trans {user.user_id} +{(float(amount) / 1000000000)} kw"
            #     )
            #     BufferTransaction.objects.create(
            #         tx_hash=tx.hash, address=sender, success=True
            #     )
            #     logger.info(
            #         f"{datetime.now()} | USER {user.user_id} BALANCE BEFORE: {user.kw_wallet}"
            #     )
            #     UserProfile.objects.select_for_update().filter(
            #         ton_wallet=sender
            #     ).update(kw_wallet=F("kw_wallet") + (float(amount) / 1000000000))
            # user = UserProfile.objects.filter(ton_wallet=sender).first()
            # logger.info(
            #     f"{datetime.now()} | USER {user.user_id} BALANCE AFTER: {user.kw_wallet}"
            # )
        except Exception:
            traceback.print_exc()
            # logger.exception("trans error")

    # ADMIN CHARTS
    GlobalStats.objects.update_or_create(
        defaults={
            "total_energy": UserProfile.objects.aggregate(total=Sum("energy"))["total"] or 0,
            "total_kw": UserProfile.objects.aggregate(total=Sum("kw_wallet"))["total"] or 0,
            "total_tbtc": UserProfile.objects.aggregate(total=Sum("tbtc_wallet"))["total"] or 0,
            "total_unclaimed_tbtc": UserProfile.objects.aggregate(total=Sum("mined_tokens_balance"))["total"] or 0,
            "total_ref_kw": UserProfile.objects.aggregate(total=Sum("bonus_kw_level_1") + Sum("bonus_kw_level_2"))["total"] or 0,
            "total_ref_tbtc_mining": UserProfile.objects.aggregate(total=Sum("bonus_tbtc_level_1") + Sum("bonus_tbtc_level_2"))["total"] or 0,
            "total_ref_tbtc_staking": UserProfile.objects.aggregate(total=Sum("bonus_invest_level_1") + Sum("bonus_invest_level_2"))["total"] or 0,
            "total_mining_speed": UserProfile.objects.aggregate(total=Sum("mining_farm_speed"))["total"] or 0,
            "actual_mining_speed": UserProfile.objects.filter(is_mining=True).aggregate(total=Sum("mining_farm_speed"))["total"] or 0,
            "connected_asics": (UserProfile.objects.aggregate(total=Sum("nft_count"))["total"] or 0),
            "mining_asics": (UserProfile.objects.filter(is_mining=True).aggregate(total=Sum("nft_count"))["total"] or 0),
            "setup_asics": (UserProfile.objects.filter(is_mining=False).aggregate(total=Sum("nft_count"))["total"] or 0),
        }
    )
    
    STATION_LEVELS = [
        "Boiler house",
        "Coal power plant",
        "Thermal power plant",
        "Geothermal power plant",
        "Nuclear power plant",
        "Thermonuclear power plant",
        "Dyson Sphere",
        "Neutron star",
        "Antimatter",
        "Galactic core",
    ]
    
    counts = {}
    for station_level in range(1, 11):
        for generation_level in range(1, 4):
            key = f"count_{station_level}_{generation_level}"
            counts[key] = UserProfile.objects.filter(
                station_type=STATION_LEVELS[station_level - 1],
                generation_level=generation_level
            ).count()

    StationLevelStat.objects.update_or_create(
        defaults=counts
    )
    
    print("UPD CHARTS", timezone.now())



if __name__ == "__main__":
    import asyncio

    while True:
        try:
            main()
            # time.sleep(1)
        except Exception:
            traceback.print_exc()

        time.sleep(5)
