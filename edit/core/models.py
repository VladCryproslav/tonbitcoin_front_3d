import csv
import hashlib
import logging
import math
import random
import re
import time
import traceback
from datetime import datetime, timedelta
import uuid

try:
    import base58
except ImportError:
    # Fallback для base58 если библиотека не установлена
    base58 = None

from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone

from tasks.models import Booster, UserReward


def add_chart_tbtc(value: float):
    """
    Добавить значение к графику tbtc_mined.
    Использует get_or_create + update для избежания блокировок при конкурентных вызовах.
    """
    today = timezone.now().date()
    max_retries = 3
    for attempt in range(max_retries):
        try:
            with transaction.atomic():
                # Используем get_or_create для атомарного получения или создания записи
                chart_data, created = ChartData.objects.get_or_create(
                    date=today,
                    chart_type="tbtc_mined",
                    defaults={"value": 0}
                )
                # Обновляем значение атомарно через F() выражение
                ChartData.objects.filter(id=chart_data.id).update(
                    value=F("value") + value
                )
            break  # Успешно выполнили операцию
        except Exception as e:
            if attempt == max_retries - 1:
                # Если все попытки неудачны, логируем ошибку
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to update chart_data after {max_retries} attempts: {e}")
            else:
                # Небольшая задержка перед повторной попыткой
                import time
                time.sleep(0.1 * (attempt + 1))


# Create your models here.
class RoadmapItem(models.Model):
    STATUS_CHOICES = [
        (1, "Виконано"),
        (2, "В процесі"),
        (3, "В майбутньому"),
    ]

    title = models.CharField(max_length=255, verbose_name="Назва пункту")
    title_en = models.CharField(max_length=255, verbose_name="Назва пункту EN", blank=True)
    title_ru = models.CharField(max_length=255, verbose_name="Назва пункту RU", blank=True)
    status = models.PositiveSmallIntegerField(
        choices=STATUS_CHOICES, default=3, verbose_name="Стан"
    )
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    item_date = models.DateField(null=True, blank=True, verbose_name="Дата")

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.title


from django.contrib.auth.models import User
from django.db import models
from django.db.models import Case, F, Value, When

from shared import setup_logger

action_logger = setup_logger()


def generate_random_dates(start: datetime, n):
    """
    Генерирует случайные даты остановки майнинга.
    КРИТИЧНО: Все даты должны быть в будущем относительно start.
    """
    start_of_day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)  # 23:59:59 того же дня
    
    # Первая дата должна быть в будущем относительно start, но не позже конца дня
    min_first_time = start + timedelta(minutes=1)  # Минимум через 1 минуту от start
    max_first_time = min(end_of_day, start + timedelta(hours=22))  # Максимум до конца дня или через 22 часа
    
    if min_first_time > max_first_time:
        # Если start слишком близко к концу дня, генерируем даты на следующий день
        start_of_day = start_of_day + timedelta(days=1)
        end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
        min_first_time = start_of_day
        max_first_time = start_of_day + timedelta(hours=21, minutes=59)
    
    first_time = min_first_time + timedelta(
        seconds=random.randint(0, int((max_first_time - min_first_time).total_seconds()))
    )
    times = [first_time]

    for _ in range(n - 1):
        min_next_time = times[-1] + timedelta(hours=4)
        max_next_time = end_of_day

        if min_next_time > max_next_time:
            # Если следующая дата выходит за пределы дня, генерируем на следующий день
            start_of_day = start_of_day + timedelta(days=1)
            end_of_day = start_of_day + timedelta(days=1) - timedelta(seconds=1)
            min_next_time = start_of_day
            max_next_time = start_of_day + timedelta(hours=21, minutes=59)

        if min_next_time > max_next_time:
            break

        next_time = min_next_time + timedelta(
            seconds=random.randint(
                0, int((max_next_time - min_next_time).total_seconds())
            )
        )
        if next_time > max_next_time:
            break
        times.append(next_time)

    return times


def parse_csv_to_dicts(csv_content: str):
    equipments = {}
    reader = csv.DictReader(csv_content.splitlines())
    for row in reader:
        name = row["Name"]
        equipment = {
            "rarity": row["Rarity"],
            "hash_rate": int(row["Hash Rate"]),
            "consumption_kw": int(row["Consumption (kW)"] or 0),
            "mining_speed_tbtc": float(
                row["Mining speed (tBTC)"].replace(",", ".") or 0
            ),
            "price_ton": float(str(row["Price (TON)"] or 0).replace(",", ".")),
        }
        equipments[name] = equipment
    return equipments


csv_data = """Rarity,Name,Hash Rate,Measurement,Consumption (kW),Mining speed (tBTC),Price (TON)
Common,Asic S1,100,Hour,1,"0,01",0.05
Common,Asic S3,200,Hour,2,"0,02",0.1
Rare,Asic S5+,400,Hour,4,"0,04",0.2
Rare,Asic S7+,1000,Hour,10,"0,10",0.4
Rare,Asic S9+,2500,Hour,20,"0,26",0.8
Epic,Asic S11 XP,6000,Hour,44,"0,62",1.6
Epic,Asic S15 XP,15000,Hour,92,"1,56",3.2
Epic,Asic S17 XP,40000,Hour,192,"4,16",6.4
Legendary,Asic S19 XP+,100000,Hour,400,"10,41",12.8
Legendary,Asic S21 XP+,250000,Hour,800,"26,04",25.6
Mythic,Asic SX Ultra Pro,600000,Hour,1664,"62,5",51.2
Special,Asic S10 Maxx,1000,Hour,80,"5",32
Special,Asic S30 Maxx,2000,Hour,80,"10",64
Special,Asic S50 Maxx,2800,Hour,80,"15",128
Special,Asic S70 Maxx,5000,Hour,80,"25",128
Special,Asic S90 Maxx,7500,Hour,80,"40",256
"""

asics_data = parse_csv_to_dicts(csv_data)

# МИГРАЦИЯ NFT → SOLANA ASSETS: Boost Assets
# Цены бустов в SOL (по аналогии с asics_data)
# Формат: (boost_type, boost_class): price_sol
boosts_data = {
    # Jarvis Bot - цены зависят от класса (со скидкой -50%)
    ('jarvis', 4): 1.0,  # Было: 1.0, стало: 0.5 SOL
    ('jarvis', 3): 2.0,  # Было: 2.0, стало: 1.0 SOL
    ('jarvis', 2): 4.0,  # Было: 4.0, стало: 2.0 SOL
    ('jarvis', 1): 7.0,  # Было: 7.0, стало: 3.5 SOL
    
    # Cryochamber - цены зависят от класса (со скидкой -50%)
    ('cryo', 3): 1.0,  # Было: 1.0, стало: 0.5 SOL
    ('cryo', 2): 2.0,  # Было: 2.0, стало: 1.0 SOL
    ('cryo', 1): 4.0,  # Было: 4.0, стало: 2.0 SOL
    
    # ASIC Manager - цены зависят от класса (со скидкой -50%)
    ('asic_manager', 3): 0.5,  # Было: 0.5, стало: 0.3 SOL (округлено от 0.25)
    ('asic_manager', 2): 1.0,  # Было: 1.0, стало: 0.5 SOL
    ('asic_manager', 1): 2.0,  # Было: 2.0, стало: 1.0 SOL
    
    # Magnetic ring - цены зависят от класса (со скидкой -50%)
    ('magnit', 2): 1.0,  # Было: 1.0, стало: 0.5 SOL
    ('magnit', 1): 2.0,  # Было: 2.0, стало: 1.0 SOL
    
    # Electrics - без классов (со скидкой -50%)
    ('electrics', 1): 1.0,  # Было: 1.0, стало: 0.5 SOL
}

# Конфигурация премиальных станций (Solana)
premium_stations_data = {
    'Hydroelectric Power Plant': {
        'price_sol': 1.0,
        'storage': 1000,
        'generation': 250,
        'engineers': 25,
        'station_type_mapping': 'Nuclear power plant',
    },
    'Orbital Power Plant': {
        'price_sol': 2.0,
        'storage': 2320,
        'generation': 460,
        'engineers': 35,
        'station_type_mapping': 'Thermonuclear power plant',
    },
    'Singularity Reactor': {
        'price_sol': 4.0,
        'storage': 2690,
        'generation': 800,
        'engineers': 45,
        'station_type_mapping': 'Dyson Sphere',
    },
    'Proton Star': {
        'price_sol': 8.0,
        'storage': 5350,
        'generation': 1400,
        'engineers': 55,
        'station_type_mapping': 'Neutron star',
    },
    'Dark Matter': {
        'price_sol': 16.0,
        'storage': 9450,
        'generation': 2430,
        'engineers': 64,
        'station_type_mapping': 'Antimatter',
    },
}

from django.conf import settings
from telebot import TeleBot
from django.contrib.auth.hashers import make_password, check_password

bot = TeleBot(settings.BOT_TOKEN, parse_mode="HTML")

    # username = models.CharField(max_length=150, unique=True)
    # email = models.EmailField(unique=True)
    # password = models.CharField(max_length=128)
    
    # def set_password(self, raw_password):
    #     self.password = make_password(raw_password)
    #     self.save(update_fields=["password"])

    # def check_password(self, raw_password):
    #     return check_password(raw_password, self.password)

