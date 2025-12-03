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
from django.db.models import F


def import_referral_bonuses(csv_file_path):
    with open(csv_file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            tg_id = int(row["TG ID"])
            bonus_tbtc = float(row["Бонус tBTC"].replace(",", "."))
            try:
                user_profile = UserProfile.objects.get(user_id=tg_id)
                UserProfile.objects.filter(user_id=tg_id).update(
                    bonus_tbtc_level_1=F("bonus_tbtc_level_1") + bonus_tbtc
                )
                logging.info(f"Updated bonus for user {tg_id}: {bonus_tbtc} tbtc")
            except UserProfile.DoesNotExist:
                logging.warning(f"User with TG ID {tg_id} not found")


if __name__ == "__main__":
    csv_file_path = "REF - Bonus tBTC.csv"
    import_referral_bonuses(csv_file_path)
