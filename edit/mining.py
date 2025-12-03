import os
import time
import traceback
from pytonapi import AsyncTonapi
import django


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import (
    AsicsCoefs,
    BufferTransaction,
    MiningStats,
    UserProfile,
    add_mining_commission,
)
from tasks.models import Booster
from django.utils import timezone

import logging
from tgbot.views import bot


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
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.DEBUG)  # Set the minimum logging level

    logger.propagate = False

    # Create handlers
    file_handler = logging.FileHandler(log_file)
    console_handler = logging.StreamHandler()

    # Set logging levels for handlers
    file_handler.setLevel(logging.DEBUG)
    console_handler.setLevel(logging.INFO)

    # Create formatters and add them to the handlers
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


logger = setup_logging("logs/mining.log")

from django.db.models import F


def main():
    booster = Booster.objects.filter(slug="magnit").first()
    for user_profile in UserProfile.objects.filter(is_mining=True):
        try:
            if not user_profile.mining_was_stopped:
                user_profile.add_tbtc_mining()
            is_active_manager = (
                user_profile.manager_expires
                and timezone.now() < user_profile.manager_expires
            )

            if not is_active_manager and not user_profile.mining_was_stopped:
                if (
                    (
                        user_profile.stop_mining_at1
                        and user_profile.stop_mining_at1 < timezone.now()
                    )
                    or (
                        user_profile.stop_mining_at2
                        and user_profile.stop_mining_at2 < timezone.now()
                    )
                    or (
                        user_profile.stop_mining_at3
                        and user_profile.stop_mining_at3 < timezone.now()
                    )
                ):
                    user_profile.upd_stopper()
                    UserProfile.objects.filter(user_id=user_profile.user_id).update(
                        mining_was_stopped=True,
                        mining_last_stopped=timezone.now(),
                    )
                    try:
                        bot.send_message(
                            user_profile.user_id,
                            """📢 Внимание!
Обнаружены перебои с интернет-соединением. 🔌⚡️
Пожалуйста, откройте приложение и проверьте подключение. 📲✅""",
                        )
                    except Exception:
                        pass
                    continue

            if (
                timezone.now() - user_profile.started_mining_at
            ).total_seconds() > user_profile.mining_period:
                # if user_profile.mining_was_stopped:
                #     UserProfile.objects.filter(user_id=user_profile.user_id).update(
                #         is_mining=False,
                #         battery_balance=0,
                #         mining_period=0,
                #     )
                #     continue
                user_profile.upd_stopper()
                user_profile.recalc_rent()
                user_profile.refresh_from_db()

                farm_consumption = (
                    user_profile.total_farm_consumption
                    - user_profile.rent_farm_consumption_minus
                    + user_profile.rent_farm_consumption_plus
                )
                if user_profile.is_powerbank_active:
                    farm_consumption -= user_profile.powerbank_max_consume

                energy_saved_magnet = 0
                magnit_percent = float(getattr(booster, "n1", 20))
                if user_profile.premium_sub_expires and user_profile.premium_sub_expires > timezone.now():
                    magnit_percent = 24
                if (
                    user_profile.magnit_expires
                    and user_profile.magnit_expires > timezone.now()
                ):
                    energy_saved_magnet = farm_consumption * (magnit_percent / 100)
                    farm_consumption = farm_consumption * (1 - magnit_percent / 100)

                if farm_consumption == 0:
                    farm_consumption == 1

                if farm_consumption > user_profile.kw_wallet:
                    if farm_consumption / 2 > user_profile.kw_wallet:
                        UserProfile.objects.filter(user_id=user_profile.user_id).update(
                            is_mining=False,
                            battery_balance=0,
                            mining_period=0,
                        )
                        continue
                    else:
                        UserProfile.objects.filter(user_id=user_profile.user_id).update(
                            kw_wallet=F("kw_wallet") - farm_consumption / 2,
                            battery_balance=farm_consumption / 2,
                            mining_period=1800,
                            is_mining=True,
                            started_mining_at=timezone.now(),
                            last_tbtc_added=timezone.now(),
                            farm_runtime=F("kw_wallet") / float(1),
                        )
                        add_mining_commission(farm_consumption / 2)
                        MiningStats.objects.update(energy_spent_mining=F("energy_spent_mining") + farm_consumption / 2)

                else:
                    UserProfile.objects.filter(user_id=user_profile.user_id).update(
                        kw_wallet=F("kw_wallet") - farm_consumption,
                        battery_balance=farm_consumption,
                        mining_period=3600,
                        is_mining=True,
                        started_mining_at=timezone.now(),
                        last_tbtc_added=timezone.now(),
                        farm_runtime=F("kw_wallet") / float(1),
                    )
                    add_mining_commission(farm_consumption)
                    MiningStats.objects.update(energy_spent_mining=F("energy_spent_mining") + farm_consumption)
                if user_profile.is_powerbank_active:
                    UserProfile.objects.filter(user_id=user_profile.user_id).update(
                        is_powerbank_active=False,
                        powerbank_activated=timezone.now(),
                    )
                    MiningStats.objects.update(energy_saved_powerbank=F("energy_saved_powerbank") + user_profile.powerbank_max_consume)
                MiningStats.objects.update(energy_saved_magnet=F("energy_saved_magnet") + energy_saved_magnet)
        except Exception:
            logger.exception(f"error mining")
            print(traceback.format_exc())
            user_profile.stop_mining(f"error {traceback.format_exc()}")


if __name__ == "__main__":
    # Run the asynchronous function
    # asyncio.run(main())
    while True:
        try:
            main()
            time.sleep(3)
        except Exception:
            traceback.print_exc()
            logger.exception(f"error")
