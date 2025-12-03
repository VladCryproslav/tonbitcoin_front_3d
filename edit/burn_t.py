import csv
import os
import time
import traceback
from pytonapi import AsyncTonapi
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from django.utils import timezone

import logging
from django.db.models import F

from core.models import BurnedTBTCBase, UserBurnedTBTC, UserProfile

    # user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True)
    # wallet = models.CharField(max_length=255, verbose_name="Wallet Address")
    # amount = models.FloatField(verbose_name="Total Amount")
    # apr = models.FloatField(verbose_name="APR %", default=24)
    
    # unlock_date_1 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 1")
    # unlock_date_2 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 2")
    # unlock_date_3 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 3")
    # unlock_date_4 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 4")
    # unlock_date_5 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 5")
    # unlock_date_6 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 6")

import pytoniq_core

def wallet_readable(wallet):
    return pytoniq_core.Address(wallet).to_str(is_user_friendly=False)

def parse_burned_tbtc_csv(csv_file_path):
    
    with open(csv_file_path, 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            user_id = int(row['ID'].strip())
            wallet = row['Wallet'].strip()
            wallet = wallet_readable(wallet)
            amount = float(row['Amount'].strip().replace(",","."))
            
            BurnedTBTCBase.objects.create(
                wallet=wallet,
                amount=amount
            )
            # потрібно створити або добавити існуючий amount по user_id
            if UserBurnedTBTC.objects.filter(user__user_id=user_id).exists():
                UserBurnedTBTC.objects.filter(user__user_id=user_id).update(
                    amount=F("amount") + amount
                )
            else:
                user = UserBurnedTBTC.objects.create(
                    user=UserProfile.objects.filter(user_id=user_id).first(),
                    amount=amount,
                    wallet=wallet,
                    unlock_date_1=timezone.datetime(2025, 9, 3),
                    unlock_date_2=timezone.datetime(2025, 10, 3),
                    unlock_date_3=timezone.datetime(2025, 11, 3),
                    unlock_date_4=timezone.datetime(2025, 12, 3),
                    unlock_date_5=timezone.datetime(2026, 1, 3),
                    unlock_date_6=None,
                )
                user.save()
            print(f"Додано: {wallet} - {amount} tBTC")

if __name__ == "__main__":
    # Вкажіть шлях до вашого CSV файлу
    csv_file_path = "burned_tbtc.csv"  # Замініть на ваш шлях
    
    try:
        parse_burned_tbtc_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Файл {csv_file_path} не знайдено!")
    except Exception as e:
        print(f"Помилка: {e}")