import csv
import logging
import math
import random
import time
import traceback
from datetime import datetime, timedelta

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
    start_of_day = start.replace(hour=0, minute=0, second=0, microsecond=0)

    first_time = start_of_day + timedelta(seconds=random.randint(0, 24 * 3600 - 1))
    times = [first_time]

    for _ in range(n - 1):
        min_next_time = times[-1] + timedelta(hours=4)
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
            "price_ton": int(row["Price (TON)"] or 0),
        }
        equipments[name] = equipment
    return equipments


csv_data = """Rarity,Name,Hash Rate,Measurement,Consumption (kW),Mining speed (tBTC),Price (TON)
Common,Asic S1,100,Hour,1,"0,02",2
Common,Asic S3,200,Hour,2,"0,04",4
Rare,Asic S5+,400,Hour,4,"0,08",8
Rare,Asic S7+,1000,Hour,10,"0,21",16
Rare,Asic S9+,2500,Hour,20,"0,52",32
Epic,Asic S11 XP,6000,Hour,44,"1,25",64
Epic,Asic S15 XP,15000,Hour,92,"3,13",128
Epic,Asic S17 XP,40000,Hour,192,"8,33",256
Legendary,Asic S19 XP+,100000,Hour,400,"20,83",512
Legendary,Asic S21 XP+,250000,Hour,800,"52,08",1024
Mythic,Asic SX Ultra Pro,600000,Hour,1664,"125,00",2048
Special,Asic S10 Maxx,1000,Hour,80,"5",32
Special,Asic S30 Maxx,2000,Hour,80,"10",64
Special,Asic S50 Maxx,2800,Hour,80,"15",128
Special,Asic S70 Maxx,5000,Hour,80,"25",128
Special,Asic S90 Maxx,7500,Hour,80,"40",256
"""

asics_data = parse_csv_to_dicts(csv_data)
from django.conf import settings
from telebot import TeleBot

bot = TeleBot(settings.BOT_TOKEN, parse_mode="HTML")


class UserProfile(models.Model):
    user_id = models.BigIntegerField(
        unique=True
    )  # Унікальний ідентифікатор користувача
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
    has_singularity_station = models.BooleanField(default=False)
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
    prem_power_plant_old_owner = models.BooleanField(default=True)  # True = старі характеристики преміальних станцій
    # Singularity при откате использует те же hydro_prev_* что и орбитальная/гидра
    # ============

    past_engineer_level = models.IntegerField(default=0)  # Рівень інженера
    kw_per_tap = models.FloatField(default=0.025)  # Кількість кВ на тап
    storage = models.DecimalField(max_digits=36, decimal_places=16, default=10)
    storage_limit = models.DecimalField(max_digits=36, decimal_places=16, default=10)
    generation_rate = models.DecimalField(max_digits=36, decimal_places=16, default=5)
    
    
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

    # Нові поля для зберігання інформації про рефералів та отримані бонуси
    first_name = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
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

    repair_kit_expires = models.DateTimeField(null=True, blank=True)
    repair_kit_power_level = models.DecimalField(
        max_digits=36, 
        decimal_places=16, 
        null=True, 
        blank=True,
        default=None
    )

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
    energy_run_extra_life_used = models.BooleanField(
        default=False,
        help_text="Использована ли 4-я жизнь в текущем забеге"
    )
    energy_run_claimed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Время последнего успешного начисления за забег (для идемпотентности claim)"
    )
    # Льготные проигрыши раннера по уровням станции (1–3)
    runner_lose_uses_level_1 = models.IntegerField(
        default=0,
        help_text="Сколько льготных проигрышей уже было на станции 1 уровня"
    )
    runner_lose_uses_level_2 = models.IntegerField(
        default=0,
        help_text="Сколько льготных проигрышей уже было на станции 2 уровня"
    )
    runner_lose_uses_level_3 = models.IntegerField(
        default=0,
        help_text="Сколько льготных проигрышей уже было на станции 3 уровня"
    )

    # Training Run (Тренировочные забеги)
    training_run_last_started_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Время последнего тренировочного забега (для сброса счетчика по часам)"
    )
    training_run_count_this_hour = models.IntegerField(
        default=0,
        help_text="Количество тренировочных забегов в текущий час"
    )

    stop_mining_at1 = models.DateTimeField(null=True, blank=True)
    stop_mining_at2 = models.DateTimeField(null=True, blank=True)
    stop_mining_at3 = models.DateTimeField(null=True, blank=True)
    stop_mining_next = models.DateTimeField(null=True, blank=True)
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
        if self.electrics_expires and self.electrics_expires > timezone.now():
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
            return 0.08  # 4% + 4% (pool + fee)
        if self.has_silver_sbt and self.has_silver_sbt_nft:
            return 0.09  # 4.5% + 4.5%
        return 0.10  # 5% + 5%

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



    def can_use_staking_bonus(self, input_amount):
        BONUS_LIMIT = 100_000
        total_locked = (
            UserStaking.objects.filter(user=self, status="active").aggregate(
                total=models.Sum("token_amount")
            )["total"]
            or 0
        )
        return (total_locked + input_amount) <= BONUS_LIMIT

    def save(self, *args, **kwargs):
        # try:
        #     self.storage_limit = StoragePowerStationConfig.objects.get(
        #         station_type=self.station_type, level=self.storage_level
        #     ).storage_limit
        #     self.generation_rate = GenPowerStationConfig.objects.get(
        #         station_type=self.station_type, level=self.generation_level
        #     ).generation_rate
        #     self.kw_per_tap = EngineerConfig.objects.get(
        #         level=self.engineer_level
        #     ).tap_power
        # except Exception:
        #     logging.exception(f"User save error {self.user_id}")
        super().save(*args, **kwargs)

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

