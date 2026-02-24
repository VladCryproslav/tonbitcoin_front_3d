import time
import django, os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()

import logging


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,  # Set the minimum logging level for the root logger
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Log to the specified file
            logging.StreamHandler(),  # Log to the console
        ],
    )

    # Create a custom logger
    logger = logging.getLogger("my_logger3")
    logger.setLevel(logging.DEBUG)  # Set the minimum logging level

    logger.propagate = False

    # Create handlers
    file_handler = logging.FileHandler(log_file)
    # console_handler = logging.StreamHandler()

    # Set logging levels for handlers
    file_handler.setLevel(logging.DEBUG)
    # console_handler.setLevel(logging.INFO)

    # Create formatters and add them to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    # console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    # logger.addHandler(console_handler)

    return logger


logger = setup_logging("logs/gen.log")

import random
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.utils import timezone

from core.models import OverheatConfig, UserProfile
from tgbot.views import bot

# ОПЦИОНАЛЬНО: Переключение логики снижения power
# False (по умолчанию): power снижается ВСЕГДА, даже когда storage = storage_limit
# True: power снижается ТОЛЬКО пока storage < storage_limit
POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = True

# Типы станций с перегревом при заполнении Storage до лимита (docs/OVERHEAT_SYSTEM_ANALYSIS.md)
OVERHEAT_HOURS_BY_TYPE = {
    "Thermal power plant": 4,
    "Geothermal power plant": 2,
    "Nuclear power plant": 2,
    "Thermonuclear power plant": 1,
    "Dyson Sphere": 1,
    "Neutron star": 1,
    "Antimatter": 1,
    "Galactic core": 1,
}

OVERHEAT_TELEGRAM_MESSAGE = (
    "📢 Ваша электростанция перегрелась. Зайдите в приложение, дождитесь окончания охлаждения и нажмите кнопку включения генерации."
)

