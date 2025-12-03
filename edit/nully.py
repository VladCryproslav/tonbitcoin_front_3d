import csv
import logging
import os
import time
import traceback
from datetime import datetime

import django
from django.utils import timezone
from pytonapi import AsyncTonapi

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from django.db.models import F

from core.models import AutoWithdrawalRequest, UserProfile, UserStaking

# UserProfile.objects.all().update(
#     past_engineer_level=F("engineer_level"),
# )


UserProfile.objects.all().update(
    engineer_level=1,
    # station_type="Boiler house",
    # storage_level=1,
    # generation_level=1,
    # storage=10,
    # storage_limit=10,
    # generation_rate=5,
    # power=100,
    # kw_per_tap=0.025,
    # #
    # is_mining=False,
    # battery_balance=0,
    # mining_period=0,
    # mined_tokens_balance=0,
    # last_tbtc_added=timezone.now(),
    # #
    # bonus_kw_level_1=0,
    # bonus_kw_level_2=0,
    # last_kw_bonus_claimed_at=timezone.now(),
    # bonus_tbtc_level_1=0,
    # bonus_tbtc_level_2=0,
    # last_tbtc_bonus_claimed_at=timezone.now(),
    # bonus_invest_level_1=0,
    # bonus_invest_level_2=0,
    # last_staking_bonus_claimed_at=timezone.now(),
    # #
    # energy=0,
    # kw_wallet=0,
    # tbtc_wallet=0,
)

# UserStaking.objects.all().delete()
