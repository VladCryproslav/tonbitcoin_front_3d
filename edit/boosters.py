import time
import traceback
import django, os


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from tasks.models import Booster
from core.models import JarvisEnergyStat, UserProfile, WalletInfo
from core.utils import add_chart_kw
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
    logger = logging.getLogger("log_boost")
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


logger = setup_logging("logs/boost.log")

from django.db import transaction
from django.db.models import F, Q
from django.db.models.functions import Greatest
from django.utils import timezone


while True:
    start_time = time.time()
    try:
        booster = Booster.objects.filter(slug="jarvis").first()
        jarvis_percent = float(getattr(booster, "n1", 100) or 100)
        now = timezone.now()
        
        # Накопление суммы для ChartData (оптимизация: один вызов вместо тысячи)
        total_added_kw = 0.0
        
        # Оптимизация: загружаем только нужные поля
        users_queryset = UserProfile.objects.filter(
            Q(jarvis_expires__gt=now)
            & Q(jarvis_expires__isnull=False)
            & (Q(building_until__lt=now) | Q(building_until__isnull=True))
        ).only(
            'id', 'generation_rate', 'power', 'repair_kit_expires', 
            'repair_kit_power_level', 'ton_wallet', 'premium_sub_expires',
            'has_gold_sbt', 'has_gold_sbt_nft', 'has_silver_sbt', 'has_silver_sbt_nft'
        )
        
        # Оптимизация: используем iterator() вместо .all() для экономии памяти
        # Оптимизация: обрабатываем батчами по 50 пользователей
        BATCH_SIZE = 50
        batch = []
        
        for u in users_queryset.iterator(chunk_size=100):
            try:
                added_kw = float(u.generation_rate) * float(u.power) / 100 / 1800 * jarvis_percent / 100 * u.sbt_get_jarvis()
                
                # Накопление суммы для ChartData
                total_added_kw += added_kw
                
                # Проверяем активность Repair Kit
                is_repair_kit_active = (
                    u.repair_kit_expires and
                    now < u.repair_kit_expires
                )
                
                update_data = {
                    "energy": F("energy") + added_kw,
                }
                
                if is_repair_kit_active and u.repair_kit_power_level is not None:
                    # Repair Kit активен: power вообще не должен снижаться.
                    # На всякий случай поднимаем power до repair_kit_power_level,
                    # если он вдруг оказался ниже (например, из-за старой логики).
                    update_data["power"] = Greatest(
                        F("power"),
                        u.repair_kit_power_level,
                    )
                else:
                    # Обычное снижение power
                    update_data["power"] = F("power") - 1 / 3600 * u.sbt_get_power()
                
                batch.append((u, update_data, added_kw))
                
                # Оптимизация: обрабатываем батчами в отдельных транзакциях
                if len(batch) >= BATCH_SIZE:
                    with transaction.atomic():
                        for user_obj, update_data, added_kw in batch:
                            UserProfile.objects.filter(id=user_obj.id).update(**update_data)
                            WalletInfo.objects.filter(user=user_obj, wallet=user_obj.ton_wallet).update(
                                kw_amount=F("kw_amount") + added_kw
                            )
                    batch = []
                    
            except Exception as e:
                # Оптимизация: обработка ошибок для отдельных записей
                logger.error(f"Error processing user {u.id}: {e}")
                traceback.print_exc()
                continue
        
        # Обработка остатка батча
        if batch:
            with transaction.atomic():
                for user_obj, update_data, added_kw in batch:
                    UserProfile.objects.filter(id=user_obj.id).update(**update_data)
                    WalletInfo.objects.filter(user=user_obj, wallet=user_obj.ton_wallet).update(
                        kw_amount=F("kw_amount") + added_kw
                    )
        
        # Оптимизация: один вызов add_chart_kw вместо тысячи
        if total_added_kw > 0:
            add_chart_kw(total_added_kw)
        
        # Обновление power < 0 и autostart_count остается в одной транзакции
        with transaction.atomic():
            UserProfile.objects.filter(power__lt=0).update(power=0)
            
            logger.info(
                UserProfile.objects.filter(
                    autostart_count__gt=0, overheated_until__lt=now
                ).update(
                    overheated_until=None,
                    tap_count_since_overheat=0,
                    autostart_count=F("autostart_count") - 1,
                )
            )
    except Exception:
        traceback.print_exc()

    elapsed_time = time.time() - start_time
    logger.info(f"upd {elapsed_time}")
    sleep_time = max(2 - elapsed_time, 0)
    time.sleep(sleep_time)
