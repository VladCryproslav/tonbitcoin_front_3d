import os
import time
import traceback
from pytonapi import AsyncTonapi
import django
import pytoniq_core


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import AsicsCoefs, AutoWithdrawalRequest, BufferTransaction, UserProfile, NFTRentalAgreement
from django.utils import timezone

import logging
from django.db.models import F
from core.models import UserProfile, UserStaking

def user_friendly_wallet(address):
    if not address:
        return ""
    return pytoniq_core.Address(address).to_str(
            is_user_friendly=True, is_bounceable=False
        )

def get_total_staking(user):
    return sum(
        UserStaking.objects.filter(user=user, status="active").values_list("token_amount", flat=True)
    )

import csv

def main():
    filename = f"users_export_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
    with open(filename, "w", newline='', encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Імʼя",
            "Username",
            "Підключений гаманець",
            "Nft string",
            "Загальна швидкість ферми (hashrate)",
            "Сумарний стейкінг (токени)",
            "Заблокований"
        ])
        for user in UserProfile.objects.all():
            writer.writerow([
                user.first_name or "",
                user.username or "",
                user_friendly_wallet(user.ton_wallet),
                user.nft_string or "",
                user.mining_farm_speed or 0,
                get_total_staking(user),
                "+" if user.blocked else "-"
            ])
    print(f"Exported to {filename}")

if __name__ == "__main__":
    main()