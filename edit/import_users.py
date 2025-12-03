import csv
import os
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import UserProfile

i1 = 0
i2 = 0
with open("users.csv", newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        created = False
        user_profile = UserProfile.objects.filter(
            user_id=row["User TG ID"],
        ).first()
        if user_profile is None:
            created = True
            d ={
                    "user_id": row["User TG ID"],
                    "energy": float(row["Energy"].replace(",", ".")),
                    "kw_wallet": float(row["Kw wallet"].replace(",", ".")),
                    "tbtc_wallet": float(row["Tbtc wallet"].replace(",", ".")),
                    "station_type": row["Station type"],
                    "storage_level": int(row["Storage level"]),
                    "generation_level": int(row["Generation level"]),
                    "engineer_level": int(row["Engineer level"]),
                    "kw_per_tap": float(row["Kw per tap"].replace(",", ".")),
                    "storage": float(row["Storage"].replace(",", ".")),
                    "storage_limit": float(row["Storage limit"].replace(",", ".")),
                    "generation_rate": float(row["Generation rate"].replace(",", ".")),
                    "power": float(row["Power"].replace(",", ".")),
                    # "referrer_id": int(row["Referrer"]) if row["Referrer"] else None,
                    # "referrer_level_2_id": (
                    #     int(row["Referrer level 2"]) if row["Referrer level 2"] else None
                    # ),
                    "bonus_kw_level_1": float(row["Bonus kw level 1"].replace(",", ".")),
                    "bonus_kw_level_2": float(row["Bonus kw level 2"].replace(",", ".")),
                    "bonus_tbtc_level_1": float(row["Bonus tbtc level 1"].replace(",", ".")),
                    "bonus_tbtc_level_2": float(row["Bonus tbtc level 2"].replace(",", ".")),
                    "mined_tokens_balance": float(row["Mined tokens balance"].replace(",", "."))
                }
            user_profile = UserProfile.objects.create(id=row["Main ID"], **d)
            

        if created:
            i1 += 1
            print(f"User {user_profile.id} created")
        else:
            i2 += 1
            print(f"User {user_profile.id} already exists")
# with open("users.csv", newline="", encoding="utf-8") as csvfile:
#     reader = csv.DictReader(csvfile)
#     for row in reader:
#         if row["Referrer"]:
#             try:
#                 user_profile = UserProfile.objects.get(id=row["Id"])
#                 referrer_profile = UserProfile.objects.get(id=row["Referrer"])
#                 user_profile.referrer_id = referrer_profile.id
#                 user_profile.save()
#             except UserProfile.DoesNotExist:
#                 print("err", user_profile.id, row["Referrer"])
#         if row["Referrer level 2"]:
#             try:
#                 user_profile = UserProfile.objects.get(id=row["Id"])
#                 referrer_profile = UserProfile.objects.get(
#                     user_id=row["Referrer level 2"]
#                 )
#                 user_profile.referrer_level_2_id = referrer_profile.id
#                 user_profile.save()
#             except UserProfile.DoesNotExist:
#                 print("err", user_profile.id, row["Referrer level 2"])

print(i1, i2)