while True:
    start_time = time.time()
    with transaction.atomic():
        now = timezone.now()
        
        # Генерация энергии: прибавляем к storage и к overheat_energy_collected (для цели перегрева)
        generation_delta = F("generation_rate") * F("power") / 100 / 60
        same_filter = (
            ~Q(storage=F("storage_limit"))
            & Q(overheated_until=None)
            & (Q(jarvis_expires__lt=now) | Q(jarvis_expires__isnull=True))
            & (Q(building_until__lt=now) | Q(building_until__isnull=True))
        )
        logger.info(
            UserProfile.objects.filter(same_filter).update(
                storage=F("storage") + generation_delta,
                overheat_energy_collected=F("overheat_energy_collected") + generation_delta,
            )
        )
        logger.info(
            UserProfile.objects.filter(storage__gt=F("storage_limit")).update(
                storage=F("storage_limit")
            )
        )

        # Перегрев по цели (overheat_goal), а не при storage=limit (docs/OVERHEAT_SYSTEM_ANALYSIS.md)
        # Пример: первый перегрев при 245 kW, второй при +450 kW (695 всего) за период для атомки
        overheat_config = OverheatConfig.objects.first()
        min_dur = getattr(overheat_config, "min_duration", 30) if overheat_config else 30
        max_dur = getattr(overheat_config, "max_duration", 300) if overheat_config else 300

        # Выставить случайный goal тем, у кого его ещё нет (первый перегрев в периоде)
        users_need_goal = UserProfile.objects.filter(
            overheated_until__isnull=True,
            overheat_goal__isnull=True,
            station_type__in=list(OVERHEAT_HOURS_BY_TYPE.keys()),
        ).exclude(
            Q(cryo_expires__gt=now) & Q(cryo_expires__isnull=False)
        )
        for u in users_need_goal:
            if u.cryo_expires and now < u.cryo_expires:
                continue
            needed_hours = OVERHEAT_HOURS_BY_TYPE.get(u.station_type)
            if not needed_hours:
                continue
            max_goal = (
                float(u.generation_rate)
                * needed_hours
                * (float(u.power) / 100)
            )
            if max_goal <= 0:
                continue
            goal = random.uniform(0, max_goal)
            UserProfile.objects.filter(id=u.id).update(overheat_goal=goal)

        # Срабатывание перегрева при достижении цели (overheat_energy_collected >= overheat_goal)
        users_overheated = UserProfile.objects.filter(
            overheated_until__isnull=True,
            overheat_goal__isnull=False,
            station_type__in=list(OVERHEAT_HOURS_BY_TYPE.keys()),
        ).exclude(
            Q(cryo_expires__gt=now) & Q(cryo_expires__isnull=False)
        )
        for u in users_overheated:
            if u.cryo_expires and now < u.cryo_expires:
                continue
            if float(u.overheat_energy_collected) < float(u.overheat_goal):
                continue
            duration_sec = random.randint(min_dur, max_dur)
            overheated_until = now + timedelta(seconds=duration_sec)
            UserProfile.objects.filter(id=u.id).update(
                overheated_until=overheated_until,
                was_overheated=True,
                overheat_energy_collected=0,
                overheat_goal=None,
            )
            try:
                bot.send_message(u.user_id, OVERHEAT_TELEGRAM_MESSAGE)
            except Exception:
                pass

        # НОВАЯ ЛОГИКА: Снижение power при генерации
        # Получаем пользователей для снижения power (те же условия что и для генерации)
        users_for_power_reduction = UserProfile.objects.filter(
            Q(overheated_until=None)
            & (Q(jarvis_expires__lt=now) | Q(jarvis_expires__isnull=True))
            & (Q(building_until__lt=now) | Q(building_until__isnull=True))
            & Q(power__gt=0)  # Защита: не снижаем если power = 0
        )
        
        # Обрабатываем каждого пользователя для снижения power
        for u in users_for_power_reduction.all():
            # Проверяем активность Repair Kit
            is_repair_kit_active = (
                u.repair_kit_expires and
                now < u.repair_kit_expires
            )
            
            # Определяем нужно ли снижать power
            should_reduce_power = False
            
            if POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL:
                # Опциональная логика: снижение только пока storage < storage_limit
                should_reduce_power = (
                    float(u.storage) < float(u.storage_limit) and
                    not is_repair_kit_active
                )
            else:
                # По умолчанию: снижение всегда (кроме случаев с Repair Kit)
                should_reduce_power = not is_repair_kit_active
            
            # Применяем снижение power
            if should_reduce_power:
                # Снижение power аналогично Jarvis: 1/120 * sbt_get_power() за минуту (0.5% в час)
                power_reduction = 1 / 120 * u.sbt_get_power()
                UserProfile.objects.filter(id=u.id).update(
                    power=F("power") - power_reduction
                )
            elif is_repair_kit_active and u.repair_kit_power_level is not None:
                # Repair Kit активен: power не снижается, но может быть поднят
                UserProfile.objects.filter(id=u.id).update(
                    power=Greatest(
                        F("power"),
                        u.repair_kit_power_level,
                    )
                )
        
        # Ограничение power до минимума 0 (на всякий случай)
        UserProfile.objects.filter(power__lt=0).update(power=0)

        # Burn referral bonuses if not claimed within 7 days
        seven_days_ago = timezone.now() - timezone.timedelta(hours=168)
        h12_ago = timezone.now() - timezone.timedelta(hours=12)
        logger.info(
            UserProfile.objects.filter(
                last_kw_bonus_claimed_at__lt=seven_days_ago
            ).update(
                bonus_kw_level_1=0,
                bonus_kw_level_2=0,
                last_kw_bonus_claimed_at=timezone.now(),
            )
        )

        logger.info(
            UserProfile.objects.filter(
                last_tbtc_bonus_claimed_at__lt=seven_days_ago
            ).update(
                bonus_tbtc_level_1=0,
                bonus_tbtc_level_2=0,
                last_tbtc_bonus_claimed_at=timezone.now(),
            )
        )

        logger.info(
            UserProfile.objects.filter(
                last_staking_bonus_claimed_at__lt=seven_days_ago
            ).update(
                bonus_invest_level_1=0,
                bonus_invest_level_2=0,
                last_staking_bonus_claimed_at=timezone.now(),
            )
        )

        
        for u in UserProfile.objects.filter(
                mining_last_stopped__lt=h12_ago,
                rented_from__isnull=False,  # Ensure the user is a renter in at least one agreement
                rented_from__end_date__gte=timezone.now(),  # Ensure the rental is still active
            ):
            u.remove_point()

# пройтись по всем орендам и остановить оренду у всех у кого с начала аренды прошло больше 12 часов
        # for r in NFTRentalAgreement.

        # logger.info(
        #     UserProfile.objects.filter(points__lte=-3).update(
        #         rent_blocked_until=timezone.now() + timezone.timedelta(days=7),
        #         points=0,
        #     )
        # )

    elapsed_time = time.time() - start_time
    logger.info(f"upd {elapsed_time}")
    sleep_time = max(60 - elapsed_time, 0)
    time.sleep(sleep_time)