ASIC возвращён в раздел “Оборудование”, чтобы снова сдать его в аренду — создайте новую заявку в меню Инвестора.""",
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
        return STATION_LEVELS.index(self.station_type)

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
        UserProfile.objects.filter(user_id=self.user_id).update(
            station_type="Boiler house",
            storage_level=1,
            generation_level=1,
            storage_limit=config_storage.storage_limit,
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

    def upgrade_engineer(self):
        self.refresh_from_db()
        with transaction.atomic():
            next_level = self.engineer_level + 1
            config = EngineerConfig.objects.get(level=next_level)
            if config.hire_cost and self.energy >= config.hire_cost:
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
            return False

    def upgrade_station(self):
        self.refresh_from_db()
        if self.storage_level == 3 and self.generation_level == 3:
            action_logger.info(
                f"user {self.user_id} | upgrading station {self.energy} kw, {self.tbtc_wallet} tbtc"
            )
            next_station_type = self.get_next_station_type()
            print(next_station_type)
            if next_station_type:
                config_storage = StoragePowerStationConfig.objects.get(
                    station_type=next_station_type, level=1
                )
                if (
                    self.energy >= config_storage.price_kw
                    and self.tbtc_wallet >= config_storage.price_tbtc
                ):
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

                    print(config_storage.get_duration())
                    UserProfile.objects.filter(user_id=self.user_id).update(
                        energy=F("energy") - config_storage.price_kw,
                        tbtc_wallet=F("tbtc_wallet") - config_storage.price_tbtc,
                        station_type=next_station_type,
                        storage_level=1,
                        generation_level=1,
                        storage_limit=config_storage.storage_limit,
                        generation_rate=config_gen.generation_rate,
                        building_until=timezone.now()
                        + config_storage.get_duration()
                        * self.sbt_get_building_reduction(),
                    )
                    self.refresh_from_db()
                    action_logger.info(
                        f"user {self.user_id} | upgraded station {self.energy} kw, {self.tbtc_wallet} tbtc"
                    )
                    
                    StationUpgradeEvent.objects.create(
                        user=self,
                        level=f"{self.get_station_level()+1}-{self.generation_level}"
                    )
                    return True
        return False

    def upd_stopper(self):
        manager = Booster.objects.filter(slug="asic_manager").first()
        stop_count = (
            max(int(manager.n1), 1) if manager.n1 and manager.n1.isdigit() else 3
        )
        now = timezone.now()
        if self.stop_mining_next is None or self.stop_mining_next.date() <= now.date():
            dates = generate_random_dates(now, n=stop_count)
            UserProfile.objects.filter(user_id=self.user_id).update(
                stop_mining_next=now + timedelta(days=1),
                stop_mining_at1=dates.pop(0) if dates else None,
                stop_mining_at2=dates.pop(0) if dates else None,
                stop_mining_at3=dates.pop(0) if dates else None,
            )
            self.refresh_from_db()

        UserProfile.objects.filter(user_id=self.user_id).update(
            stop_mining_at1=(
                None
                if (self.stop_mining_at1 and self.stop_mining_at1 < now)
                else self.stop_mining_at1
            ),
            stop_mining_at2=(
                None
                if (self.stop_mining_at2 and self.stop_mining_at2 < now)
                else self.stop_mining_at2
            ),
            stop_mining_at3=(
                None
                if (self.stop_mining_at3 and self.stop_mining_at3 < now)
                else self.stop_mining_at3
            ),
        )

    def add_tbtc_mining(self):
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
            rent_mined_tokens_balance = 0
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

            print()

            mined = 0
            mined_tokens_balance_s21 = 0
            mined_tokens_balance_sx = 0
            for nft_address in self.nft_string.split(";"):
                nft = NFTDatabase.objects.filter(nft=nft_address).first()
                if nft:
                    if nft.name == "Asic S21 XP+":
                        mined_tokens_balance_s21 += nft.mining_speed_tbtc * min(
                            (timezone.now() - self.last_tbtc_added).total_seconds()
                            / 3600,
                            1,
                        )
                        continue

                    if nft.name == "Asic SX Ultra Pro":
                        mined_tokens_balance_sx += nft.mining_speed_tbtc * min(
                            (timezone.now() - self.last_tbtc_added).total_seconds()
                            / 3600,
                            1,
                        )
                        continue
                    
                    if not TimedUserNFT.objects.filter(
                        user=self, nft_address=nft_address, block_until__gt=timezone.now()
                    ).exists():
                        # print(nft.mining_speed_tbtc)
                        mined += (
                            min((timezone.now() - self.last_tbtc_added).total_seconds() / 3600, 1)
                            * nft.mining_speed_tbtc
                        )

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
            return 2320 if getattr(self, "prem_power_plant_old_owner", True) else 1840
        if self.has_singularity_station:
            return 3200
        if self.has_hydro_station:
            return 1000
        return StoragePowerStationConfig.objects.filter(
            station_type=self.station_type,
            level=self.storage_level,
        ).first().storage_limit

    def calc_generation_rate(self):
        if self.has_orbital_station:
            if getattr(self, "prem_power_plant_old_owner", True):
                if self.orbital_first_owner:
                    if self.orbital_is_blue:
                        return 580
                    return 290
                return 580
            return 460
        if self.has_singularity_station:
            return 800
        if self.has_hydro_station:
            return 250
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
        current_index = station_types.index(self.station_type)
        if current_index < len(station_types) - 1:
            return station_types[current_index + 1]
        return None

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
    saved_percent_on_lose = models.FloatField(
        default=0,
        help_text='Процент энергии (kW), сохраняемой при проигрыше забега для этого уровня инженера (0–100)'
    )

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
    min_duration = models.PositiveIntegerField(default=15)  # in seconds
    max_duration = models.PositiveIntegerField(default=300)  # in seconds
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
    engineer_minus = models.IntegerField(default=1)

    min_rent = models.FloatField(default=10)
    max_auto_rent = models.FloatField(default=1000)


class RunnerConfig(models.Model):
    """Конфигурация для раннера"""
    # Цена 1 STAR в kW (например, 100 kW = 1 STAR)
    stars_per_kw = models.FloatField(
        default=100,
        help_text="Количество kW за 1 STAR (например, 100 означает 100 kW = 1 STAR)"
    )
    max_training_runs_per_hour = models.IntegerField(
        default=5,
        help_text="Максимальное количество тренировочных забегов в час для каждого пользователя"
    )
    # Энергозабег: поинты в зависимости от времени с последнего забега
    energy_points_per_minute = models.IntegerField(
        default=2,
        help_text="Базовых поинтов за 1 минуту ожидания (1 ч → 120 при 2)"
    )
    energy_points_reserve_percent = models.IntegerField(
        default=20,
        help_text="Процент запаса поинтов сверх базового количества"
    )
    energy_run_max_hours = models.IntegerField(
        default=4,
        help_text="Максимум часов для расчёта поинтов (4 ч × 60 × 2 = 480 поинтов)"
    )
    # Льготный процент сохранения при проигрыше для станций 1–3 уровня
    lose_percent_station_level_1 = models.FloatField(
        default=100,
        help_text="Процент собранной энергии при проигрыше для станции 1 уровня"
    )
    lose_percent_station_level_2 = models.FloatField(
        default=100,
        help_text="Процент собранной энергии при проигрыше для станции 2 уровня"
    )
    lose_percent_station_level_3 = models.FloatField(
        default=50,
        help_text="Процент собранной энергии при проигрыше для станции 3 уровня"
    )
    # Лимиты количества льготных проигрышей (на пользователя) для уровней 1–3
    lose_max_uses_station_level_1 = models.IntegerField(
        default=200,
        help_text="Сколько раз пользователь может получить льготный процент на 1 уровне станции"
    )
    lose_max_uses_station_level_2 = models.IntegerField(
        default=200,
        help_text="Сколько раз пользователь может получить льготный процент на 2 уровне станции"
    )
    lose_max_uses_station_level_3 = models.IntegerField(
        default=100,
        help_text="Сколько раз пользователь может получить льготный процент на 3 уровне станции"
    )
    # Настройки скорости забега
    run_base_speed = models.FloatField(
        default=0.15,
        help_text="Минимальная скорость (старт)"
    )
    run_mid_speed = models.FloatField(
        default=0.25,
        help_text="Скорость на 60% дистанции"
    )
    run_max_speed = models.FloatField(
        default=0.32,
        help_text="Максимальная скорость (с 90%)"
    )
    run_first_ramp_end = models.IntegerField(
        default=60,
        help_text="Процент дистанции, до которого идет первый набор скорости (0% -> 60%)"
    )
    run_second_ramp_end = models.IntegerField(
        default=90,
        help_text="Процент дистанции, до которого идет второй набор скорости (60% -> 90%)"
    )

    class Meta:
        verbose_name = "Runner Config"
        verbose_name_plural = "Runner Configs"
    
    def __str__(self):
        return f"Runner Config: {self.stars_per_kw} kW = 1 STAR, {self.max_training_runs_per_hour} training runs/hour"


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
    
    # Новые поля для восстановления
    nft_address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='NFT Address',
        help_text='Адрес NFT станции для восстановления'
    )
    is_restored = models.BooleanField(
        default=False,
        verbose_name='Восстановлено',
        help_text='Была ли станция восстановлена'
    )
    restored_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата восстановления',
        help_text='Дата и время восстановления станции'
    )

    def __str__(self):
        status = "✅ Восстановлено" if self.is_restored else "❌ Не восстановлено"
        return f"StationRollbackLog(user={self.user.user_id}, from_station={self.from_station}, {status})"


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
    gradation_value = models.IntegerField(default=1)
    
class WalletInfo(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True)
    wallet = models.CharField(max_length=255, verbose_name="Wallet Address")
    kw_amount = models.FloatField(default=0)
    tbtc_amount = models.FloatField(default=0)
    tbtc_amount_s21 = models.FloatField(default=0)
    tbtc_amount_sx = models.FloatField(default=0)
    block_until = models.DateTimeField(verbose_name="Block Until", null=True, blank=True)
    

class Lottery(models.Model):
    total_tickets = models.IntegerField(default=150, verbose_name="Total Tickets")
    remaining_tickets = models.IntegerField(default=150, verbose_name="Remaining Tickets")
    ticket_price = models.FloatField(default=0.01, verbose_name="Ticket Price (TON)")
    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Lottery"
        verbose_name_plural = "Lotteries"

    def __str__(self):
        return f"Lottery {self.id} - {self.remaining_tickets}/{self.total_tickets} tickets"


class LotteryParticipant(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE, verbose_name="User", null=True, blank=True)
    username = models.CharField(max_length=100, verbose_name="Username")
    wallet_address = models.CharField(max_length=100, verbose_name="Wallet Address", unique=True)
    tickets_count = models.IntegerField(default=1, verbose_name="Tickets Count")
    transaction_hash = models.CharField(max_length=200, verbose_name="Transaction Hash")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        verbose_name = "Lottery Participant"
        verbose_name_plural = "Lottery Participants"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.username} - {self.tickets_count} tickets"

    