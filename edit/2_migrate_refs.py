import csv
import json
import os
import time
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import UserProfile

i1 = 0
i2 = 0

for user in UserProfile.objects.all():
    if (
        user.referrer
        and user.referrer.referrer
        and user.user_id == user.referrer.referrer.user_id
    ):
        print(1, user.user_id, user.referrer.user_id, user.referrer.referrer.user_id)
        UserProfile.objects.filter(user_id=user.user_id).update(
            referrer=None, referrer_level_2=None
        )
        UserProfile.objects.filter(user_id=user.referrer.user_id).update(
            referrer=None, referrer_level_2=None
        )
    if user.referrer_level_2 and user.user_id == user.referrer_level_2.user_id:
        print(2, user.user_id, user.referrer_level_2.user_id)
    if user.referrer and user.user_id == user.referrer.user_id:
        print(3, user.user_id, user.referrer.user_id)

# with open("refs.json", newline="", encoding="utf-8") as f:
#     # with open("users.csv", newline="", encoding="utf-8") as csvfile:
#     refs = json.load(f)
#     #     {
#     # "user_id": "204",
#     # "invited_users": "[4249, 1201, 1200, 1199, 1198, 1196, 1194, 1193, 24217]",
#     # "referal_count": "9"
#     # },
#     m = dict()
#     for ref in refs:
#         user_id = int(ref["user_id"])
#         invited_users = json.loads(ref["invited_users"])
#         m[user_id] = invited_users
# for user_id, invited_users in m.items():
#     for i in invited_users:
#         if

# =======================================
# for ref in refs:
#     user_profile = UserProfile.objects.filter(
#         pk=ref["user_id"],
#     ).first()
#     if user_profile is None:
#         print("User not found", ref["user_id"])
#         continue
#     invited_users = json.loads(ref["invited_users"])

#     for invited_user in invited_users:
#         invited_user_profile = UserProfile.objects.filter(
#             pk=invited_user,
#         ).first()
#         if invited_user_profile is None:
#             print("Invited user not found", invited_user)
#             continue
#         if invited_user_profile.referrer is not None:
#             print("Already invited", invited_user)
#             continue
#         UserProfile.objects.filter(
#             pk=invited_user,
#         ).update(
#             referrer=user_profile,
#             referrer_level_2=user_profile.referrer,
#         )
#         print(f"User {user_profile.id} invited {invited_user_profile.id}")
# =======================================
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
