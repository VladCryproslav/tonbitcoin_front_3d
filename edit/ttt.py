import csv
import os
import time
import traceback
from aiogram.types import User
from pytonapi import AsyncTonapi
import django



os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import AsicsCoefs, AutoWithdrawalRequest, BufferTransaction, UserProfile, NFTRentalAgreement, UserStaking, WalletInfo, UserBurnedTBTC
from tasks.models import UserReward
from django.utils import timezone

import logging
from django.db.models import F

# UserBurnedTBTC.objects.filter(unlock_date_1=timezone.datetime(2025, 9, 3)).update(amount=F("amount") *4/5)


# print(UserReward.objects.all().delete())

# print(UserProfile.objects.exclude(ton_wallet="").exclude(ton_wallet=None).count())
# WALLET INFOS
# i=0
# counts = UserProfile.objects.count()
# for u in UserProfile.objects.all():
#     if not u.ton_wallet:
#         continue
#     UserProfile.objects.filter(user_id=u.user_id).update(
#         prev_ton_wallet=u.ton_wallet,
#     )
#     info = WalletInfo.objects.filter(user=u).first()
#     if info is None:
#         WalletInfo.objects.create(
#             user=u,
#             wallet=u.ton_wallet,
#             kw_amount=u.energy,
#             tbtc_amount=u.mined_tokens_balance,
#             tbtc_amount_s21=u.mined_tokens_balance_s21,
#             tbtc_amount_sx=u.mined_tokens_balance_sx,
#         )
#     i+=1
#     if i % 100 == 0:
#         print(f"{i}/{counts}")
# END

# a = 0
# b = 0

# a += UserProfile.objects.filter(
#     referrer_level_2=UserProfile.objects.get(user_id=1317239556)
# ).count()

# # REEEEEEEEEFS
# for user in UserProfile.objects.all():
#     for u in UserProfile.objects.filter(
#             referrer=UserProfile.objects.get(user_id=user.user_id)
#         ):
#         for u2 in UserProfile.objects.filter(
#             referrer=u
#         ):
#             if u2.referrer_level_2 is None or u2.referrer_level_2.user_id != user.user_id:
#                 print(u2.user_id)
#             a += 1
#             b += 1
# # END
    
# print(a, b)
    # if u.referrer.referrer.user_id == 1317239556:
    #     print(u.user_id, u.referrer.referrer.user_id, u.referrer_level_2.user_id)
    # if u.referrer !=/ 
    # print(u.user_id)


# AutoWithdrawalRequest.objects.all().update(status="ok")

# print(UserProfile.objects.filter(ton_wallet="").count()+
# UserProfile.objects.filter(ton_wallet=None).count())
# print(UserProfile.objects.all().count())

# UserProfile.objects.all().update(
#     ton_wallet=None,
#     kw_address=None,
#     tbtc_address=None,
# )


# UserProfile.objects.filter(
#     user_id=678886913
# ).update(
#     station_type="Coal power plant",
#     storage_level=1,
#     energy=142.40
# )

# print(UserProfile.objects.filter(referrer__user_id=6841260272).count())



# print(UserProfile.objects.get(id=14862).sbt_get_staking(10000))

# for u in UserProfile.objects.exclude(
#         rent_total_mining_speed_plus=0
#     ):
#     u.recalc_rent()


# for u in UserProfile.objects.exclude(
#         rent_total_mining_speed_minus=0
#     ):
#     u.recalc_rent()


# for u in UserProfile.objects.exclude(
#         rent_farm_consumption_plus=0
#     ):
#     u.recalc_rent()


# for u in UserProfile.objects.exclude(
#         rent_farm_consumption_minus=0
#     ):
#     u.recalc_rent()

# for r in NFTRentalAgreement.objects.all():
#     c = NFTRentalAgreement.objects.filter(
#         nft=r.nft
#     ).count()
#     if c > 1:
#         print(c, r.nft)
# print(UserProfile.objects.filter(manager_expires__gt=timezone.now()).update(manager_buy_hashrate=F("mining_farm_speed")))

# import traceback
# from django.apps import AppConfig
# from django.conf import settings
# import telebot

# import time

# bot = telebot.TeleBot(settings.BOT_TOKEN)
# webhook_url = settings.WEBHOOK_URL
# bot.remove_webhook()
# time.sleep(5)
# print(bot.set_webhook(url=webhook_url))

# print(AutoWithdrawalRequest.objects.filter(
#         status="pending",
#         claimed_at__lt=timezone.now() - timezone.timedelta(minutes=10),
#         claimed_at__gt=timezone.now() - timezone.timedelta(days=5),
# ).update(status="ok"))

# print(UserProfile.objects.filter(kw_wallet=F("tbtc_wallet")).exclude(kw_wallet=0).count())
#print(UserProfile.objects.filter(engineer_level=65).update(engineer_level=F('engineer_level') - 1))