class UserProfile(models.Model):
    id = models.BigAutoField(
        primary_key=True
    )  # Унікальний ідентифікатор користувача
    user_id = models.BigIntegerField(null=True, blank=True)
    
    username = models.CharField(max_length=255, null=False, blank=False)
    email = models.EmailField(unique=True, null=False, blank=False)
    password_hash = models.CharField(max_length=128, null=False, blank=False)
    email_confirmed = models.BooleanField(default=False)
    email_confirmation_code = models.CharField(max_length=16, null=True, blank=True, db_index=True)
    
    energy = models.FloatField(default=0)  # Енергія в кіловатах
    kw_wallet = models.FloatField(default=0)  # Енергія в кіловатах
    tbtc_wallet = models.FloatField(default=0)  # Енергія в кіловатах
    ton_wallet = models.CharField(blank=True, max_length=255, null=True, db_index=True)
    prev_ton_wallet = models.CharField(blank=True, max_length=255, null=True, db_index=True)
    kw_address = models.CharField(blank=True, max_length=255, null=True)
    tbtc_address = models.CharField(blank=True, max_length=255, null=True)

    station_type = models.CharField(max_length=255, default="Boiler house")
    storage_level = models.PositiveIntegerField(default=1)
    generation_level = models.PositiveIntegerField(default=1)
    engineer_level = models.PositiveIntegerField(default=1)  # Рівень інженера
    
    
    # HYDRO UPDATE
    has_hydro_station = models.BooleanField(default=False)  # Чи є гідроелектростанція
    has_orbital_station = models.BooleanField(default=False)  # Чи є орбітальна станція
    orbital_first_owner = models.BooleanField(default=False)  # Чи є орбітальна станція
    orbital_is_blue = models.BooleanField(default=False)  # Чи є орбітальна станція
    orbital_force_basic = models.BooleanField(default=False)
    current_station_nft = models.CharField(max_length=255, default="", blank=True)
    hydro_prev_energy = models.FloatField(default=0)
    hydro_prev_power = models.FloatField(default=100)
    hydro_prev_station_type = models.CharField(max_length=255, default="", blank=True)
    hydro_prev_storage_level = models.IntegerField(default=None, blank=True, null=True)
    hydro_prev_generation_level = models.IntegerField(default=None, blank=True, null=True)
    hydro_prev_engineer_level = models.IntegerField(default=None, blank=True, null=True)  # Рівень інженера
    # ============

    # Премиальные станции (Solana)
    has_hydroelectric_power_plant_station = models.BooleanField(default=False)
    has_orbital_power_plant_station = models.BooleanField(default=False)
    has_singularity_reactor_station = models.BooleanField(default=False)
    has_proton_star_station = models.BooleanField(default=False)
    has_dark_matter_station = models.BooleanField(default=False)

    premium_station_type = models.CharField(max_length=255, default="", blank=True)
    premium_station_asset = models.ForeignKey(
        'UserAsset', null=True, blank=True, on_delete=models.SET_NULL, related_name='premium_station_user'
    )

    # Активная станция из улучшения (5+ уровень)
    active_upgraded_station = models.ForeignKey(
        'UserStation', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL,
        related_name='active_station_user',
        help_text="Активная станция, полученная через улучшение (5+ уровень)"
    )

    # Сохраненное состояние до активации премиальной станции
    prev_station_energy = models.FloatField(default=0)
    prev_station_power = models.FloatField(default=100)
    prev_station_type = models.CharField(max_length=255, default="", blank=True)
    prev_station_storage_level = models.IntegerField(default=None, blank=True, null=True)
    prev_station_generation_level = models.IntegerField(default=None, blank=True, null=True)
    prev_station_engineer_level = models.IntegerField(default=None, blank=True, null=True)
    prev_station_building_until = models.DateTimeField(null=True, blank=True)  # Сохраненный таймер постройки
    
    past_engineer_level = models.IntegerField(default=0)  # Рівень інженера
    kw_per_tap = models.FloatField(default=0.025)  # Кількість кВ на тап
    storage = models.DecimalField(max_digits=36, decimal_places=16, default=10)
    storage_limit = models.DecimalField(max_digits=36, decimal_places=16, default=10)
    generation_rate = models.DecimalField(max_digits=36, decimal_places=16, default=5)
    
    # Energy Run (Раннер)
    energy_run_last_started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Время последнего старта забега (для cooldown 60 минут)"
    )
    energy_run_start_storage = models.DecimalField(
        max_digits=36, 
        decimal_places=16, 
        default=0,
        null=True,
        blank=True,
        help_text="Storage при старте забега (для валидации)"
    )
    
    power = models.DecimalField(max_digits=36, decimal_places=16, default=100)
    referrer = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals",
    )
    referrer_level_2 = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referrals_level_2",
    )
    referral_code = models.CharField(
        max_length=16,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
    )

    # Нові поля для зберігання інформації про рефералів та отримані бонуси
    first_name = models.CharField(max_length=255, null=True, blank=True)
    bonus_kw_level_1 = models.FloatField(default=0)
    bonus_kw_level_2 = models.FloatField(default=0)
    bonus_tbtc_level_1 = models.FloatField(default=0)
    bonus_tbtc_level_2 = models.FloatField(default=0)
    bonus_invest_level_1 = models.FloatField(default=0)
    bonus_invest_level_2 = models.FloatField(default=0)

    bring_bonus_kw_level_1 = models.FloatField(default=0)
    bring_bonus_kw_level_2 = models.FloatField(default=0)
    bring_bonus_tbtc_level_1 = models.FloatField(default=0)
    bring_bonus_tbtc_level_2 = models.FloatField(default=0)
    bring_bonus_invest_level_1 = models.FloatField(default=0)
    bring_bonus_invest_level_2 = models.FloatField(default=0)

    # Нові поля для екрану Miner
    battery_balance = models.FloatField(default=0)  # Баланс акумулятора
    nft_count = models.PositiveIntegerField(default=0)  # Кількість NFT
    mining_farm_speed = models.FloatField(default=0)  # Швидкість майнинг ферми
    total_mining_speed = models.FloatField(
        default=0
    )  # Загальна швидкість видобування токенів фермою в годину
    mined_tokens_balance = models.FloatField(
        default=0
    )  # Баланс намайнених токенів фермою

    # Окремі баланси для S21/SX асиків
    mined_tokens_balance_s21 = models.FloatField(
        default=0, verbose_name="Баланс майнінгу S21"
    )
    mined_tokens_balance_sx = models.FloatField(
        default=0, verbose_name="Баланс майнінгу SX"
    )

    def total_mined_tokens_balance(self):
        return (
            self.mined_tokens_balance
            + self.mined_tokens_balance_s21
            + self.mined_tokens_balance_sx
        )

    total_farm_consumption = models.FloatField(
        default=0
    )  # Загальна сума витрат ферми в kW/h
    farm_runtime = models.FloatField(
        default=0
    )  # Час роботи ферми, враховуючи кількість енергії на акумуляторі та загальне споживання асиків
    miner_referrals_count = models.PositiveIntegerField(
        default=0
    )  # Кількість рефералів-майнерів
    is_mining = models.BooleanField(default=False)  # Чи йде зараз майнінг
    nft_string = models.TextField(blank=True, default="")  # Строка з усіма NFT
    started_mining_at = models.DateTimeField(
        null=True, blank=True
    )  # Час початку майнінгу
    true_started_mining_at = models.DateTimeField(null=True, blank=True)
    mining_period = models.PositiveIntegerField(default=0)  # Період майнінгу
    last_tbtc_added = models.DateTimeField(null=True, blank=True)
    # last_tap = models.DateTimeField(null=True, blank=True)
    register_date = models.DateTimeField(auto_now_add=True)

    tbtc_claimed_period = models.PositiveIntegerField(default=0)

    tap_count = models.PositiveIntegerField(default=0)

    overheated_until = models.DateTimeField(null=True, blank=True)  # New field
    tap_count_since_overheat = models.PositiveIntegerField(default=0)  # New field
    overheat_energy_collected = models.FloatField(default=0)  # New field
    overheat_goal = models.FloatField(null=True, blank=True, default=None)  # New field
    was_overheated = models.BooleanField(default=False)  # New field
    last_kw_bonus_claimed_at = models.DateTimeField(auto_now_add=True)  # New field
    last_tbtc_bonus_claimed_at = models.DateTimeField(auto_now_add=True)  # New field
    last_staking_bonus_claimed_at = models.DateTimeField(auto_now_add=True)  # New field

    # ====== BOOSTERS ======
    azot_activated = models.DateTimeField(null=True, blank=True)
    azot_counts = models.IntegerField(default=0)
    azot_uses_left = models.IntegerField(default=0)
    azot_reward_balance = models.IntegerField(default=0)  # Баланс винагород powerbank з колеса

    jarvis_expires = models.DateTimeField(null=True, blank=True)

    cryo_expires = models.DateTimeField(null=True, blank=True)

    autostart_count = models.IntegerField(default=0)

    is_powerbank_active = models.BooleanField(default=False)
    powerbank_activated = models.DateTimeField(null=True, blank=True)
    powerbank_max_consume = models.FloatField(default=0)
    powerbank_uses_left = models.IntegerField(default=0)
    powerbank_reward_balance = models.IntegerField(default=0)  # Баланс винагород powerbank з колеса

    magnit_expires = models.DateTimeField(null=True, blank=True)
    magnit_buy_hashrate = models.FloatField(default=0)

    manager_expires = models.DateTimeField(null=True, blank=True)
    manager_buy_hashrate = models.FloatField(default=0)

    electrics_expires = models.DateTimeField(null=True, blank=True)
    
    premium_sub_expires = models.DateTimeField(null=True, blank=True)

    stop_mining_at1 = models.DateTimeField(null=True, blank=True)
    stop_mining_at2 = models.DateTimeField(null=True, blank=True)
    stop_mining_at3 = models.DateTimeField(null=True, blank=True)
    stop_mining_next = models.DateTimeField(null=True, blank=True)
    stop_mining_window_start = models.DateTimeField(null=True, blank=True)  # Начало 24-часового окна для генерации дат остановки
    stop_mining_activate_last = models.DateTimeField(null=True, blank=True)
    mining_last_stopped = models.DateTimeField(null=True, blank=True)

    mining_was_stopped = models.BooleanField(default=False)
    # ======================

    wheel_slot2 = models.BooleanField(default=False)
    blocked = models.BooleanField(default=False)
    # ======= MINT STATIONS =======
    building_until = models.DateTimeField(null=True, blank=True)
    mint_string = models.TextField(blank=True, default="")
    current_mint = models.TextField(blank=True, default="")

    # ========= RENT NFT ==============
    points = models.FloatField(default=0)
    rent_blocked_until = models.DateTimeField(null=True, blank=True)
    rent_mined_tokens_balance = models.FloatField(default=0)

    rent_total_mining_speed_plus = models.FloatField(default=0)
    rent_total_mining_speed_minus = models.FloatField(default=0)
    rent_farm_consumption_plus = models.FloatField(default=0)
    rent_farm_consumption_minus = models.FloatField(default=0)

    has_gold_sbt = models.BooleanField(default=False)
    has_silver_sbt = models.BooleanField(default=False)
    has_gold_sbt_nft = models.BooleanField(default=False)
    has_silver_sbt_nft = models.BooleanField(default=False)
    
    def get_real_engs(self):
        engs = self.engineer_level
        
        # МИГРАЦИЯ NFT → SOLANA ASSETS: Используем get_active_boosts() вместо проверки electrics_expires
        # ЛОГИКА ПРИМЕНЕНИЯ ELECTRICS НЕ МЕНЯЕТСЯ - меняется только способ проверки наличия буста
        active_boosts = self.get_active_boosts()
        if 'electrics' in active_boosts:  # Проверка БД вместо проверки NFT на кошельке
            # ЛОГИКА ПРИМЕНЕНИЯ ELECTRICS (ОСТАЕТСЯ ПРЕЖНЕЙ)
            engs += int(Booster.objects.filter(slug="electrics").first().n1)
        
        if self.engineer_level < 49:
            engs += max(0, self.past_engineer_level-49)
        return min(64, engs)

    def sbt_get_stars_discount(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 0.9
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 0.95
        return 1

    def sbt_get_kw_commision(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 0.04
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 0.045
        return 0.05

    def sbt_get_claim_commision(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 0.007
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 0.0085
        return 0.01

    def sbt_get_power(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 0.9
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 0.95
        return 1

    def sbt_get_tap_power_bonus(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 1.1
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 1.05
        return 1

    def sbt_get_building_reduction(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 0.8
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 0.9
        return 1

    def sbt_get_building_reduction(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 0.8
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 0.9
        return 1

    def sbt_get_staking(self, input_amount):
        if self.can_use_staking_bonus(input_amount):
            gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
            premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
            if gold_sbt or premium_sub:
                return 5
            if self.has_silver_sbt and self.has_silver_sbt_nft:
                return 2
        return 0

    def sbt_get_azots(self):
        gold_sbt = self.has_gold_sbt and self.has_gold_sbt_nft
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if gold_sbt or premium_sub:
            return 1
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 1
        return 0
    
    def sbt_get_jarvis(self):
        premium_sub = self.premium_sub_expires and self.premium_sub_expires > timezone.now()
        if premium_sub:
            return 1.05
        return 1
    
    def get_active_boosts(self):
        """
        Возвращает активные бусты пользователя (из BoostAsset и временные)
        
        ВАЖНО: Логика применения бустов НЕ меняется!
        Этот метод только заменяет проверку NFT на кошельке на проверку БД.
        
        Returns:
            dict: Словарь активных бустов вида {
                'jarvis': {'source': 'asset', 'class': 1, 'expires': datetime},
                'magnit': {'source': 'temporary', 'expires': datetime},
                ...
            }
        """
        from core.utils import check_boost_class_conditions
        from datetime import datetime
        
        now = timezone.now()
        infinite_date = datetime(2100, 1, 1, 0, 0, 0)
        
        active_boosts = {}
        
        # Проверяем вечные бусты из BoostAsset (ЗАМЕНА проверки NFT на кошельке)
        boost_assets = BoostAsset.objects.filter(
            user=self,
            status='success',
            is_enabled=True  # Только включенные бусты
        )
        
        # Сначала собираем все активные бусты (те, что соответствуют условиям)
        for asset in boost_assets:
            # Проверяем условия класса (та же логика, что была для NFT)
            conditions_met = check_boost_class_conditions(self, asset.boost_type, asset.boost_class)
            
            if conditions_met:
                active_boosts[asset.boost_type] = {
                    'source': 'asset',
                    'class': asset.boost_class,
                    'expires': infinite_date,  # Вечный буст (как было с NFT)
                }
        
        # ВАЖНО: Очищаем expires только если НЕТ активных бустов этого типа
        # Это исправляет баг, когда expires очищался при первом несоответствии,
        # даже если есть другой активный буст того же типа
        update_fields = []
        
        # Проверяем jarvis
        if 'jarvis' not in active_boosts:
            if self.jarvis_expires and self.jarvis_expires.year == 2100:
                self.jarvis_expires = None
                update_fields.append('jarvis_expires')
        
        # Проверяем magnit
        if 'magnit' not in active_boosts:
            if self.magnit_expires and self.magnit_expires.year == 2100:
                self.magnit_expires = None
                update_fields.append('magnit_expires')
        
        # Проверяем asic_manager
        if 'asic_manager' not in active_boosts:
            if self.manager_expires and self.manager_expires.year == 2100:
                self.manager_expires = None
                update_fields.append('manager_expires')
                # Для Manager также очищаем даты остановки
                self.stop_mining_at1 = None
                self.stop_mining_at2 = None
                self.stop_mining_at3 = None
                self.stop_mining_next = None
                update_fields.extend(['stop_mining_at1', 'stop_mining_at2', 'stop_mining_at3', 'stop_mining_next'])
        
        # Проверяем cryo
        if 'cryo' not in active_boosts:
            if self.cryo_expires and self.cryo_expires.year == 2100:
                self.cryo_expires = None
                update_fields.append('cryo_expires')
        
        # Проверяем electrics
        if 'electrics' not in active_boosts:
            if self.electrics_expires and self.electrics_expires.year == 2100:
                self.electrics_expires = None
                update_fields.append('electrics_expires')
        
        # Сохраняем изменения одним запросом
        if update_fields:
            self.save(update_fields=update_fields)
        
        # Проверяем временные бусты (покупка за звезды) - остается как есть
        if self.jarvis_expires and self.jarvis_expires > now and self.jarvis_expires.year != 2100:
            if 'jarvis' not in active_boosts:  # Временный имеет приоритет только если нет вечного
                active_boosts['jarvis'] = {
                    'source': 'temporary',
                    'expires': self.jarvis_expires,
                }
        
        if self.magnit_expires and self.magnit_expires > now and self.magnit_expires.year != 2100:
            if 'magnit' not in active_boosts:
                active_boosts['magnit'] = {
                    'source': 'temporary',
                    'expires': self.magnit_expires,
                }
        
        if self.manager_expires and self.manager_expires > now and self.manager_expires.year != 2100:
            if 'asic_manager' not in active_boosts:
                active_boosts['asic_manager'] = {
                    'source': 'temporary',
                    'expires': self.manager_expires,
                }
        
        if self.cryo_expires and self.cryo_expires > now and self.cryo_expires.year != 2100:
            if 'cryo' not in active_boosts:
                active_boosts['cryo'] = {
                    'source': 'temporary',
                    'expires': self.cryo_expires,
                }
        
        if self.electrics_expires and self.electrics_expires > now and self.electrics_expires.year != 2100:
            if 'electrics' not in active_boosts:
                active_boosts['electrics'] = {
                    'source': 'temporary',
                    'expires': self.electrics_expires,
                }
        
        return active_boosts



    def can_use_staking_bonus(self, input_amount):
        BONUS_LIMIT = 100_000
        total_locked = (
            UserStaking.objects.filter(user=self, status="active").aggregate(
                total=models.Sum("token_amount")
            )["total"]
            or 0
        )
        return (total_locked + input_amount) <= BONUS_LIMIT

    # def save(self, *args, **kwargs):
    #     # try:
    #     #     self.storage_limit = StoragePowerStationConfig.objects.get(
    #     #         station_type=self.station_type, level=self.storage_level
    #     #     ).storage_limit
    #     #     self.generation_rate = GenPowerStationConfig.objects.get(
    #     #         station_type=self.station_type, level=self.generation_level
    #     #     ).generation_rate
    #     #     self.kw_per_tap = EngineerConfig.objects.get(
    #     #         level=self.engineer_level
    #     #     ).tap_power
    #     # except Exception:
    #     #     logging.exception(f"User save error {self.user_id}")
    #     if not self.pk:
    #         super().save(*args, **kwargs)
    #         self.user_id = self.pk
    #     super().save(*args, **kwargs)

    def recalc_rent(self):
        rent_total_mining_speed_plus = 0
        rent_total_mining_speed_minus = 0
        rent_farm_consumption_plus = 0
        rent_farm_consumption_minus = 0

        for rental in NFTRentalAgreement.objects.filter(
            end_date__gte=timezone.now(), renter=self
        ):
            rent_total_mining_speed_plus += (
                NFTDatabase.objects.filter(nft=rental.nft).first().mining_speed_tbtc
                * (100 - rental.owner_percentage)
                / 100
            )
            rent_farm_consumption_plus += (
                NFTDatabase.objects.filter(nft=rental.nft).first().consumption_kw
            )

        for rental in NFTRentalAgreement.objects.filter(owner=self):
            rent_total_mining_speed_minus += (
                NFTDatabase.objects.filter(nft=rental.nft).first().mining_speed_tbtc
            )
            rent_farm_consumption_minus += (
                NFTDatabase.objects.filter(nft=rental.nft).first().consumption_kw
            )

        UserProfile.objects.filter(user_id=self.user_id).update(
            rent_total_mining_speed_plus=rent_total_mining_speed_plus,
            rent_total_mining_speed_minus=rent_total_mining_speed_minus,
            rent_farm_consumption_plus=rent_farm_consumption_plus,
            rent_farm_consumption_minus=rent_farm_consumption_minus,
        )

        self.refresh_from_db()

    def stop_all_rents(self):
        rented_nfts = NFTRentalAgreement.objects.filter(renter=self)
        for r in rented_nfts:
            try:
                bot.send_message(
                    self.user_id,
                    f"""<b>🔔 Аренда {r.name} завершена</b>

Аренда была автоматически завершена из-за невыполнения условий.

Возможные причины:
1. Недостаточно kW для обеспечения работы арендованного ASIC на следующие 24 часа.
2. Устройство не было в сети (отсутствие интернета) в течение 12 часов после потери соединения.

Ваш рейтинг арендатора: {int(self.points)} балл из максимально допустимых -3 баллов.
При достижении -3 баллов, аренда ASIC-оборудования будет заблокирована на 7 дней.""",
                )
                bot.send_message(
                    r.owner.user_id,
                    f"""<b>🔔 Аренда {r.name} завершена

Аренда вашего ASIC была автоматически завершена из-за невыполнения условий со стороны арендатора.

Возможные причины:
1. У арендатора было недостаточно kW для продолжения работы оборудования.
2. Устройство арендатора не было в сети более 12 часов после потери соединения.

ASIC возвращён в раздел "Оборудование", чтобы снова сдать его в аренду — создайте новую заявку в меню Инвестора.""",
                )
            except Exception:
                pass
        NFTRentalAgreement.objects.filter(renter=self).update(
            start_date=None,
            end_date=None,
            renter=None,
            total_collected_owner=0,
            total_collected_renter=0,
            mining_speed_tbtc=0,
        )
        self.recalc_rent()

    def remove_point(self):
        action_logger.info(f"{datetime.now()} | REMOVE POINT {self.user_id}")
        UserProfile.objects.filter(user_id=self.user_id).update(points=F("points") - 1)
        self.refresh_from_db()
        if self.points <= -3:
            UserProfile.objects.filter(user_id=self.user_id).update(
                rent_blocked_until=timezone.now() + timezone.timedelta(days=7),
                points=0,
            )

        self.stop_all_rents()
        self.refresh_from_db()

    def get_build_price(self):
        if not self.is_building():
            return None
        config = WithdrawalConfig.objects.first()
        return (
            math.ceil(
                (self.building_until - timezone.now()).total_seconds()
                / 60
                / config.gradation_minutes
            )
            * config.gradation_value
        )

    def get_station_level(self):
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
        # Если есть премиальная станция, используем маппинг
        station_type_to_check = self.station_type
        if self.premium_station_type:
            # Маппинг премиальных станций на обычные
            premium_mapping = {
                'Hydroelectric Power Plant': 'Nuclear power plant',
                'Orbital Power Plant': 'Thermonuclear power plant',
            }
            mapped_type = premium_mapping.get(self.premium_station_type)
            if mapped_type:
                station_type_to_check = mapped_type
        
        try:
            return STATION_LEVELS.index(station_type_to_check)
        except ValueError:
            # Если станция не найдена, возвращаем -1 (будет обработано в вызывающем коде)
            return -1

    def reset_station(self):

        engineer_minus = WithdrawalConfig.objects.first().engineer_minus
        engineer_level_deduction = self.get_station_level() + engineer_minus
        StationRollbackLog.objects.create(
            user=self,
            from_station=self.station_type,
            generation_level=self.generation_level,
            storage_level=self.storage_level,
            engineer_level=self.engineer_level,
            energy=self.energy,
        )
        StationNFTOwner.objects.filter(user=self).delete()

        config_storage = StoragePowerStationConfig.objects.filter(
            station_type="Boiler house", level=1
        ).first()

        config_gen = GenPowerStationConfig.objects.filter(
            station_type="Boiler house", level=1
        ).first()

        print(config_storage.get_duration())
        # Ограничиваем storage до максимума Boiler house уровня 1
        # Конвертируем FloatField в Decimal для совместимости с DecimalField
        from decimal import Decimal
        storage_limit_decimal = Decimal(str(config_storage.storage_limit))
        UserProfile.objects.filter(user_id=self.user_id).update(
            station_type="Boiler house",
            storage_level=1,
            generation_level=1,
            storage_limit=storage_limit_decimal,
            storage=Case(
                When(storage__gt=storage_limit_decimal, then=Value(storage_limit_decimal)),
                default=F("storage"),
                output_field=models.DecimalField(max_digits=36, decimal_places=16)
            ),  # Ограничиваем storage до максимума Boiler house уровня 1
            generation_rate=config_gen.generation_rate,
            engineer_level=max(
                1, self.engineer_level - max(0, engineer_level_deduction)
            ),
            current_mint="",
            energy=0,
            building_until=timezone.now() + config_storage.get_duration(),
        )
        self.refresh_from_db()

    def generate_energy(self, divide=1):
        # actual_generation_rate = self.generation_rate * (self.power / 100)
        # self.storage += actual_generation_rate
        # if self.storage > self.storage_limit:
        #     self.storage = self.storage_limit
        # self.save()
        self.update(
            storage=Case(
                When(
                    F("storage") + F("generation_rate") * (F("power") / 100) / divide
                    > F("storage_limit"),
                    then=F("storage_limit"),
                ),
                default=F("storage")
                + F("generation_rate") * (F("power") / 100) / divide,
            )
        )

    def reduce_power(self, hours):
        reduction_percentage = (hours / (self.storage_limit / self.generation_rate)) * 2
        UserProfile.objects.filter(user_id=self.user_id).update(
            power=F("power") - reduction_percentage
        )
        UserProfile.objects.filter(user_id=self.user_id, power__lt=0).update(power=0)
        self.refresh_from_db()

    def is_building(self):
        return bool(self.building_until and self.building_until > timezone.now())

    def upgrade_storage(self):
        self.refresh_from_db()
        if self.storage_level < 3:
            next_level = self.storage_level + 1
            config = StoragePowerStationConfig.objects.get(
                station_type=self.station_type, level=next_level
            )
            if self.energy >= config.price_kw and self.tbtc_wallet >= config.price_tbtc:
                action_logger.info(
                    f"user {self.user_id} | upgrading storage {self.energy} kw, {self.tbtc_wallet} tbtc"
                )
                GlobalSpendStats.objects.update(
                    energy_spent_build=F("energy_spent_build") + config.price_kw,
                    energy_spent_upgrade=F("energy_spent_upgrade") + config.price_kw,
                    tbtc_spent_build=F("tbtc_spent_build") + config.price_tbtc,
                    tbtc_spent_upgrade=F("tbtc_spent_upgrade") + config.price_tbtc
                )

                UserProfile.objects.filter(user_id=self.user_id, energy__gt=config.price_kw).update(
                    energy=F("energy") - config.price_kw,
                    tbtc_wallet=F("tbtc_wallet") - config.price_tbtc,
                    storage_level=next_level,
                    storage_limit=config.storage_limit,
                    building_until=timezone.now()
                    + config.get_duration() * self.sbt_get_building_reduction(),
                )
                self.refresh_from_db()
                action_logger.info(
                    f"user {self.user_id} | upgraded storage {self.energy} kw, {self.tbtc_wallet} tbtc"
                )
                return True
        return False

    def upgrade_generation(self):
        self.refresh_from_db()
        if self.generation_level < 3:
            next_level = self.generation_level + 1
            config = GenPowerStationConfig.objects.get(
                station_type=self.station_type, level=next_level
            )
            if self.energy >= config.price_kw and self.tbtc_wallet >= config.price_tbtc:
                action_logger.info(
                    f"user {self.user_id} | upgrading gen {self.energy} kw, {self.tbtc_wallet} tbtc"
                )
                GlobalSpendStats.objects.update(
                    energy_spent_build=F("energy_spent_build") + config.price_kw,
                    energy_spent_upgrade=F("energy_spent_upgrade") + config.price_kw,
                    tbtc_spent_build=F("tbtc_spent_build") + config.price_tbtc,
                    tbtc_spent_upgrade=F("tbtc_spent_upgrade") + config.price_tbtc
                )

                UserProfile.objects.filter(user_id=self.user_id).update(
                    energy=F("energy") - config.price_kw,
                    tbtc_wallet=F("tbtc_wallet") - config.price_tbtc,
                    generation_level=next_level,
                    generation_rate=config.generation_rate,
                    building_until=timezone.now()
                    + config.get_duration() * self.sbt_get_building_reduction(),
                )

                action_logger.info(
                    f"user {self.user_id} | upgraded gen {self.energy} kw, {self.tbtc_wallet} tbtc"
                )
                
                StationUpgradeEvent.objects.create(
                        user=self,
                        level=f"{self.get_station_level()+1}-{self.generation_level}"
                    )
                return True
        return False

    def upgrade_engineer(self, payment_type="energy"):
        self.refresh_from_db()
        with transaction.atomic():
            next_level = self.engineer_level + 1
            config = EngineerConfig.objects.get(level=next_level)
            
            # Оплата энергией (kW)
            if payment_type == "energy" and config.hire_cost and self.energy >= config.hire_cost:
                action_logger.info(
                    f"user {self.user_id} | upgrading eng {self.energy} kw"
                )
                GlobalSpendStats.objects.update(
                    energy_spent_engineer=F("energy_spent_engineer") + config.hire_cost
                )
                if next_level == 49 and self.past_engineer_level >= 50:
                    next_level = self.past_engineer_level
                UserProfile.objects.filter(user_id=self.user_id).update(
                    energy=F("energy") - config.hire_cost,
                    engineer_level=next_level,
                    kw_per_tap=EngineerConfig.objects.get(level=next_level).tap_power,
                )
                self.refresh_from_db()
                action_logger.info(
                    f"user {self.user_id} | upgraded eng {self.energy} kw"
                )
                return True
            
            # Оплата fBTC токенами
            elif payment_type == "fbtc" and config.hire_cost_fbtc and self.tbtc_wallet >= config.hire_cost_fbtc:
                action_logger.info(
                    f"user {self.user_id} | upgrading eng {self.tbtc_wallet} tbtc (fbtc payment)"
                )
                if next_level == 49 and self.past_engineer_level >= 50:
                    next_level = self.past_engineer_level
                UserProfile.objects.filter(user_id=self.user_id).update(
                    tbtc_wallet=F("tbtc_wallet") - config.hire_cost_fbtc,
                    engineer_level=next_level,
                    kw_per_tap=EngineerConfig.objects.get(level=next_level).tap_power,
                )
                self.refresh_from_db()
                action_logger.info(
                    f"user {self.user_id} | upgraded eng {self.tbtc_wallet} tbtc (fbtc payment)"
                )
                return True
            
            return False

    def upgrade_station(self, code=None, sol_payment_signature=None):
        """
        Upgrade station with code OR SOL payment verification when transitioning between station types
        
        Args:
            code: Code for transitioning between station types (required only if target station requires code)
            sol_payment_signature: SOL transaction signature (alternative to code)
        
        Returns:
            tuple: (success: bool, error_message: str)
        """
        self.refresh_from_db()
        action_logger.info(f"UPGRADE_STATION: Called for user {self.user_id}, storage_level={self.storage_level}, generation_level={self.generation_level}")
        if self.storage_level == 3 and self.generation_level == 3:
            action_logger.info(
                f"user {self.user_id} | upgrading station {self.energy} kw, {self.tbtc_wallet} tbtc"
            )
            next_station_type = self.get_next_station_type()
            action_logger.info(f"UPGRADE_STATION: next_station_type={next_station_type}, current_station_type={self.station_type}")
            if not next_station_type:
                return False, "Maximum station level reached"
            
            # Проверяем, является ли следующая станция уровнем 5+ (Nuclear power plant и выше)
            # ВАЖНО: Используем тот же список, что и в get_next_station_type() для консистентности
            station_levels = [
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
            
            # ВАЖНО: Проверяем наличие next_station_type в списке и логируем для отладки
            if next_station_type not in station_levels:
                action_logger.error(f"UPGRADE_STATION: next_station_type '{next_station_type}' not found in station_levels list!")
                action_logger.error(f"UPGRADE_STATION: current_station_type='{self.station_type}', station_levels={station_levels}")
                # Используем тот же список для пересчета next_station_type
                try:
                    current_index = station_levels.index(self.station_type)
                    if current_index < len(station_levels) - 1:
                        next_station_type = station_levels[current_index + 1]
                        action_logger.info(f"UPGRADE_STATION: Recalculated next_station_type={next_station_type} from station_levels")
                    else:
                        return False, "Maximum station level reached"
                except ValueError:
                    action_logger.error(f"UPGRADE_STATION: Current station_type '{self.station_type}' not found in station_levels!")
                    return False, "Invalid station type"
            
            # ВАЖНО: Теперь next_station_type гарантированно есть в station_levels
            try:
                next_station_level = station_levels.index(next_station_type) + 1
            except ValueError:
                action_logger.error(f"UPGRADE_STATION: Critical error - next_station_type '{next_station_type}' still not found after recalculation!")
                return False, "Critical error: station type mismatch"
            
            is_level_5_or_higher = next_station_level >= 5
            action_logger.info(f"UPGRADE_STATION: next_station_level={next_station_level}, is_level_5_or_higher={is_level_5_or_higher}, next_station_type='{next_station_type}'")
            
            config_storage = StoragePowerStationConfig.objects.get(
                station_type=next_station_type, level=1
            )
            
            # Check: is station type changing AND does target station require code?
            is_type_change = (next_station_type != self.station_type)
            requires_code = config_storage.requires_code and is_type_change
            
            # If target station requires code - verify code OR SOL payment
            upgrade_code = None
            station_upgrade_payment = None
            
            if requires_code:
                # If SOL payment signature exists - verify it instead of code
                if sol_payment_signature:
                    try:
                        payment = SolanaPayment.objects.select_for_update().filter(
                            signature=sol_payment_signature,
                            user=self
                        ).first()
                        
                        if not payment:
                            return False, "SOL payment not found or not verified"
                        
                        # Verify that payment is associated with station upgrade
                        try:
                            station_upgrade_payment = payment.station_upgrade
                        except StationUpgradeSolPayment.DoesNotExist:
                            return False, "SOL payment not associated with station upgrade"
                        
                        # Verify that payment was not used
                        if station_upgrade_payment.used:
                            return False, "SOL payment already used for station upgrade"
                        
                        # Verify target station match
                        if station_upgrade_payment.target_station_type != next_station_type:
                            return False, "SOL payment target station mismatch"
                    
                    except Exception as e:
                        action_logger.error(f"Error checking SOL payment: {e}")
                        return False, "Error verifying SOL payment"
                
                # If neither code nor SOL payment exists - require code
                elif not code:
                    return False, "Code or SOL payment required for station type change"
                
                # If code exists - verify it (existing logic)
                else:
                    # Normalize and validate format: prefix <Ns> + 6 digits
                    code_normalized = StationUpgradeCode.normalize_code(code)
                    if not STATION_CODE_REGEX.match(code_normalized):
                        return False, "Invalid code format. Code must match <Ns><6 digits> (e.g. 1s124214)"

                    expected_station_type = StationUpgradeCode.station_type_from_code(code_normalized)
                    if not expected_station_type or expected_station_type != next_station_type:
                        return False, "Code does not match target station type"

                    # Code validation and record locking
                    # ВАЖНО: select_for_update() требует активной транзакции
                    # Транзакция должна быть открыта в вызывающем коде (views.py)
                    try:
                        upgrade_code = StationUpgradeCode.objects.select_for_update().get(
                            code=code_normalized,
                            status='active',
                        )
                        action_logger.info(f"UPGRADE_STATION: Code found and locked: {code_normalized}")
                    except StationUpgradeCode.DoesNotExist:
                        action_logger.error(f"UPGRADE_STATION: Code not found: {code_normalized}")
                        return False, "Invalid or expired code"
                    
                    if upgrade_code.station_type and upgrade_code.station_type != next_station_type:
                        return False, "Code does not match target station type"
                    
                    if not upgrade_code.is_valid():
                        # Automatically mark as expired
                        upgrade_code.status = 'expired'
                        upgrade_code.save(update_fields=['status'])
                        return False, "Code has expired"
                    
                    if upgrade_code.used_by:
                        return False, "Code already used"
            
            action_logger.info(f"UPGRADE_STATION: Checking resources: energy={self.energy} >= {config_storage.price_kw}, tbtc={self.tbtc_wallet} >= {config_storage.price_tbtc}")
            if (
                self.energy >= config_storage.price_kw
                and self.tbtc_wallet >= config_storage.price_tbtc
            ):
                action_logger.info(f"UPGRADE_STATION: Resources sufficient, proceeding with upgrade")
                config_gen = GenPowerStationConfig.objects.get(
                    station_type=next_station_type, level=1
                )
                GlobalSpendStats.objects.update(
                    energy_spent_build=F("energy_spent_build")
                    + config_storage.price_kw,
                    energy_spent_upgrade=F("energy_spent_upgrade")
                    + config_storage.price_kw,
                    tbtc_spent_build=F("tbtc_spent_build")
                    + config_storage.price_tbtc,
                    tbtc_spent_upgrade=F("tbtc_spent_upgrade")
                    + config_storage.price_tbtc
                )

                # If this is a type transition with code or SOL payment - mark as used
                if requires_code:
                    if sol_payment_signature and station_upgrade_payment:
                        # Mark SOL payment as used
                        station_upgrade_payment.used = True
                        station_upgrade_payment.used_at = timezone.now()
                        station_upgrade_payment.save(update_fields=['used', 'used_at'])
                    elif upgrade_code:
                        # Mark code as used (existing logic)
                        upgrade_code.status = 'used'
                        upgrade_code.used_by = self
                        upgrade_code.used_at = timezone.now()
                        upgrade_code.save(update_fields=['status', 'used_by', 'used_at'])

                print(config_storage.get_duration())
                
                # Если это переход на уровень 5+, создаем UserStation и сразу применяем параметры новой станции
                if is_level_5_or_higher:
                    action_logger.info(f"UPGRADE_STATION: Level 5+ detected, creating UserStation for {next_station_type}")
                    try:
                        # Вычисляем время стройки
                        building_duration = config_storage.get_duration() * self.sbt_get_building_reduction()
                        building_until = timezone.now() + building_duration
                        action_logger.info(f"UPGRADE_STATION: Building duration={building_duration}, building_until={building_until}")
                        
                        # ВАЖНО: Создаем UserStation со статусом 'building' и правильным building_until
                        user_station = create_user_station(
                            self,
                            next_station_type,
                            source="upgrade",
                            upgraded_from=self.station_type,
                            building_until=building_until
                        )
                        action_logger.info(f"UPGRADE_STATION: Created UserStation id={user_station.id}, type={user_station.station_type}, status={user_station.status}")
                        
                        # ВАЖНО: Проверяем, что UserStation действительно создан
                        if not user_station or not user_station.id:
                            action_logger.error(f"UPGRADE_STATION: UserStation creation failed! user_station={user_station}")
                            return False, "Failed to create UserStation"
                    except Exception as e:
                        import traceback
                        action_logger.error(f"UPGRADE_STATION: Exception during UserStation creation: {e}")
                        action_logger.error(f"UPGRADE_STATION: Traceback: {traceback.format_exc()}")
                        return False, f"Error creating UserStation: {str(e)}"
                    
                    # ВАЖНО: Сразу применяем параметры новой станции к UserProfile
                    # Параметры используются сразу, но станция находится в стройке
                    # Уровни storage и generation начинаются с 1 для новой станции
                    # Ограничиваем storage до максимума новой станции
                    # ВАЖНО: Устанавливаем active_upgraded_station для связи с UserStation
                    # ВАЖНО: update() не может установить ForeignKey напрямую, нужно использовать id
                    action_logger.info(f"UPGRADE_STATION: Updating UserProfile with new station parameters")
                    # Конвертируем FloatField в Decimal для совместимости с DecimalField
                    from decimal import Decimal
                    storage_limit_decimal = Decimal(str(config_storage.storage_limit))
                    updated_count = UserProfile.objects.filter(user_id=self.user_id).update(
                        energy=F("energy") - config_storage.price_kw,
                        tbtc_wallet=F("tbtc_wallet") - config_storage.price_tbtc,
                        station_type=next_station_type,  # Сразу меняем тип станции
                        storage_level=1,  # Начальный уровень storage для новой станции
                        generation_level=1,  # Начальный уровень generation для новой станции
                        storage_limit=storage_limit_decimal,  # Сразу применяем storage_limit новой станции
                        storage=Case(
                            When(storage__gt=storage_limit_decimal, then=Value(storage_limit_decimal)),
                            default=F("storage"),
                            output_field=models.DecimalField(max_digits=36, decimal_places=16)
                        ),  # Ограничиваем storage до максимума новой станции
                        generation_rate=config_gen.generation_rate,  # Сразу применяем generation_rate новой станции
                        building_until=building_until,  # Время стройки новой станции
                        active_upgraded_station_id=user_station.id,  # Связываем новую станцию с профилем через id
                    )
                    action_logger.info(f"UPGRADE_STATION: Updated {updated_count} UserProfile records, set active_upgraded_station_id={user_station.id}")
                    
                    # Синхронизируем уровни в UserStation с UserProfile (начинаем с 1)
                    user_station.storage_level = 1
                    user_station.generation_level = 1
                    user_station.save(update_fields=['storage_level', 'generation_level'])
                    action_logger.info(f"UPGRADE_STATION: Saved UserStation levels")
                    
                    action_logger.info(
                        f"user {self.user_id} | created UserStation {next_station_type} (id: {user_station.id}) "
                        f"for upgrade, applied parameters immediately, building until {building_until}"
                    )
                else:
                    # Для станций 1-4 уровня обновляем напрямую (старая логика)
                    # Ограничиваем storage до максимума новой станции
                    # Конвертируем FloatField в Decimal для совместимости с DecimalField
                    from decimal import Decimal
                    storage_limit_decimal = Decimal(str(config_storage.storage_limit))
                    UserProfile.objects.filter(user_id=self.user_id).update(
                        energy=F("energy") - config_storage.price_kw,
                        tbtc_wallet=F("tbtc_wallet") - config_storage.price_tbtc,
                        station_type=next_station_type,
                        storage_level=1,
                        generation_level=1,
                        storage_limit=storage_limit_decimal,
                        storage=Case(
                            When(storage__gt=storage_limit_decimal, then=Value(storage_limit_decimal)),
                            default=F("storage"),
                            output_field=models.DecimalField(max_digits=36, decimal_places=16)
                        ),  # Ограничиваем storage до максимума новой станции
                        generation_rate=config_gen.generation_rate,
                        building_until=timezone.now()
                        + config_storage.get_duration()
                        * self.sbt_get_building_reduction(),
                    )
                    action_logger.info(
                        f"user {self.user_id} | upgraded station {self.energy} kw, {self.tbtc_wallet} tbtc"
                    )
                
                self.refresh_from_db()
                
                # ВАЖНО: Для уровня 5+ проверяем, что UserStation действительно создан
                if is_level_5_or_higher:
                    # Проверяем, что UserStation создан и связан с профилем
                    from core.models import UserStation
                    try:
                        user_station_check = UserStation.objects.filter(
                            user_id=self.user_id,
                            station_type=next_station_type,
                            source='upgrade'
                        ).order_by('-created_at').first()
                        
                        if not user_station_check:
                            action_logger.error(f"UPGRADE_STATION: UserStation not found after upgrade! user_id={self.user_id}, next_station_type={next_station_type}")
                            return False, "UserStation was not created during upgrade"
                        
                        # Проверяем, что active_upgraded_station_id установлен
                        self.refresh_from_db()
                        if self.active_upgraded_station_id != user_station_check.id:
                            action_logger.error(f"UPGRADE_STATION: active_upgraded_station_id mismatch! Expected {user_station_check.id}, got {self.active_upgraded_station_id}")
                            # Исправляем это
                            UserProfile.objects.filter(user_id=self.user_id).update(
                                active_upgraded_station_id=user_station_check.id
                            )
                            action_logger.info(f"UPGRADE_STATION: Fixed active_upgraded_station_id to {user_station_check.id}")
                        
                        action_logger.info(f"UPGRADE_STATION: Verified UserStation creation: id={user_station_check.id}, status={user_station_check.status}")
                    except Exception as e:
                        import traceback
                        action_logger.error(f"UPGRADE_STATION: Exception during UserStation verification: {e}")
                        action_logger.error(f"UPGRADE_STATION: Traceback: {traceback.format_exc()}")
                        return False, f"Error verifying UserStation: {str(e)}"
                
                StationUpgradeEvent.objects.create(
                    user=self,
                    level=f"{self.get_station_level()+1}-{self.generation_level}"
                )
                return True, None
            else:
                return False, "Not enough resources"
        return False, "Station not ready for upgrade"

    def clean_passed_dates(self):
        """Очищает прошедшие даты остановки"""
        now = timezone.now()
        updates = {}
        
        if self.stop_mining_at1 and self.stop_mining_at1 < now:
            updates['stop_mining_at1'] = None
        if self.stop_mining_at2 and self.stop_mining_at2 < now:
            updates['stop_mining_at2'] = None
        if self.stop_mining_at3 and self.stop_mining_at3 < now:
            updates['stop_mining_at3'] = None
        
        if updates:
            UserProfile.objects.filter(user_id=self.user_id).update(**updates)
            self.refresh_from_db()
    
    def generate_stop_dates(self, force=False):
        """Генерирует новые даты остановки только при необходимости"""
        active_boosts = self.get_active_boosts()
        is_manager_active = 'asic_manager' in active_boosts
        
        # НЕ генерируем даты остановки при активном ASIC Manager
        if is_manager_active:
            return False
        
        manager = Booster.objects.filter(slug="asic_manager").first()
        stop_count = max(int(manager.n1), 1) if manager and manager.n1 and manager.n1.isdigit() else 3
        now = timezone.now()
        
        # Проверяем, нужно ли генерировать новые даты
        # Используем stop_mining_window_start для проверки 24-часового окна
        # КРИТИЧНО: НЕ проверяем наличие дат - генерируем только если прошло 24 часа
        # Это предотвращает регенерацию дат, если все 3 остановки произошли в течение дня
        should_generate = force or (
            self.stop_mining_window_start is None or
            (now - self.stop_mining_window_start).total_seconds() >= 24 * 3600
        )
        
        if should_generate:
            dates = generate_random_dates(now, n=stop_count)
            UserProfile.objects.filter(user_id=self.user_id).update(
                stop_mining_window_start=now,  # Устанавливаем начало нового 24-часового окна
                # stop_mining_next больше не используется, оставляем для обратной совместимости
                stop_mining_at1=dates.pop(0) if dates else None,
                stop_mining_at2=dates.pop(0) if dates else None,
                stop_mining_at3=dates.pop(0) if dates else None,
            )
            self.refresh_from_db()
            return True
        
        return False

    def upd_stopper(self):
        """
        Обновляет даты остановки майнинга.
        НЕ генерирует даты при активном ASIC Manager.
        Использует 24-часовое окно для контроля генерации дат.
        """
        active_boosts = self.get_active_boosts()
        is_manager_active = 'asic_manager' in active_boosts
        
        now = timezone.now()
        
        # НЕ генерируем даты остановки при активном ASIC Manager
        if is_manager_active:
            # Только очищаем прошедшие даты, но не генерируем новые
            self.clean_passed_dates()
            return
        
        # Если менеджер НЕ активен - очищаем прошедшие даты и генерируем новые (если нужно)
        self.clean_passed_dates()
        self.generate_stop_dates()

    def add_tbtc_mining(self):
        # Инициализируем переменные в начале метода, чтобы они были доступны в блоке except
        # Это предотвращает UnboundLocalError при логировании ошибки
        mined = 0
        mined_tokens_balance_s21 = 0
        mined_tokens_balance_sx = 0
        rent_mined_tokens_balance = 0
        
        try:
            if self.last_tbtc_added is None:
                self.last_tbtc_added = self.started_mining_at

            total_mining_speed = (
                self.total_mining_speed - self.rent_total_mining_speed_minus
            )

            now = timezone.now()
            active_rentals = NFTRentalAgreement.objects.filter(
                end_date__gte=now, renter=self
            )
            # rent_mined_tokens_balance уже инициализирован в начале метода
            # print('total', total_mining_speed)
            for rental in active_rentals:
                if rental.last_collected is None:
                    rental.last_collected = now
                mining_speed = (
                    rental.mining_speed_tbtc
                    or NFTDatabase.objects.filter(nft=rental.nft)
                    .first()
                    .mining_speed_tbtc
                )
                # print(mining_speed)
                total_mined = mining_speed * min(
                    (now - rental.last_collected).total_seconds() / 3600, 1
                )
                add_rental_commission(total_mined * 0.05)
                total_mined = total_mined * 0.95
                rent_mined_tokens_balance += (
                    total_mined * (100 - rental.owner_percentage) / 100
                )
                owner_mined = total_mined * rental.owner_percentage / 100
                NFTRentalAgreement.objects.filter(id=rental.id).update(
                    last_collected=now,
                    total_collected_owner=F("total_collected_owner") + owner_mined,
                    total_collected_renter=F("total_collected_renter")
                    + rent_mined_tokens_balance,
                )
                UserProfile.objects.filter(user_id=rental.owner.user_id).update(
                    rent_mined_tokens_balance=F("rent_mined_tokens_balance")
                    + owner_mined,
                )
                add_chart_tbtc(owner_mined)

            # МИГРАЦИЯ NFT → SOLANA ASSETS: TON NFT отключены, используем только Solana Assets
            # Переменные уже инициализированы в начале метода
            
            # Получаем все активные Solana assets пользователя
            solana_assets = UserAsset.objects.filter(user=self, status='success')
            
            for asset in solana_assets:
                asset_name = asset.asset_name
                mining_speed = 0
                
                # Получаем скорость майнинга из метаданных или из таблицы asics_data
                if asset.metadata and isinstance(asset.metadata, dict):
                    mining_speed = asset.metadata.get("mining_speed_tbtc", 0)
                
                # Если в метаданных нет, ищем в asics_data
                if mining_speed == 0 and asset_name in asics_data:
                    asic_info = asics_data[asset_name]
                    mining_speed = asic_info.get("mining_speed_tbtc", 0)
                
                # Обработка специальных ASIC (S21 и SX)
                if asset_name == "Asic S21 XP+":
                    mined_tokens_balance_s21 += mining_speed * min(
                        (timezone.now() - self.last_tbtc_added).total_seconds() / 3600, 1
                    )
                    continue
                
                if asset_name == "Asic SX Ultra Pro":
                    mined_tokens_balance_sx += mining_speed * min(
                        (timezone.now() - self.last_tbtc_added).total_seconds() / 3600, 1
                    )
                    continue
                
                # Обычные ASIC
                if mining_speed > 0:
                    mined += min((timezone.now() - self.last_tbtc_added).total_seconds() / 3600, 1) * mining_speed

            # mined -= mined_tokens_balance_s21 + mined_tokens_balance_sx
            if mined < 0:
                mined = 0

            self.last_tbtc_added = timezone.now()
            UserProfile.objects.filter(user_id=self.user_id).update(
                mined_tokens_balance=F("mined_tokens_balance")
                + mined
                + rent_mined_tokens_balance,
                last_tbtc_added=self.last_tbtc_added,
                mined_tokens_balance_s21=F("mined_tokens_balance_s21")
                + mined_tokens_balance_s21,
                mined_tokens_balance_sx=F("mined_tokens_balance_sx")
                + mined_tokens_balance_sx,
            )
            add_chart_tbtc(mined + rent_mined_tokens_balance)
            
            MiningStats.objects.update(
                total_tbtc_mined=F("total_tbtc_mined")
                + mined
                + rent_mined_tokens_balance
            )
            WalletInfo.objects.filter(user=self, wallet=self.ton_wallet).update(
                tbtc_amount=F("tbtc_amount") + mined + rent_mined_tokens_balance,
                tbtc_amount_s21=F("tbtc_amount_s21") + mined_tokens_balance_s21,
                tbtc_amount_sx=F("tbtc_amount_sx") + mined_tokens_balance_sx
            )

            try:
                if self.referrer:
                    UserProfile.objects.filter(user_id=self.referrer.user_id).update(
                        bonus_tbtc_level_1=F("bonus_tbtc_level_1") + (mined + mined_tokens_balance_s21 + mined_tokens_balance_sx) * 0.06
                    )

                    UserProfile.objects.filter(user_id=self.user_id).update(
                        bring_bonus_tbtc_level_1=F("bring_bonus_tbtc_level_1")
                        + (mined + mined_tokens_balance_s21 + mined_tokens_balance_sx) * 0.06
                    )

                    if self.referrer_level_2:
                        UserProfile.objects.filter(
                            user_id=self.referrer_level_2.user_id
                        ).update(
                            bonus_tbtc_level_2=F("bonus_tbtc_level_2") + (mined + mined_tokens_balance_s21 + mined_tokens_balance_sx) * 0.03
                        )

                        UserProfile.objects.filter(
                            user_id=self.referrer.user_id
                        ).update(
                            bring_bonus_tbtc_level_2=F("bring_bonus_tbtc_level_2")
                            + (mined + mined_tokens_balance_s21 + mined_tokens_balance_sx) * 0.03
                        )
            except Exception as e:
                print("err", e)
            self.refresh_from_db()
            logging.info(f"{datetime.now()} | MINED {self.user_id}: {mined}")
        except Exception:
            # Переменные уже инициализированы в начале метода, поэтому можем безопасно их использовать
            logging.exception(f"{datetime.now()} | NOT ADDED {self.user_id}: {mined}")

    def stop_mining(self, reason=""):
        if self.is_mining:
            action_logger.info(
                f"{datetime.now()} | STOPPED MINING {self.user_id} - {reason}"
            )
            logging.info(f"{datetime.now()} | STOPPED MINING {self.user_id} - {reason}")
            UserProfile.objects.filter(user_id=self.user_id).update(
                is_mining=False, battery_balance=0
            )
            self.refresh_from_db()
            try:
                self.add_tbtc_mining()
            except Exception:
                action_logger.exception("error mining")

    def calc_storage_limit(self):
        if self.has_orbital_station:
            return 2320
        if self.has_hydro_station:
            return 1000
        return StoragePowerStationConfig.objects.filter(
            station_type=self.station_type,
            level=self.storage_level,
        ).first().storage_limit

    def calc_generation_rate(self):
        # Если активна премиальная станция, используем её generation_rate напрямую
        if self.premium_station_type:
            # Возвращаем сохраненное значение generation_rate (установлено при покупке)
            return self.generation_rate
        if self.has_orbital_station:
            if self.orbital_first_owner:
                if self.orbital_is_blue:
                    return 580
                else:
                    return 290
            else:
                return 580
        if self.has_hydro_station:
            return 278
        return GenPowerStationConfig.objects.filter(
            station_type=self.station_type,
            level=self.generation_level,
        ).first().generation_rate

    def calc_kw_per_tap(self):
        return EngineerConfig.objects.get(level=self.engineer_level).tap_power

    def check_storage_generation(self):
        UserProfile.objects.filter(user_id=self.user_id).update(
            storage_limit=self.calc_storage_limit(),
            generation_rate=self.calc_generation_rate(),
            kw_per_tap=EngineerConfig.objects.get(
                level=self.engineer_level
            ).tap_power
        )

    def get_next_station_type(self):
        # ВАЖНО: Используем тот же список, что и в upgrade_station для консистентности
        station_types = [
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
        try:
            current_index = station_types.index(self.station_type)
            if current_index < len(station_types) - 1:
                next_type = station_types[current_index + 1]
                action_logger.info(f"GET_NEXT_STATION_TYPE: current='{self.station_type}', next='{next_type}', index={current_index}")
                return next_type
        except ValueError:
            action_logger.error(f"GET_NEXT_STATION_TYPE: station_type '{self.station_type}' not found in station_types list!")
            action_logger.error(f"GET_NEXT_STATION_TYPE: station_types={station_types}")
        return None

    def get_station_level(self):
        """Возвращает уровень станции (1-10)"""
        station_types = [
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
        try:
            return station_types.index(self.station_type) + 1
        except ValueError:
            return 0

    def __str__(self):
        name = self.first_name or ""
        short_name = (name[:20] + "...") if len(name) > 20 else name
        return f"User {self.user_id} {short_name}"


class UserProfileWheelProxy(UserProfile):
    class Meta:
        proxy = True
        verbose_name = "User profile wheel stat"
        verbose_name_plural = "User profiles wheel stats"


from django.db import models


class GenPowerStationConfig(models.Model):
    station_type = models.CharField(max_length=50)  # Тип станції
    level = models.PositiveSmallIntegerField()  # Рівень (1, 2 або 3)
    price_kw = models.FloatField()  # Ціна в kW
    price_tbtc = models.FloatField()  # Ціна в tBTC
    generation_rate = models.FloatField()  # Генерація kW/год
    duration = models.DurationField(default=None, null=True, blank=True)

    order_number = models.FloatField()

    class Meta:
        ordering = ["order_number"]

    def get_duration(self):
        return self.duration or timedelta()

    def __str__(self):
        return f"{self.station_type} - Level {self.level}"


class StoragePowerStationConfig(models.Model):
    station_type = models.CharField(max_length=50)  # Тип станції
    level = models.PositiveSmallIntegerField()  # Рівень (1, 2 або 3)
    price_kw = models.FloatField()  # Ціна в kW
    price_tbtc = models.FloatField()  # Ціна в tBTC
    storage_limit = models.FloatField()
    duration = models.DurationField(default=None, null=True, blank=True)
    min_ton_price = models.FloatField(default=0)  # Мінімальна ціна в TON
    max_ton_price = models.FloatField(default=0)
    requires_code = models.BooleanField(
        default=False,
        verbose_name="Requires code",
        help_text="Whether a code is required to upgrade to this station type (applies only to level=1)"
    )
    code_bypass_price_sol = models.DecimalField(
        max_digits=20,
        decimal_places=9,
        null=True,
        blank=True,
        default=None,
        verbose_name="Code bypass price in SOL",
        help_text="Price in SOL to bypass code requirement when upgrading to this station type. Applies only to level=1."
    )

    order_number = models.FloatField()

    class Meta:
        ordering = ["order_number"]

    def get_duration(self):
        return self.duration or timedelta()

    def __str__(self):
        return f"{self.station_type} - Level {self.level}"


class RepairPowerStationConfig(models.Model):
    station_type = models.CharField(max_length=50)  # Тип станції
    price_kw = models.FloatField()  # Ціна в kW
    price_tbtc = models.FloatField()  # Ціна в tBTC

    def __str__(self):
        return f"{self.station_type}"


class WithdrawalRequest(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    wallet_address = models.CharField(max_length=255)
    token_amount = models.DecimalField(max_digits=20, decimal_places=8)
    token_contract_address = models.CharField(max_length=255)
    claimed_at = models.DateTimeField(default=timezone.now)
    processed = models.BooleanField(default=False)

    energy = models.FloatField(default=0)  # Енергія в кіловатах
    tbtc_left = models.FloatField(default=0)
    tbtc_claimed_period = models.FloatField(default=0)
    station_type = models.CharField(max_length=255, default="Boiler house")
    generation_level = models.PositiveIntegerField(default=1)
    storage_level = models.PositiveIntegerField(default=1)
    generation_rate = models.DecimalField(max_digits=36, decimal_places=16, default=5)
    note = models.CharField(max_length=255, default="withdraw")
    commision_percent = models.FloatField(default=0)
    total_mining_speed = models.FloatField(default=0, null=True, blank=True)  # Total mining speed для sBTC на момент запроса

    is_auto = models.BooleanField(default=False)

    def __str__(self):
        return (
            f"WithdrawalRequest(user={self.user.user_id}, amount={self.token_amount})"
        )


class AutoWithdrawalRequest(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.DO_NOTHING)
    wallet_address = models.CharField(max_length=255, default="")
    comment = models.CharField(max_length=255, default="")
    username = models.CharField(max_length=255, null=True, blank=True)
    token_amount_full = models.DecimalField(max_digits=20, decimal_places=8)
    token_amount = models.DecimalField(max_digits=20, decimal_places=8)
    token_type = models.CharField(max_length=255)
    claimed_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=255, default="wait_auto")
    tx_id = models.CharField(max_length=255, default="")

    def __str__(self):
        return (
            f"WithdrawalRequest(user={self.user.user_id}, amount={self.token_amount})"
        )


class EngineerConfig(models.Model):
    level = models.PositiveSmallIntegerField()  # Рівень інженера
    tap_power = models.FloatField()  # Сила тапа, kW
    hire_cost = models.FloatField()  # Вартість найму, kW
    hire_cost_stars = models.IntegerField(default=0)  # Вартість найму, Stars
    hire_cost_fbtc = models.FloatField(default=0)  # Вартість найму, fBTC

    def __str__(self):
        return f"Engineer Level {self.level}"


class BufferTransaction(models.Model):
    tx_hash = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    success = models.BooleanField(default=False)


class AsicsCoefs(models.Model):
    address = models.CharField(max_length=255)
    coef = models.FloatField(default=1)


class OverheatConfig(models.Model):
    min_duration = models.PositiveIntegerField(default=15)  # in minutes
    max_duration = models.PositiveIntegerField(default=300)
    taps_before_power_reduction = models.PositiveIntegerField(default=5)  # New field
    power_reduction_percentage = models.FloatField(default=1.0)  # New field

    def __str__(self):
        return f"OverheatConfig({self.min_duration}-{self.max_duration} mins)"


class WithdrawalConfig(models.Model):
    min_kw = models.FloatField(default=500)
    min_tbtc = models.FloatField(default=50)
    min_claim = models.FloatField(default=0)
    max_auto_kw = models.FloatField(default=10000)
    max_auto_tbtc = models.FloatField(default=500)
    max_auto_claim = models.FloatField(default=500)

    wheel_kw_cost = models.FloatField(default=1500)
    wheel_tbtc_cost = models.FloatField(default=100)
    wheel_stars_cost = models.FloatField(default=100)

    min_staking = models.FloatField(default=1000)
    min_staking_out = models.FloatField(default=10)
    max_auto_staking_out = models.FloatField(default=0)

    tap_power = models.FloatField(default=0.5)

    gradation_minutes = models.IntegerField(default=10)
    gradation_value = models.IntegerField(default=1)
    gradation_value_tbtc = models.FloatField(default=0.1)  # Ціна в tBTC за gradation_minutes
    engineer_minus = models.IntegerField(default=1)

    min_rent = models.FloatField(default=10)
    max_auto_rent = models.FloatField(default=1000)


class KwCommissions(models.Model):
    date = models.DateField()
    amount = models.FloatField()

    class Meta:
        ordering = ["-date"]


class WheelStats(models.Model):
    date = models.DateField()
    amount_kw = models.FloatField()
    amount_tbtc = models.FloatField()
    amount_stars = models.FloatField()
    amount_nft = models.FloatField()

    class Meta:
        ordering = ["-date"]


def add_wheel_stat(reward: UserReward):
    today = timezone.now().date()
    data = {
        "kw": reward.asset_quantity if reward.asset_type == "kW" else 0,
        "tbtc": reward.asset_quantity if reward.asset_type == "tBTC" else 0,
        "stars": reward.asset_quantity if reward.asset_type == "Stars" else 0,
        "nft": 1 if reward.asset_type == "ASIC" else 0,
    }
    with transaction.atomic():
        if WheelStats.objects.filter(date=today).first():
            WheelStats.objects.filter(date=today).update(
                amount_kw=F("amount_kw") + data["kw"],
                amount_tbtc=F("amount_tbtc") + data["tbtc"],
                amount_stars=F("amount_stars") + data["stars"],
                amount_nft=F("amount_nft") + data["nft"],
            )
        else:
            WheelStats.objects.create(
                date=today,
                amount_kw=data["kw"],
                amount_tbtc=data["tbtc"],
                amount_stars=data["stars"],
                amount_nft=data["nft"],
            )


from django.db import transaction


def add_kw_commission(amount: float):
    today = timezone.now().date()
    with transaction.atomic():
        if KwCommissions.objects.filter(date=today).first():
            KwCommissions.objects.filter(date=today).update(amount=F("amount") + amount)
        else:
            KwCommissions.objects.create(date=today, amount=amount)


class TbtcCommissions(models.Model):
    date = models.DateField()
    amount = models.FloatField()

    class Meta:
        ordering = ["-date"]


def add_tbtc_commission(amount: float):
    today = timezone.now().date()
    with transaction.atomic():
        if TbtcCommissions.objects.filter(date=today).first():
            TbtcCommissions.objects.filter(date=today).update(
                amount=F("amount") + amount
            )
        else:
            TbtcCommissions.objects.create(date=today, amount=amount)


class MiningCommissions(models.Model):
    date = models.DateField()
    amount = models.FloatField()

    class Meta:
        ordering = ["-date"]


def add_mining_commission(amount: float):
    today = timezone.now().date()
    with transaction.atomic():
        if MiningCommissions.objects.filter(date=today).first():
            MiningCommissions.objects.filter(date=today).update(
                amount=F("amount") + amount
            )
        else:
            MiningCommissions.objects.create(date=today, amount=amount)


class RentalCommissions(models.Model):
    date = models.DateField()
    amount = models.FloatField()

    class Meta:
        ordering = ["-date"]


def add_rental_commission(amount: float):
    today = timezone.now().date()
    with transaction.atomic():
        if RentalCommissions.objects.filter(date=today).first():
            RentalCommissions.objects.filter(date=today).update(
                amount=F("amount") + amount
            )
        else:
            RentalCommissions.objects.create(date=today, amount=amount)


class StakingPeriodConfig(models.Model):
    days = models.PositiveIntegerField()
    apr = models.FloatField()

    def __str__(self):
        return f"{self.days} days - {self.apr}% APR"


class UserStaking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("wait_deposit", "Wait deposit"),
        ("finished", "Finished"),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    token_amount = models.FloatField(null=True, blank=True)
    reward = models.FloatField(null=True, blank=True)
    collected = models.FloatField(default=0)
    last_collected = models.DateTimeField(null=True, blank=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    days = models.PositiveIntegerField()
    apr = models.FloatField()

    wallet_address = models.CharField(max_length=255, default="")
    tx_id = models.CharField(max_length=255, default="")
    confirmed = models.BooleanField(default=False)

    status = models.CharField(max_length=255, default="pending")


class HashrateInfo(models.Model):
    hashrate = models.FloatField(default=0)


class BoosterRefund(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    booster = models.ForeignKey(Booster, on_delete=models.CASCADE)
    days_left = models.PositiveIntegerField()
    old_price = models.FloatField()
    new_price = models.FloatField()
    total_amount = models.FloatField()
    processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class MintRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("finished", "Finished"),
    ]
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    wallet = models.CharField(max_length=255)
    nft_required = models.CharField(max_length=255)
    nft_sent_1 = models.CharField(max_length=255, null=True, blank=True)
    nft_sent_2 = models.CharField(max_length=255, null=True, blank=True)
    kw_spent = models.FloatField()
    tbtc_spent = models.FloatField()
    status = models.CharField(max_length=50, default="pending", choices=STATUS_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"MintRequest(user={self.user.user_id}, status={self.status})"


class NFTStation(models.Model):
    station_type = models.CharField(max_length=50)
    level = models.PositiveSmallIntegerField()
    construction_time = models.DurationField()
    active_image = models.ImageField(upload_to="stations/active/")
    construction_image = models.ImageField(upload_to="stations/construction/")

    def __str__(self):
        return f"{self.station_type} - Level {self.level}"


class UserActionLog(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    action = models.CharField(max_length=255)
    details = models.TextField()
    status = models.CharField(max_length=50, default="success")
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"UserActionLog(user={self.user.user_id}, action={self.action})"


class StationRollbackLog(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    from_station = models.CharField(max_length=50)
    generation_level = models.PositiveSmallIntegerField(null=True, blank=True)
    storage_level = models.PositiveSmallIntegerField(null=True, blank=True)
    engineer_level = models.PositiveSmallIntegerField(null=True, blank=True)
    energy = models.FloatField(null=True, blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"StationRollbackLog(user={self.user.user_id}, from_station={self.from_station})"


class NFTRentalConfig(models.Model):
    min_days = models.PositiveIntegerField(default=7)
    max_days = models.PositiveIntegerField(default=60)
    min_percentage = models.PositiveIntegerField(default=30)
    max_percentage = models.PositiveIntegerField(default=70)

    max_points_block = models.IntegerField(default=3)
    platform_fee = models.PositiveIntegerField(default=5)

    def __str__(self):
        return f"Rental Config ({self.min_days}-{self.max_days} days, {self.min_percentage}-{self.max_percentage}%)"


class NFTDatabase(models.Model):
    nft = models.CharField(max_length=255)
    wallet = models.CharField(max_length=255, blank=True, null=True)
    hashrate = models.FloatField(default=0)
    collection = models.CharField(max_length=255, verbose_name="NFT Collection", default="")
    name = models.CharField(max_length=255, blank=True, null=True)
    mining_speed_tbtc = models.FloatField(default=0)
    consumption_kw = models.FloatField(default=0)


class NFTRentalAgreement(models.Model):
    nft = models.CharField(max_length=255)
    hashrate = models.FloatField(null=True, blank=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    owner = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="rented_nfts"
    )
    renter = models.ForeignKey(
        UserProfile,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="rented_from",
    )

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    last_collected = models.DateTimeField(null=True, blank=True)
    total_collected_renter = models.FloatField(default=0)
    total_collected_owner = models.FloatField(default=0)
    mining_speed_tbtc = models.FloatField(default=0)

    rentals_days = models.PositiveIntegerField()
    owner_percentage = models.PositiveIntegerField()
    platform_fee = models.PositiveIntegerField(default=5)

    def stop_rent(self):
        NFTRentalAgreement.objects.filter(id=self.id).update(
            start_date=None,
            end_date=None,
            renter=None,
            total_collected_owner=0,
            total_collected_renter=0,
            mining_speed_tbtc=0,
        )


# class ActiveRentalRecord(models.Model):
#     nft = models.CharField(max_length=255)
#     owner = models.ForeignKey(
#         UserProfile, on_delete=models.CASCADE, related_name="rented_nfts"
#     )
#     renter = models.ForeignKey(
#         UserProfile,
#         on_delete=models.CASCADE,
#         null=True,
#         blank=True,
#         related_name="rented_from",
#     )
#     rentals_days = models.PositiveIntegerField()
#     start_date = models.DateTimeField(null=True, blank=True)
#     end_date = models.DateTimeField(null=True, blank=True)
#     owner_percentage = models.PositiveIntegerField()
#     platform_fee = models.PositiveIntegerField(default=5)


class StationNFTOwner(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    wallet = models.CharField(max_length=255)
    nft = models.CharField(max_length=255, null=True, blank=True)


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("nft_not_found", "Nft Not Found"),
    ]

    user = models.ForeignKey(
        UserProfile, on_delete=models.CASCADE, related_name="notifications"
    )
    notif_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class ChartData(models.Model):
    CHART_TYPE_CHOICES = [
        ("station_power", "Station Power"),
        ("network_hashrate", "Network Hashrate"),
        ("active_stations", "Active Stations"),
        ("active_asics", "Active ASICs"),
        ("kw_price", "kW Price"),
        ("tbtc_price", "tBTC Price"),
        ("kw_mined", "kW Mined"),
        ("tbtc_mined", "tBTC Mined"),
        ("kw_per_tbtc", "kW per tBTC"),
        ("energy_burned", "Energy Burned"),
        ("tbtc_remaining", "tBTC Remaining"),
        ("tbtc_staked", "tBTC Staked"),
    ]

    chart_type = models.CharField(
        max_length=50, choices=CHART_TYPE_CHOICES, verbose_name="Тип графика"
    )
    date = models.DateField(verbose_name="Дата")
    value = models.FloatField(verbose_name="Значение")

    class Meta:
        ordering = ["chart_type", "date"]

    def __str__(self):
        return f"{self.chart_type} - {self.date}: {self.value}"


class GlobalStats(models.Model):
    total_energy = models.FloatField(default=0)
    total_kw = models.FloatField(default=0)
    total_tbtc = models.FloatField(default=0)
    total_unclaimed_tbtc = models.FloatField(default=0)
    total_ref_kw = models.FloatField(default=0)
    total_ref_tbtc_mining = models.FloatField(default=0)
    total_ref_tbtc_staking = models.FloatField(default=0)
    total_mining_speed = models.FloatField(default=0)
    actual_mining_speed = models.FloatField(default=0)
    connected_asics = models.PositiveIntegerField(default=0)
    mining_asics = models.PositiveIntegerField(default=0)
    setup_asics = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Глобальна статистика"
        verbose_name_plural = "Глобальна статистика"

    def __str__(self):
        return f"Глобальна статистика"


class GlobalSpendStats(models.Model):
    total_energy_accumulated = models.FloatField(
        default=0, verbose_name="Загальна накопичена Енергія"
    )
    energy_spent_build = models.FloatField(
        default=0, verbose_name="Витрачено Енергії на будівництво"
    )
    energy_spent_upgrade = models.FloatField(
        default=0, verbose_name="Витрачено Енергії на апгрейди"
    )
    energy_spent_engineer = models.FloatField(
        default=0, verbose_name="Витрачено Енергії на інженерів"
    )
    energy_spent_repair = models.FloatField(
        default=0, verbose_name="Витрачено Енергії на ремонти"
    )
    tbtc_spent_build = models.FloatField(
        default=0, verbose_name="Витрачено tBTC на будівництво"
    )
    tbtc_spent_upgrade = models.FloatField(
        default=0, verbose_name="Витрачено tBTC на апгрейди"
    )
    tbtc_spent_repair = models.FloatField(
        default=0, verbose_name="Витрачено tBTC на ремонти"
    )

    class Meta:
        verbose_name = "Глобальна статистика витрат"
        verbose_name_plural = "Глобальна статистика витрат"

    def __str__(self):
        return f"Витрати"


class DailyStat(models.Model):
    STAT_TYPE_CHOICES = [
        ("kw_deposit", "Поповнення kW"),
        ("tbtc_deposit", "Поповнення tBTC"),
        ("ref_kw_accrued", "Нараховано kW від рефералів"),
        ("ref_tbtc_mining_accrued", "Нараховано tBTC від рефералів (майнінг)"),
        ("ref_tbtc_staking_accrued", "Нараховано tBTC від рефералів (стейкінг)"),
        ("ref_kw_claimed", "Заклеймлено kW від рефералів"),
        ("ref_tbtc_mining_claimed", "Заклеймлено tBTC від рефералів (майнінг)"),
        ("ref_tbtc_staking_claimed", "Заклеймлено tBTC від рефералів (стейкінг)"),
    ]

    date = models.DateTimeField(verbose_name="Дата", db_index=True)
    stat_type = models.CharField(
        max_length=50, choices=STAT_TYPE_CHOICES, verbose_name="Тип"
    )
    value = models.FloatField(default=0, verbose_name="Значення")

    class Meta:
        verbose_name = "Статистика поповнення"
        verbose_name_plural = "Статистика поповнення"
        ordering = ["-date", "stat_type"]

    def __str__(self):
        return f"Statistic for {self.date} - {self.stat_type}: {self.value}"


class MiningStats(models.Model):
    total_tbtc_mined = models.FloatField(
        default=0, verbose_name="Загальна кількість добутого tBTC"
    )
    total_tbtc_claimed = models.FloatField(
        default=0, verbose_name="Загальна кількість заклеймленого tBTC"
    )
    energy_spent_mining = models.FloatField(
        default=0, verbose_name="Витрачено Енергії на майнінг"
    )
    energy_saved_powerbank = models.FloatField(
        default=0, verbose_name="Зекономлено Енергії на майнінг (PowerBank)"
    )
    energy_saved_magnet = models.FloatField(
        default=0, verbose_name="Зекономлено Енергії на майнінг (Магніт)"
    )

    class Meta:
        verbose_name = "Глобальна статистика майнінгу"
        verbose_name_plural = "Глобальна статистика майнінгу"

    def __str__(self):
        return "Глобальна статистика майнінгу"


class JarvisEnergyStat(models.Model):
    date = models.DateField(verbose_name="Дата", db_index=True)
    total_jarvis_energy = models.FloatField(
        default=0, verbose_name="Загальна натапана Енергія Джарвісом"
    )
    jarvis_level_1 = models.FloatField(default=0, verbose_name="Джарвіс рівня 1")
    jarvis_level_2 = models.FloatField(default=0, verbose_name="Джарвіс рівня 2")
    jarvis_level_3 = models.FloatField(default=0, verbose_name="Джарвіс рівня 3")
    jarvis_level_4 = models.FloatField(default=0, verbose_name="Джарвіс рівня 4")
    jarvis_level_5 = models.FloatField(default=0, verbose_name="Джарвіс рівня 5")

    class Meta:
        verbose_name = "Енергія Джарвіса за день"
        verbose_name_plural = "Енергія Джарвіса за день"
        ordering = ["-date"]

    def __str__(self):
        return f"Енергія Джарвіса"


class StationUpgradeEvent(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    level = models.CharField(max_length=50, verbose_name="Рівень станції")
    upgrade_date = models.DateTimeField(auto_now_add=True, verbose_name="Дата апгрейду")

    class Meta:
        verbose_name = "Подія апгрейду станції"
        verbose_name_plural = "Події апгрейду станцій"

    def __str__(self):
        return f"Подія апгрейду станції {self.level} для користувача {self.user.user_id}"

class StationLevelStat(models.Model):
    count_10_3 = models.PositiveIntegerField(default=0, verbose_name="10-3")
    count_10_2 = models.PositiveIntegerField(default=0, verbose_name="10-2")
    count_10_1 = models.PositiveIntegerField(default=0, verbose_name="10-1")
    count_9_3 = models.PositiveIntegerField(default=0, verbose_name="9-3")
    count_9_2 = models.PositiveIntegerField(default=0, verbose_name="9-2")
    count_9_1 = models.PositiveIntegerField(default=0, verbose_name="9-1")
    count_8_3 = models.PositiveIntegerField(default=0, verbose_name="8-3")
    count_8_2 = models.PositiveIntegerField(default=0, verbose_name="8-2")
    count_8_1 = models.PositiveIntegerField(default=0, verbose_name="8-1")
    count_7_3 = models.PositiveIntegerField(default=0, verbose_name="7-3")
    count_7_2 = models.PositiveIntegerField(default=0, verbose_name="7-2")
    count_7_1 = models.PositiveIntegerField(default=0, verbose_name="7-1")
    count_6_3 = models.PositiveIntegerField(default=0, verbose_name="6-3")
    count_6_2 = models.PositiveIntegerField(default=0, verbose_name="6-2")
    count_6_1 = models.PositiveIntegerField(default=0, verbose_name="6-1")
    count_5_3 = models.PositiveIntegerField(default=0, verbose_name="5-3")
    count_5_2 = models.PositiveIntegerField(default=0, verbose_name="5-2")
    count_5_1 = models.PositiveIntegerField(default=0, verbose_name="5-1")
    count_4_3 = models.PositiveIntegerField(default=0, verbose_name="4-3")
    count_4_2 = models.PositiveIntegerField(default=0, verbose_name="4-2")
    count_4_1 = models.PositiveIntegerField(default=0, verbose_name="4-1")
    count_3_3 = models.PositiveIntegerField(default=0, verbose_name="3-3")
    count_3_2 = models.PositiveIntegerField(default=0, verbose_name="3-2")
    count_3_1 = models.PositiveIntegerField(default=0, verbose_name="3-1")
    count_2_3 = models.PositiveIntegerField(default=0, verbose_name="2-3")
    count_2_2 = models.PositiveIntegerField(default=0, verbose_name="2-2")
    count_2_1 = models.PositiveIntegerField(default=0, verbose_name="2-1")
    count_1_3 = models.PositiveIntegerField(default=0, verbose_name="1-3")
    count_1_2 = models.PositiveIntegerField(default=0, verbose_name="1-2")
    count_1_1 = models.PositiveIntegerField(default=0, verbose_name="1-1")

    class Meta:
        verbose_name = "Статистика станцій за рівнями"
        verbose_name_plural = "Статистика станцій за рівнями"

    def __str__(self):
        return f"Статистика станцій"


class SpecialAsicStaking(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("finished", "Finished"),
    ]

    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    token_amount = models.FloatField(null=True, blank=True)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    days = models.PositiveIntegerField()
    apr = models.FloatField()

    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default="pending")

    # class Meta:
    #     verbose_name = "Спеціальний стейкінг S21/SX"
    #     verbose_name_plural = "Спеціальні стейкінги S21/SX"


class BurnedTBTCBase(models.Model):
    wallet = models.CharField(max_length=255, verbose_name="Wallet Address")
    amount = models.FloatField(verbose_name="Amount")
    upload_date = models.DateTimeField(auto_now_add=True, verbose_name="Upload Date")

    class Meta:
        verbose_name = "Burned tBTC Base Record"
        verbose_name_plural = "Burned tBTC Base"
        ordering = ["-upload_date"]

    def __str__(self):
        return f"{self.wallet} - {self.amount} tBTC"

class UserBurnedTBTC(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True)
    wallet = models.CharField(max_length=255, verbose_name="Wallet Address")
    amount = models.FloatField(verbose_name="Total Amount")
    apr = models.FloatField(verbose_name="APR %", default=24)
    
    unlock_date_1 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 1")
    unlock_date_2 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 2")
    unlock_date_3 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 3")
    unlock_date_4 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 4")
    unlock_date_5 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 5")
    unlock_date_6 = models.DateField(null=True, blank=True, verbose_name="Unlock Date 6")

class LinkedUserNFT(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True)
    wallet = models.CharField(max_length=255, verbose_name="Wallet Address")
    nft_address = models.CharField(max_length=255, verbose_name="NFT Address")
    

class TimedUserNFT(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True)
    wallet = models.CharField(max_length=255, verbose_name="Wallet Address")
    name = models.CharField(max_length=255, verbose_name="NFT Name")
    collection = models.CharField(max_length=255, verbose_name="NFT Collection")
    nft_address = models.CharField(max_length=255, verbose_name="NFT Address")
    block_until = models.DateTimeField(verbose_name="Block Until", null=True, blank=True)


class OrbitalOwner(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True)
    nft_address = models.CharField(max_length=255, verbose_name="NFT Address")


class GradationConfig(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name")
    gradation_minutes = models.IntegerField(default=10)
    gradation_value_tbtc = models.FloatField(default=0.1)  # Ціна в tBTC за gradation_minutes
    gradation_value = models.IntegerField(default=1)
    
class WalletInfo(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True)
    wallet = models.CharField(max_length=255, verbose_name="Wallet Address")
    kw_amount = models.FloatField(default=0)
    tbtc_amount = models.FloatField(default=0)
    tbtc_amount_s21 = models.FloatField(default=0)
    tbtc_amount_sx = models.FloatField(default=0)
    block_until = models.DateTimeField(verbose_name="Block Until", null=True, blank=True)
    

class Nonce(models.Model):
    value = models.CharField(max_length=100, unique=True)
    used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    @classmethod
    def create_nonce(cls):
        import os, base58, datetime
        nonce = base58.b58encode(os.urandom(16)).decode()
        expires = timezone.now() + timedelta(minutes=2)
        return cls.objects.create(value=nonce, expires_at=expires)


# МИГРАЦИЯ NFT → SOLANA ASSETS
# Новая модель для покупки ASIC через Solana
class SolanaPayment(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='solana_payments')
    signature = models.CharField(max_length=128, unique=True, verbose_name="Transaction Signature")
    asic_name = models.CharField(max_length=128, verbose_name="Asset Name")
    asic_index = models.IntegerField(null=True, blank=True, verbose_name="ASIC Index")
    asic_price = models.DecimalField(max_digits=20, decimal_places=9, verbose_name="Price in SOL")
    asic_data = models.JSONField(null=True, blank=True, verbose_name="ASIC Metadata")
    # Премиальные станции
    station_type = models.CharField(max_length=128, null=True, blank=True, verbose_name="Station Type")
    station_price = models.DecimalField(max_digits=20, decimal_places=9, null=True, blank=True, verbose_name="Station Price in SOL")
    network = models.CharField(max_length=16, default="devnet", verbose_name="Network")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Solana Payment"
        verbose_name_plural = "Solana Payments"
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.signature[:8]}... by {self.user.username} for {self.asic_name}"


class UserAsset(models.Model):
    """Внутренний ассет пользователя (замена NFT-модели)"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='user_assets')
    asset_hash = models.CharField(max_length=128, unique=True, verbose_name="Asset Hash")
    asset_name = models.CharField(max_length=64, verbose_name="Asset Name")
    purchase_time = models.DateTimeField(auto_now_add=True, verbose_name="Purchase Time")
    status = models.CharField(max_length=16, default='success', choices=[
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], verbose_name="Status")
    
    # Связь с платежом
    payment = models.ForeignKey(SolanaPayment, on_delete=models.SET_NULL, null=True, blank=True, related_name='assets')
    
    # Метаданные для совместимости с NFT
    metadata = models.JSONField(null=True, blank=True, verbose_name="Asset Metadata")

    class Meta:
        verbose_name = "User Asset"
        verbose_name_plural = "User Assets"
        ordering = ['-purchase_time']

    def __str__(self):
        return f"{self.asset_name} ({self.asset_hash[:8]}...) - {self.user.username}"
    
    def delete(self, *args, **kwargs):
        """Пересчитываем характеристики пользователя при удалении ассета"""
        user = self.user
        asset_hash = self.asset_hash
        logging.info(f"UserAsset.delete() called for {asset_hash} by user {user.user_id}")
        super().delete(*args, **kwargs)
        
        # Удаляем hash из nft_string
        if user.nft_string:
            nft_list = user.nft_string.split(";")
            nft_list = [h for h in nft_list if h.strip() != asset_hash]
            user.nft_string = ";".join(nft_list)
        
        # Пересчитываем характеристики от всех оставшихся ассетов
        all_assets = UserAsset.objects.filter(user=user, status='success')
        total_mining_speed = 0
        total_farm_consumption = 0
        total_mining_farm_speed = 0
        
        for asset in all_assets:
            asset_nft = NFTDatabase.objects.filter(nft=asset.asset_hash).first()
            if asset_nft:
                total_mining_speed += asset_nft.mining_speed_tbtc
                total_farm_consumption += asset_nft.consumption_kw
                total_mining_farm_speed += asset_nft.hashrate / 1000  # Gh/s
        
        user.total_mining_speed = total_mining_speed
        user.total_farm_consumption = total_farm_consumption
        user.mining_farm_speed = total_mining_farm_speed
        user.save(update_fields=['nft_string', 'total_mining_speed', 'total_farm_consumption', 'mining_farm_speed'])
        logging.info(f"Recalculated user {user.user_id} stats after delete: mining_speed={total_mining_speed}, consumption={total_farm_consumption}")


class UserStation(models.Model):
    """Станция пользователя, полученная через улучшение или P2P-покупку"""
    
    SOURCE_CHOICES = [
        ('upgrade', 'Upgrade'),           # Получена через улучшение
        ('craft', 'Craft'),                # Получена через крафт (6+ уровень)
        ('p2p_purchase', 'P2P Purchase'),  # Куплена на P2P-маркете
        ('admin', 'Admin'),                # Добавлена администратором
    ]
    
    STATUS_CHOICES = [
        ('building', 'Building'),          # В процессе стройки
        ('ready', 'Ready'),                # Готова к активации
        ('active', 'Active'),              # Активна (используется)
        ('inactive', 'Inactive'),          # Неактивна (в инвентаре)
    ]
    
    user = models.ForeignKey(
        UserProfile, 
        on_delete=models.CASCADE, 
        related_name='user_stations'
    )
    
    # Основная информация о станции
    station_type = models.CharField(max_length=255, verbose_name="Station Type")
    station_hash = models.CharField(max_length=128, unique=True, verbose_name="Station Hash")
    
    # Уровни станции (на момент создания)
    storage_level = models.IntegerField(default=3, verbose_name="Storage Level")
    generation_level = models.IntegerField(default=3, verbose_name="Generation Level")
    engineer_level = models.IntegerField(default=0, verbose_name="Engineer Level")
    
    # Источник получения станции
    source = models.CharField(max_length=32, choices=SOURCE_CHOICES, default='upgrade', verbose_name="Source")
    
    # Статус станции
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default='building', verbose_name="Status")
    
    # Информация о создании/получении
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    building_until = models.DateTimeField(null=True, blank=True, verbose_name="Building Until")
    
    # Информация о крафте (для станций 6+ уровня)
    crafted_from_stations = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='crafted_into_stations',
        blank=True,
        help_text="Станции, использованные для крафта этой станции"
    )
    upgraded_from_station_type = models.CharField(
        max_length=255, 
        blank=True,
        verbose_name="Upgraded From Station Type",
        help_text="Тип станции, из которой была улучшена (для уровня 5)"
    )
    
    # Информация о P2P-покупке
    purchased_from_user = models.ForeignKey(
        UserProfile,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='sold_stations',
        verbose_name="Purchased From User",
        help_text="Пользователь, у которого была куплена станция"
    )
    purchase_price_sol = models.DecimalField(
        max_digits=20, 
        decimal_places=9, 
        null=True, 
        blank=True,
        verbose_name="Purchase Price SOL",
        help_text="Цена покупки в SOL (для P2P)"
    )
    
    # Дополнительные метаданные
    metadata = models.JSONField(
        null=True, 
        blank=True,
        verbose_name="Metadata",
        help_text="Дополнительные метаданные станции"
    )
    
    class Meta:
        verbose_name = "User Station"
        verbose_name_plural = "User Stations"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'station_type']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['status', 'building_until']),
        ]
    
    def __str__(self):
        return f"{self.station_type} ({self.user.user_id}) - {self.get_status_display()}"
    
    def is_building(self):
        """Проверяет, находится ли станция в процессе стройки"""
        if self.status != 'building':
            return False
        if self.building_until and self.building_until > timezone.now():
            return True
        return False
    
    def can_be_activated(self):
        """Проверяет, можно ли активировать станцию"""
        return self.status == 'ready' or (self.status == 'building' and not self.is_building())
    
    def can_be_sold(self):
        """Проверяет, можно ли продать станцию"""
        return self.status != 'active'  # Нельзя продать активную станцию
    
    def check_and_update_status(self):
        """Проверяет и обновляет статус станции, если стройка завершена"""
        if self.status == 'building' and not self.is_building():
            self.status = 'ready'
            self.building_until = None
            self.save(update_fields=['status', 'building_until'])
            return True
        return False


# Функции для работы со станциями

def check_and_update_user_stations_status(user_profile):
    """Проверяет и обновляет статусы всех станций пользователя, у которых закончилась стройка.
    Автоматически активирует станции после окончания стройки."""
    now = timezone.now()
    updated_stations = UserStation.objects.filter(
        user=user_profile,
        status='building',
        building_until__lte=now
    )
    
    updated_count = 0
    for station in updated_stations:
        # Если станция готова к активации - активируем её автоматически
        if station.can_be_activated():
            # Активируем станцию автоматически после окончания стройки
            success, error = activate_station_after_building(user_profile, station)
            if success:
                updated_count += 1
            else:
                # Если активация не удалась, просто меняем статус на ready
                station.status = 'ready'
                station.building_until = None
                station.save(update_fields=['status', 'building_until'])
        else:
            # Если станция не может быть активирована, просто меняем статус на ready
            station.status = 'ready'
            station.building_until = None
            station.save(update_fields=['status', 'building_until'])
            updated_count += 1
    
    return updated_count

def get_previous_station_type(station_type):
    """Возвращает тип станции, требуемый для крафта"""
    station_types = [
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
    
    try:
        index = station_types.index(station_type)
        if index > 0:
            return station_types[index - 1]
    except ValueError:
        pass
    
    return None


def generate_station_hash(user_id, station_type, source, timestamp=None):
    """Генерирует уникальный хеш станции"""
    if timestamp is None:
        timestamp = time.time()
    
    if base58:
        return base58.b58encode(
            hashlib.sha256(
                f"{user_id}_{station_type}_{timestamp}_{source}".encode()
            ).digest()
        ).decode()
    else:
        # Fallback если base58 не доступен
        return hashlib.sha256(
            f"{user_id}_{station_type}_{timestamp}_{source}".encode()
        ).hexdigest()[:64]


def create_user_station(user_profile, station_type, source="upgrade", upgraded_from=None, building_until=None):
    """Создает UserStation для станции
    
    Args:
        user_profile: Профиль пользователя
        station_type: Тип станции
        source: Источник создания ('upgrade', 'craft', 'p2p_purchase', 'admin')
        upgraded_from: Тип станции, из которой была улучшена (для upgrade)
        building_until: Время окончания стройки (если None, вычисляется автоматически)
    """
    from core.models import StoragePowerStationConfig
    
    # Генерируем уникальный хеш станции
    station_hash = generate_station_hash(user_profile.user_id, station_type, source)
    
    # Если building_until не передан, вычисляем автоматически
    if building_until is None:
        config_storage = StoragePowerStationConfig.objects.get(
            station_type=station_type, level=1
        )
        building_duration = config_storage.get_duration() * user_profile.sbt_get_building_reduction()
        building_until = timezone.now() + building_duration
    
    user_station = UserStation.objects.create(
        user=user_profile,
        station_type=station_type,
        station_hash=station_hash,
        storage_level=3,  # Максимальный уровень для новой станции
        generation_level=3,
        engineer_level=0,  # Начальный уровень инженера
        source=source,
        status='building',
        building_until=building_until,
        upgraded_from_station_type=upgraded_from or user_profile.station_type,
        metadata={
            "created_at_upgrade": timezone.now().isoformat(),
            "original_station_type": user_profile.station_type,
        }
    )
    
    return user_station


def can_craft_station(user_profile, target_station_type):
    """Проверяет возможность крафта станции"""
    from core.models import StoragePowerStationConfig
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Получаем требуемый тип станции для крафта
    required_station_type = get_previous_station_type(target_station_type)
    if not required_station_type:
        return False, "Invalid target station type"
    
    # Проверяем наличие 2 станций нужного типа
    # Включаем станции со статусом 'ready', 'inactive' и 'active' (активную можно деактивировать)
    # Исключаем только станции со статусом 'building'
    
    # Сначала получаем все станции нужного типа для логирования (включая все статусы)
    all_stations_of_type = list(UserStation.objects.filter(
        user=user_profile,
        station_type=required_station_type
    ).values('id', 'status', 'station_type'))
    
    # Получаем активную станцию пользователя для логирования
    active_station_info = None
    if user_profile.active_upgraded_station_id:
        active_station_obj = UserStation.objects.filter(id=user_profile.active_upgraded_station_id).first()
        if active_station_obj:
            active_station_info = {
                'id': active_station_obj.id,
                'station_type': active_station_obj.station_type,
                'status': active_station_obj.status
            }
    
    # Получаем станции нужного типа с подходящими статусами
    stations_query = UserStation.objects.filter(
        user=user_profile,
        station_type=required_station_type,
        status__in=['ready', 'inactive', 'active']  # Готовые, неактивные или активные станции
    )
    
    # ВАЖНО: НЕ исключаем активную станцию из подсчета для крафта
    # Пользователь может использовать активную станцию для крафта новой станции
    # Новая станция заменит активную после завершения стройки
    excluded_station_id = None
    # Логируем информацию об активной станции, но не исключаем её
    if user_profile.active_upgraded_station_id:
        active_station = UserStation.objects.filter(
            id=user_profile.active_upgraded_station_id,
            station_type=required_station_type
        ).first()
        if active_station:
            logger.info(f"Active station ID {user_profile.active_upgraded_station_id} (type: {active_station.station_type}, status: {active_station.status}) is available for craft")
    
    available_stations = stations_query
    station_count = available_stations.count()
    
    # Детальное логирование для диагностики
    available_station_ids = list(available_stations.values_list('id', flat=True))
    logger.info(f"Craft check for {target_station_type}: "
                f"required_station_type={required_station_type}, "
                f"active_station_id={user_profile.active_upgraded_station_id}, "
                f"active_station_info={active_station_info}, "
                f"all_stations_of_type={all_stations_of_type}, "
                f"excluded_station_id={excluded_station_id}, "
                f"available_station_ids={available_station_ids}, "
                f"available_count={station_count}")
    
    if station_count < 2:
        return False, f"Need 2 {required_station_type} stations (found {station_count})"
    
    # Проверяем условия улучшения текущей станции
    if user_profile.storage_level != 3 or user_profile.generation_level != 3:
        return False, "Station must be at max storage and generation levels"
    
    # Проверяем ресурсы
    config_storage = StoragePowerStationConfig.objects.get(
        station_type=target_station_type, level=1
    )
    if user_profile.energy < config_storage.price_kw or \
       user_profile.tbtc_wallet < config_storage.price_tbtc:
        return False, "Not enough resources"
    
    return True, None


def validate_craft_code(user_profile, target_station_type, code):
    """Валидирует код перед крафтом (ДО списания ресурсов)
    
    Использует ту же логику, что и ValidateUpgradeCodeView для апгрейда 2-5 уровня
    """
    # Импортируем здесь чтобы избежать циклических зависимостей
    # StationUpgradeCode и STATION_CODE_REGEX определены ниже в этом же файле
    
    # Нормализуем код
    code_normalized = StationUpgradeCode.normalize_code(code)
    if not STATION_CODE_REGEX.match(code_normalized):
        return False, "Invalid code format. Code must match <Ns><6 digits> (e.g. 1s124214)"
    
    # Проверяем соответствие кода целевой станции
    expected_station_type = StationUpgradeCode.station_type_from_code(code_normalized)
    if not expected_station_type or expected_station_type != target_station_type:
        return False, "Code does not match target station type"
    
    # Проверяем код в БД (БЕЗ select_for_update для валидации, как в ValidateUpgradeCodeView)
    try:
        upgrade_code = StationUpgradeCode.objects.get(code=code_normalized)
    except StationUpgradeCode.DoesNotExist:
        return False, "Code not found"
    
    # Проверяем соответствие типа станции в БД
    if upgrade_code.station_type and upgrade_code.station_type != target_station_type:
        return False, "Code does not match target station type"
    
    # Проверяем валидность кода (используем тот же метод, что и ValidateUpgradeCodeView)
    if not upgrade_code.is_valid():
        return False, "Code is expired or invalid"
    
    if upgrade_code.used_by:
        return False, "Code already used"
    
    return True, upgrade_code


def get_craft_info(user_profile, target_station_type):
    """Возвращает информацию о крафте для отображения в UI"""
    # Автоматически проверяем и обновляем статусы станций перед получением информации
    check_and_update_user_stations_status(user_profile)
    
    # StoragePowerStationConfig определен выше в этом же файле
    
    required_station_type = get_previous_station_type(target_station_type)
    if not required_station_type:
        return None
    
    # Получаем доступные станции для крафта
    # Включаем станции со статусом 'ready', 'inactive' и 'active'
    # ВАЖНО: НЕ исключаем активную станцию - пользователь может использовать её для крафта
    stations_query = UserStation.objects.filter(
        user=user_profile,
        station_type=required_station_type,
        status__in=['ready', 'inactive', 'active']  # Готовые, неактивные или активные станции
    )
    
    available_stations = stations_query[:2]
    
    # Получаем конфигурацию целевой станции
    config_storage = StoragePowerStationConfig.objects.get(
        station_type=target_station_type, level=1
    )
    
    can_craft, error = can_craft_station(user_profile, target_station_type)
    
    return {
        "target_station_type": target_station_type,
        "required_station_type": required_station_type,
        "available_stations": [
            {
                "id": s.id,
                "station_type": s.station_type,
                "status": s.status,
                "created_at": s.created_at.isoformat(),
            }
            for s in available_stations
        ],
        "required_count": 2,
        "has_enough_stations": available_stations.count() >= 2,
        "price_kw": float(config_storage.price_kw),
        "price_tbtc": float(config_storage.price_tbtc),
        "building_duration": config_storage.get_duration().total_seconds(),
        "can_craft": can_craft,
        "error": error if not can_craft else None,
    }


def craft_station(user_profile, target_station_type, code=None, sol_payment_signature=None):
    """Крафтит новую станцию из 2 станций предыдущего уровня"""
    from core.models import StoragePowerStationConfig, GlobalSpendStats
    from django.db import transaction
    
    # ВАЖНО: Вся логика выполняется в транзакции для атомарности и корректной работы select_for_update()
    with transaction.atomic():
        # ВАЖНО: Код проверяется ПЕРВЫМ, ДО всех операций со списанием
        
        # Проверка кода (обязательно перед списанием)
        upgrade_code = None
        if code:
            is_valid, result = validate_craft_code(user_profile, target_station_type, code)
            if not is_valid:
                return False, result
            upgrade_code = result
        elif sol_payment_signature:
            # Альтернатива коду - SOL платеж (логика аналогична upgrade_station)
            # TODO: Реализовать проверку SOL платежа
            return False, "SOL payment verification not implemented yet"
        else:
            return False, "Code or SOL payment required for crafting"
        
        # Проверяем возможность крафта
        can_craft, error = can_craft_station(user_profile, target_station_type)
        if not can_craft:
            return False, error
        
        required_station_type = get_previous_station_type(target_station_type)
        
        # Получаем 2 станции для крафта
        # Включаем станции со статусом 'ready', 'inactive' и 'active'
        # ВАЖНО: НЕ исключаем активную станцию - пользователь может использовать её для крафта
        # Новая станция заменит активную после завершения стройки
        stations_query = UserStation.objects.filter(
            user=user_profile,
            station_type=required_station_type,
            status__in=['ready', 'inactive', 'active']  # Готовые, неактивные или активные станции
        )
        
        # Получаем список ID станций (без limit для проверки количества)
        station_ids = list(stations_query.values_list('id', flat=True))
        
        if len(station_ids) < 2:
            return False, "Not enough stations for crafting"
        
        # Берем первые 2 станции для крафта
        stations_to_use_ids = station_ids[:2]
        stations_to_use = UserStation.objects.filter(id__in=stations_to_use_ids)
        
        # Получаем конфигурацию
        config_storage = StoragePowerStationConfig.objects.get(
            station_type=target_station_type, level=1
        )
        config_gen = GenPowerStationConfig.objects.get(
            station_type=target_station_type, level=1
        )
        
        # Вычисляем время стройки
        building_duration = config_storage.get_duration() * user_profile.sbt_get_building_reduction()
        building_until = timezone.now() + building_duration
        
        # Помечаем код как использованный (если использовался код)
        if upgrade_code:
            upgrade_code.status = 'used'
            upgrade_code.used_by = user_profile
            upgrade_code.used_at = timezone.now()
            upgrade_code.save(update_fields=['status', 'used_by', 'used_at'])
        
        # Сохраняем предыдущее состояние перед применением новой станции
        # (если уже была активная станция 5+ уровня)
        prev_station_data = {}
        if user_profile.active_upgraded_station:
            # Уже есть активная станция 5+ уровня - сохраняем её параметры
            prev_station_data = {
                "prev_station_energy": user_profile.energy,
                "prev_station_power": user_profile.power,
                "prev_station_type": user_profile.station_type,
                "prev_station_storage_level": user_profile.storage_level,
                "prev_station_generation_level": user_profile.generation_level,
                "prev_station_engineer_level": user_profile.engineer_level,
            }
        elif not user_profile.active_upgraded_station:
            # Первая станция 5+ уровня - сохраняем параметры обычной станции
            prev_station_data = {
                "prev_station_energy": user_profile.energy,
                "prev_station_power": user_profile.power,
                "prev_station_type": user_profile.station_type,
                "prev_station_storage_level": user_profile.storage_level,
                "prev_station_generation_level": user_profile.generation_level,
                "prev_station_engineer_level": user_profile.engineer_level,
            }
        
        # Создаем новую станцию с правильным building_until
        # ВАЖНО: Сначала создаем станцию, чтобы получить её ID для active_upgraded_station
        new_station = create_user_station(
            user_profile, 
            target_station_type, 
            source="craft",
            building_until=building_until
        )
        
        # Сразу синхронизируем уровни в UserStation с начальными значениями (1)
        new_station.storage_level = 1
        new_station.generation_level = 1
        new_station.save(update_fields=['storage_level', 'generation_level'])
        
        # Связываем использованные станции с новой через ManyToMany (для истории)
        # ВАЖНО: Делаем это ДО удаления, иначе связь не сохранится
        new_station.crafted_from_stations.set(stations_to_use)
        
        # Удаляем использованные станции (СЖИГАЕМ их - полностью удаляем из БД)
        # Это аналогично burn NFT в блокчейне - станции больше не существуют
        # Используем filter по ID вместо delete() на QuerySet с limit
        UserStation.objects.filter(id__in=stations_to_use_ids).delete()
        
        # ВАЖНО: Сразу применяем параметры новой станции к UserProfile (как при апгрейде на 5 уровень)
        # Параметры используются сразу, но станция находится в стройке
        # Уровни storage и generation начинаются с 1 для новой станции
        
        # Обновляем UserProfile с новыми параметрами
        # Используем отдельные вызовы для F() выражений и обычных значений
        UserProfile.objects.filter(user_id=user_profile.user_id).update(
            energy=F("energy") - config_storage.price_kw,
            tbtc_wallet=F("tbtc_wallet") - config_storage.price_tbtc,
        )
        
        # Обновляем остальные поля отдельно (без F() выражений)
        # Ограничиваем storage до максимума новой станции
        current_storage = user_profile.storage
        new_storage_limit = config_storage.storage_limit
        limited_storage = min(float(current_storage), float(new_storage_limit))
        
        update_data = {
            "station_type": target_station_type,  # Сразу меняем тип станции
            "storage_level": 1,  # Начальный уровень storage для новой станции
            "generation_level": 1,  # Начальный уровень generation для новой станции
            "storage_limit": config_storage.storage_limit,  # Сразу применяем storage_limit новой станции
            "storage": limited_storage,  # Ограничиваем storage до максимума новой станции
            "generation_rate": config_gen.generation_rate,  # Сразу применяем generation_rate новой станции
            "building_until": building_until,  # Время стройки новой станции
            "active_upgraded_station": new_station,  # Связываем новую станцию с профилем
        }
        update_data.update(prev_station_data)
        
        UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
        
        # Обновляем user_profile для дальнейшего использования
        user_profile.refresh_from_db()
        
        # Обновляем статистику
        GlobalSpendStats.objects.update(
            energy_spent_build=F("energy_spent_build") + config_storage.price_kw,
            energy_spent_upgrade=F("energy_spent_upgrade") + config_storage.price_kw,
            tbtc_spent_build=F("tbtc_spent_build") + config_storage.price_tbtc,
            tbtc_spent_upgrade=F("tbtc_spent_upgrade") + config_storage.price_tbtc
        )
    
    return True, new_station


def activate_station_after_building(user_profile, user_station):
    """Активирует станцию после окончания стройки"""
    from core.models import StoragePowerStationConfig, GenPowerStationConfig, EngineerConfig
    
    with transaction.atomic():
        # Проверяем, что станция готова к активации
        if not user_station.can_be_activated():
            return False, "Station is not ready for activation"
        
        # Сохраняем текущее состояние
        if user_profile.active_upgraded_station:
            # Уже есть активная станция 5+ уровня - сохраняем её параметры
            prev_energy = user_profile.energy
            prev_power = user_profile.power
            prev_station_type = user_profile.station_type
            prev_storage_level = user_profile.storage_level
            prev_generation_level = user_profile.generation_level
            prev_engineer_level = user_profile.engineer_level
        else:
            # Первая станция 5+ уровня - сохраняем параметры обычной станции
            prev_energy = user_profile.energy
            prev_power = user_profile.power
            prev_station_type = user_profile.station_type
            prev_storage_level = user_profile.storage_level
            prev_generation_level = user_profile.generation_level
            prev_engineer_level = user_profile.engineer_level
        
        # Получаем конфигурацию новой станции
        station_type = user_station.station_type
        
        # ВАЖНО: Используем максимальный уровень из UserStation и UserProfile
        # Это нужно, чтобы не потерять улучшения, сделанные после создания UserStation, но до активации
        final_storage_level = max(user_station.storage_level, user_profile.storage_level)
        final_generation_level = max(user_station.generation_level, user_profile.generation_level)
        
        config_storage = StoragePowerStationConfig.objects.get(
            station_type=station_type, level=final_storage_level
        )
        config_gen = GenPowerStationConfig.objects.get(
            station_type=station_type, level=final_generation_level
        )
        
        # Активируем станцию
        # ВАЖНО: При улучшении параметры уже применены, поэтому сохраняем текущие energy и storage
        # Используем максимальные уровни из UserStation и UserProfile
        # НО для engineer_level сохраняем текущий уровень пользователя, так как инженер не сбрасывается при крафте
        # Ограничиваем storage до максимума новой станции
        current_storage = user_profile.storage
        new_storage_limit = config_storage.storage_limit
        limited_storage = min(float(current_storage), float(new_storage_limit))
        
        update_data = {
            "active_upgraded_station": user_station,
            "station_type": station_type,
            "storage_level": final_storage_level,  # Используем максимальный уровень
            "generation_level": final_generation_level,  # Используем максимальный уровень
            "engineer_level": user_profile.engineer_level,  # ВАЖНО: Сохраняем текущий уровень инженера пользователя, не из UserStation
            # Сохраняем текущие energy и storage (не сбрасываем, так как параметры уже применены при улучшении)
            # storage_limit и generation_rate уже применены при улучшении, но обновляем на всякий случай
            "storage_limit": config_storage.storage_limit,
            "storage": limited_storage,  # Ограничиваем storage до максимума новой станции
            "generation_rate": config_gen.generation_rate,
            "building_until": None,
        }
        
        # Сохраняем предыдущее состояние только если это первая станция 5+
        if not user_profile.active_upgraded_station:
            update_data.update({
                "prev_station_energy": prev_energy,
                "prev_station_power": prev_power,
                "prev_station_type": prev_station_type,
                "prev_station_storage_level": prev_storage_level,
                "prev_station_generation_level": prev_generation_level,
                "prev_station_engineer_level": prev_engineer_level,
            })
        
        UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
        
        # Обновляем статус станции и синхронизируем уровни с UserProfile
        user_station.status = 'active'
        user_station.building_until = None
        user_station.storage_level = final_storage_level  # Синхронизируем storage_level с UserProfile
        user_station.generation_level = final_generation_level  # Синхронизируем generation_level с UserProfile
        user_station.engineer_level = user_profile.engineer_level  # Синхронизируем уровень инженера с UserProfile
        user_station.save(update_fields=['status', 'building_until', 'storage_level', 'generation_level', 'engineer_level'])
    
    return True, None


# МИГРАЦИЯ NFT → SOLANA ASSETS: Boost Assets
class BoostAssetConfig(models.Model):
    """Конфигурация бустов для покупки через Solana"""
    boost_type = models.CharField(max_length=32, choices=[
        ('jarvis', 'Jarvis Bot'),
        ('asic_manager', 'ASIC Manager'),
        ('magnit', 'Magnetic ring'),
        ('cryo', 'Cryochamber'),
        ('electrics', 'Electrics'),
    ], verbose_name="Boost Type")
    boost_class = models.IntegerField(verbose_name="Boost Class")
    price_sol = models.DecimalField(max_digits=20, decimal_places=9, verbose_name="Price in SOL")
    
    # Условия применения
    station_level_min = models.IntegerField(null=True, blank=True, verbose_name="Min Station Level")
    station_level_max = models.IntegerField(null=True, blank=True, verbose_name="Max Station Level")
    hashrate_min = models.IntegerField(null=True, blank=True, verbose_name="Min Hashrate (Mh/s)")
    hashrate_max = models.IntegerField(null=True, blank=True, verbose_name="Max Hashrate (Mh/s)")
    
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    
    class Meta:
        verbose_name = "Boost Asset Config"
        verbose_name_plural = "Boost Asset Configs"
        unique_together = [('boost_type', 'boost_class')]
        ordering = ['boost_type', 'boost_class']
    
    def __str__(self):
        return f"{self.get_boost_type_display()} (Class {self.boost_class}) - {self.price_sol} SOL"


class BoostAsset(models.Model):
    """Внутренний буст-ассет пользователя (замена NFT-бустов)"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='boost_assets')
    asset_hash = models.CharField(max_length=128, unique=True, verbose_name="Asset Hash")
    boost_type = models.CharField(max_length=32, choices=[
        ('jarvis', 'Jarvis Bot'),
        ('asic_manager', 'ASIC Manager'),
        ('magnit', 'Magnetic ring'),
        ('cryo', 'Cryochamber'),
        ('electrics', 'Electrics'),
    ], verbose_name="Boost Type")
    boost_class = models.IntegerField(verbose_name="Boost Class")
    purchase_time = models.DateTimeField(auto_now_add=True, verbose_name="Purchase Time")
    status = models.CharField(max_length=16, default='success', choices=[
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], verbose_name="Status")
    
    # Связь с платежом
    payment = models.ForeignKey(SolanaPayment, on_delete=models.SET_NULL, null=True, blank=True, related_name='boost_assets')
    
    # Метаданные для дополнительных данных
    metadata = models.JSONField(null=True, blank=True, verbose_name="Asset Metadata")
    
    # Ручное включение/отключение буста (по умолчанию включен)
    is_enabled = models.BooleanField(default=True, verbose_name="Is Enabled")
    
    class Meta:
        verbose_name = "Boost Asset"
        verbose_name_plural = "Boost Assets"
        ordering = ['-purchase_time']
        # Убрано unique_together - пользователь может купить несколько бустов одного типа/класса
        # При применении используется только один (первый найденный в get_active_boosts())
        indexes = [
            models.Index(fields=['user', 'boost_type', 'status']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.get_boost_type_display()} (Class {self.boost_class}) - {self.user.username}"


class EmailSubscription(models.Model):
    """Модель для хранения email подписок на рассылку"""
    email = models.EmailField(unique=True, null=False, blank=False, verbose_name="Email")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Email Subscription"
        verbose_name_plural = "Email Subscriptions"
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class WalletTopupExchangeRate(models.Model):
    """Модель для хранения курсов обмена для пополнения кошелька"""
    token_type = models.CharField(max_length=10, choices=[('kw', 'kW'), ('tbtc', 'sBTC')], unique=True, verbose_name="Token Type")
    rate = models.DecimalField(max_digits=20, decimal_places=9, verbose_name="Exchange Rate (tokens per 1 SOL)")
    min_amount = models.DecimalField(max_digits=20, decimal_places=9, default=0, verbose_name="Minimum Amount")
    max_amount = models.DecimalField(max_digits=20, decimal_places=9, null=True, blank=True, verbose_name="Maximum Amount")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Wallet Topup Exchange Rate"
        verbose_name_plural = "Wallet Topup Exchange Rates"
        ordering = ['token_type']

    def __str__(self):
        return f"{self.token_type}: {self.rate} tokens per 1 SOL"


class WalletTopup(models.Model):
    """Модель для хранения пополнений внутреннего кошелька через Solana"""
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name='wallet_topups')
    signature = models.CharField(max_length=128, unique=True, verbose_name="Transaction Signature")
    token_type = models.CharField(max_length=10, choices=[('kw', 'kW'), ('tbtc', 'sBTC')], verbose_name="Token Type")
    amount = models.DecimalField(max_digits=20, decimal_places=9, verbose_name="Token Amount")
    payment_method = models.CharField(max_length=10, choices=[('spl', 'SPL Token'), ('sol', 'SOL')], verbose_name="Payment Method")
    mint_address = models.CharField(max_length=128, null=True, blank=True, verbose_name="SPL Mint Address")
    sol_amount = models.DecimalField(max_digits=20, decimal_places=9, null=True, blank=True, verbose_name="SOL Amount")
    exchange_rate = models.DecimalField(max_digits=20, decimal_places=9, null=True, blank=True, verbose_name="Exchange Rate")
    network = models.CharField(max_length=16, default="devnet", verbose_name="Network")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Wallet Topup"
        verbose_name_plural = "Wallet Topups"
        ordering = ['-created_at']

    def __str__(self):
        return f"Topup {self.signature[:8]}... by {self.user.username} - {self.amount} {self.token_type}"


class SolanaNetworkSettings(models.Model):
    """Настройки сети Solana для обработки транзакций"""
    
    devnet_enabled = models.BooleanField(
        default=True,
        verbose_name="Enable Devnet Processing",
        help_text="Включить обработку транзакций из Devnet"
    )
    mainnet_enabled = models.BooleanField(
        default=False,
        verbose_name="Enable Mainnet Processing",
        help_text="Включить обработку транзакций из Mainnet"
    )
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")

    class Meta:
        verbose_name = "Solana Network Settings"
        verbose_name_plural = "Solana Network Settings"

    def save(self, *args, **kwargs):
        # Singleton pattern - всегда сохраняем с id=1
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        # Не разрешаем удаление
        pass

    def is_network_enabled(self, network: str) -> bool:
        """Проверить, включена ли обработка для указанной сети"""
        if network == 'devnet':
            return self.devnet_enabled
        elif network == 'mainnet-beta':
            return self.mainnet_enabled
        return False

    def __str__(self):
        networks = []
        if self.devnet_enabled:
            networks.append("Devnet")
        if self.mainnet_enabled:
            networks.append("Mainnet")
        status = ", ".join(networks) if networks else "All disabled"
        return f"Solana Networks: {status}"


STATION_PREFIX_MAP = {
    '1s': "Boiler house",
    '2s': "Coal power plant",
    '3s': "Thermal power plant",
    '4s': "Geothermal power plant",
    '5s': "Nuclear power plant",
    '6s': "Thermonuclear power plant",
    '7s': "Dyson Sphere",
    '8s': "Neutron star",
    '9s': "Antimatter",
    '10s': "Galactic core",
}

STATION_CODE_REGEX = re.compile(r'^(1s|2s|3s|4s|5s|6s|7s|8s|9s|10s)[0-9]{6}$', re.IGNORECASE)


class StationUpgradeCode(models.Model):
    """Модель для кодов перехода между типами станций"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    ]

    class StationType(models.TextChoices):
        BOILER_HOUSE = "Boiler house", "Boiler house"
        COAL_POWER_PLANT = "Coal power plant", "Coal power plant"
        THERMAL_POWER_PLANT = "Thermal power plant", "Thermal power plant"
        GEOTHERMAL_POWER_PLANT = "Geothermal power plant", "Geothermal power plant"
        NUCLEAR_POWER_PLANT = "Nuclear power plant", "Nuclear power plant"
        THERMONUCLEAR_POWER_PLANT = "Thermonuclear power plant", "Thermonuclear power plant"
        DYSON_SPHERE = "Dyson Sphere", "Dyson Sphere"
        NEUTRON_STAR = "Neutron star", "Neutron star"
        ANTIMATTER = "Antimatter", "Antimatter"
        GALACTIC_CORE = "Galactic core", "Galactic core"

    # Формат кода: до 10 символов, префикс <Ns> или <10s> + 6 цифр, например 1s124214 или 10s124214
    # Для станций 1-9: формат "NsXXXXXX" (8 символов), для станции 10: формат "10sXXXXXX" (10 символов)
    code = models.CharField(max_length=10, unique=True, db_index=True, verbose_name="Code")
    station_type = models.CharField(
        max_length=50,
        choices=StationType.choices,
        null=True,
        blank=True,
        db_index=True,
        verbose_name="Station Type",
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    expires_at = models.DateTimeField(verbose_name="Expires At")
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='active',
        verbose_name="Status"
    )
    used_by = models.ForeignKey(
        UserProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='used_codes',
        verbose_name="Used By"
    )
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Used At")

    class Meta:
        verbose_name = "Station Upgrade Code"
        verbose_name_plural = "Station Upgrade Codes"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'status']),
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['station_type', 'status']),
        ]

    def __str__(self):
        return f"{self.code} - {self.status}"

    @staticmethod
    def normalize_code(code: str) -> str:
        return (code or "").strip().lower()

    @classmethod
    def station_type_from_code(cls, code: str):
        """Returns station type from code prefix"""
        match = STATION_CODE_REGEX.match(cls.normalize_code(code))
        if not match:
            return None
        prefix = match.group(1).lower()
        return STATION_PREFIX_MAP.get(prefix)

    def is_valid(self):
        """Check code validity"""
        if self.status != 'active':
            return False
        if timezone.now() > self.expires_at:
            return False
        return True


class StationUpgradeSolPayment(models.Model):
    """Link between SOL payment and station upgrade"""
    payment = models.OneToOneField(
        SolanaPayment,
        on_delete=models.CASCADE,
        related_name='station_upgrade',
        verbose_name="SOL Payment"
    )
    target_station_type = models.CharField(
        max_length=50,
        verbose_name="Target Station Type",
        help_text="Station type for which the upgrade was paid"
    )
    expected_price_sol = models.DecimalField(
        max_digits=20,
        decimal_places=9,
        verbose_name="Expected Price in SOL"
    )
    used = models.BooleanField(
        default=False,
        verbose_name="Used",
        help_text="Whether the payment was used for station upgrade"
    )
    used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Used At"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At"
    )
    
    class Meta:
        verbose_name = "Station Upgrade SOL Payment"
        verbose_name_plural = "Station Upgrade SOL Payments"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment']),
            models.Index(fields=['target_station_type', 'used']),
            models.Index(fields=['used', 'created_at']),
        ]
    
    def __str__(self):
        return f"SOL payment for {self.target_station_type} - {'Used' if self.used else 'Pending'}"