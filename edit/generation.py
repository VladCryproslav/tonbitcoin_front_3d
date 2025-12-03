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
from django.utils import timezone


while True:
    start_time = time.time()
    with transaction.atomic():
        now = timezone.now()
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
