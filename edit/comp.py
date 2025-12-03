import csv
import json
import os
import time
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import UserProfile, EngineerConfig

a = {
    50: 15858,
    51: 34572,
    52: 56654,
    53: 82710,
    54: 113456,
    55: 149738,
    56: 192550,
    57: 243068,
    58: 302680,
    59: 373022,
    60: 456026,
    61: 553970,
    62: 669544,
    63: 805920,
    64: 966844,
}

from django.db.models import F

for user in UserProfile.objects.filter(engineer_level__gte=50):
    UserProfile.objects.filter(user_id=user.user_id).update(
        engineer_level=49,
        kw_per_tap=EngineerConfig.objects.get(level=49).tap_power,
        energy=F("energy") + a[user.engineer_level],
    )
    print(f"{user.user_id} | {user.engineer_level} | {a[user.engineer_level]}")
