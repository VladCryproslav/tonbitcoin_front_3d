import time
import django, os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()

from core.models import UserProfile
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

from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.utils import timezone

# ОПЦИОНАЛЬНО: Переключение логики снижения power
# False (по умолчанию): power снижается ВСЕГДА, даже когда storage = storage_limit
# True: power снижается ТОЛЬКО пока storage < storage_limit
POWER_REDUCTION_ONLY_WHEN_STORAGE_NOT_FULL = False

while True:
    start_time = time.time()
    with transaction.atomic():
        now = timezone.now()
        
        # ОРИГИНАЛЬНАЯ ЛОГИКА ГЕНЕРАЦИИ ЭНЕРГИИ (не изменена)
        logger.info(
            UserProfile.objects.filter(
                ~Q(storage=F("storage_limit"))
                & Q(overheated_until=None)
                & (Q(jarvis_expires__lt=now) | Q(jarvis_expires__isnull=True))
                & (Q(building_until__lt=now) | Q(building_until__isnull=True))
            ).update(
                storage=F("storage") + F("generation_rate") * F("power") / 100 / 60
            )
        )
        logger.info(
            UserProfile.objects.filter(storage__gt=F("storage_limit")).update(
                storage=F("storage_limit")
            )
        )
        
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
