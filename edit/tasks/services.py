import math
from core.models import HashrateInfo, UserProfile
from tasks.models import Booster, Task, UserReward, UserTask, WheelSlot


# Определяем порядок уровней станций
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
from django.conf import settings
from telebot import types, TeleBot
from django.utils import timezone

bot = TeleBot(settings.BOT_TOKEN, parse_mode="HTML")


def check_subscription(chat_id, user_id):
    try:
        bot.get_chat_member(chat_id, user_id)
        return True
    except Exception as e:
        return False


def check_task_completion(user: UserProfile, task: Task, user_task: UserTask) -> bool:
    if task.condition == "referral_station":
        start_index = STATION_LEVELS.index(task.n2)
        stations_to_filter = STATION_LEVELS[start_index:]
        return UserProfile.objects.filter(
            referrer=user, station_type__in=stations_to_filter
        ).count() >= int(task.n1)
    elif task.condition == "station":
        start_index = STATION_LEVELS.index(task.n1)
        stations_to_filter = STATION_LEVELS[start_index:]
        return user.station_type in stations_to_filter
    elif task.condition == "storage":
        start_index = STATION_LEVELS.index(task.n1)
        return (
            user.station_type == task.n1 and user.storage_level >= int(task.n2)
        ) or (user.station_type in STATION_LEVELS[start_index + 1 :])
    elif task.condition == "generation":
        start_index = STATION_LEVELS.index(task.n1)
        return (
            user.station_type == task.n1 and user.generation_level >= int(task.n2)
        ) or (user.station_type in STATION_LEVELS[start_index + 1 :])
    elif task.condition == "balance_energizer":
        return float(user.energy) >= float(task.n1)
    elif task.condition == "balance_kW":
        return float(user.kw_wallet) >= float(task.n1)
    elif task.condition == "balance_tBTC":
        return float(user.tbtc_wallet) >= float(task.n1)
    elif task.condition == "nft_asic":
        return len(user.nft_string.split(";")) >= int(task.n1)
    elif task.condition == "subscribed_channel":
        return check_subscription(int(task.n2), user.user_id)
    elif task.condition == "chat_message":
        return user_task.completed
    return False


def get_booster_price(user: UserProfile, booster: Booster, fbtc=False):
    station_index = STATION_LEVELS.index(user.station_type) + 1
    return getattr(booster, f"price{station_index}_fbtc" if fbtc else f"price{station_index}")


def get_booster_price_hashrate(mining_speed, booster: Booster, fbtc=False):
    infos = HashrateInfo.objects.order_by("hashrate").values_list("hashrate", flat=True)
    for i, info in enumerate(infos, start=1):
        if mining_speed < info:
            return getattr(booster, f"price{i}_fbtc" if fbtc else f"price{i}")
    return getattr(booster, f"price{len(infos)+1}_fbtc" if fbtc else f"price{len(infos)+1}")

from django.db.models import F

def activate_booster(user: UserProfile, booster: Booster, day_count: int, fbtc=False):
    if booster.slug == "azot":
        is_first_time_today = user.azot_activated is None or (timezone.now() - user.azot_activated > timezone.timedelta(days=1))
        if (
            is_first_time_today
        ):
            UserProfile.objects.filter(id=user.id).update(
                azot_uses_left=1+user.sbt_get_azots(),
                azot_activated=timezone.now(),
                azot_counts=0,
            )
            user.refresh_from_db()

        total_uses_left = user.azot_uses_left
        if user.azot_reward_balance > 0:
            total_uses_left += user.azot_reward_balance

        if total_uses_left > 0:
            # Спочатку використовуємо безкоштовні uses
            if user.azot_uses_left > 0:
                UserProfile.objects.filter(id=user.id).update(
                    overheated_until=None,
                    tap_count_since_overheat=0,
                    azot_uses_left=F("azot_uses_left") - 1,
                )
            else:
                # Якщо немає безкоштовних, використовуємо винагороди
                UserProfile.objects.filter(id=user.id).update(
                    overheated_until=None,
                    tap_count_since_overheat=0,
                    azot_reward_balance=F("azot_reward_balance") - 1,
                )
            return 0
        
        else:
            n1 = int(booster.n1) if booster.n1.isdigit() else 2
            return get_booster_price(user, booster, fbtc) + n1 * user.azot_counts
    elif booster.slug == "jarvis":
        discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
        return math.ceil(get_booster_price(user, booster, fbtc) * day_count * discount)
    elif booster.slug == "cryo":
        discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
        return math.ceil(get_booster_price(user, booster, fbtc) * day_count * discount)
    elif booster.slug == "autostart":
        return get_booster_price(user, booster, fbtc) * day_count
    elif booster.slug == "powerbank":
        n1 = int(booster.n1) if booster.n1.isdigit() else 22
        is_first_time_today = user.powerbank_activated is None or timezone.now() - user.powerbank_activated > timezone.timedelta(hours=n1)
        
        # Розраховуємо загальну кількість доступних powerbank (безкоштовний + винагороди)
        total_uses_left = user.powerbank_uses_left
        if user.powerbank_reward_balance > 0:
            total_uses_left += user.powerbank_reward_balance
            
        if is_first_time_today:
            UserProfile.objects.filter(id=user.id).update(
                powerbank_activated=timezone.now(),
                powerbank_uses_left=1+user.sbt_get_azots(),
            )
            user.refresh_from_db()
            
        if not user.is_powerbank_active and total_uses_left > 0:
            # Спочатку використовуємо безкоштовні uses
            if user.powerbank_uses_left > 0:
                UserProfile.objects.filter(id=user.id).update(
                    is_powerbank_active=True,
                    powerbank_uses_left=F("powerbank_uses_left") - 1,
                )
            else:
                # Якщо немає безкоштовних, використовуємо винагороди
                UserProfile.objects.filter(id=user.id).update(
                    is_powerbank_active=True,
                    powerbank_reward_balance=F("powerbank_reward_balance") - 1,
                )
            return 0
        else:
            return None

    elif booster.slug == "magnit":
        discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
        return math.ceil(
            get_booster_price_hashrate(user.mining_farm_speed, booster, fbtc)
            * day_count
            * discount
        )
    elif booster.slug == "asic_manager":
        discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
        return math.ceil(
            get_booster_price_hashrate(user.mining_farm_speed, booster, fbtc)
            * day_count
            * discount
        )
    elif booster.slug == "electrics":
        discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
        return math.ceil(get_booster_price(user, booster, fbtc) * day_count * discount)
    elif booster.slug == "premium_sub":
        discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
        return math.ceil(get_booster_price(user, booster, fbtc) * day_count * discount)
    elif booster.slug == "repair_kit":
        discount = max(1 - day_count * 0.01, 0.7) if day_count >= 5 else 1
        return math.ceil(get_booster_price(user, booster, fbtc) * day_count * discount)

from django.utils import timezone

def check_booster_time_limit(user: UserProfile, booster_slug: str, days_to_add: int):
    """Перевіряє чи можна додати бустер з урахуванням обмеження в 30 днів"""
    
    current_time = timezone.now()
    total_days = 0
    
    # Перевіряємо активні бустери з терміном дії
    booster_fields = {
        'jarvis': 'jarvis_expires',
        'cryo': 'cryo_expires', 
        'magnit': 'magnit_expires',
        'asic_manager': 'manager_expires',
        'premium_sub': 'premium_sub_expires',
        'repair_kit': 'repair_kit_expires'
    }
    
    if booster_slug in booster_fields:
        field_name = booster_fields[booster_slug]
        current_expiry = getattr(user, field_name)
        
        if current_expiry and current_expiry > current_time:
            current_days = (current_expiry - current_time).days
            if current_days + days_to_add > 30:
                return False, "Too many days of active boosters"
    
    return True, None


from django.utils import timezone
from django.db.models import F

def apply_booster_reward(user: UserProfile, reward: UserReward):
    """Застосовує винагороду бустера до користувача"""
    
    if reward.asset_type == "autostart":
        # Автостартер - додаємо до кількості
        UserProfile.objects.filter(id=user.id).update(
            autostart_count=F("autostart_count") + int(reward.asset_quantity or 1)
        )
        return True, "Автостартер додано до балансу"
        
    elif reward.asset_type == "azot":
        # Жидкий азот - додаємо до кількості
        UserProfile.objects.filter(id=user.id).update(
            azot_reward_balance=F("azot_reward_balance") + int(reward.asset_quantity or 1)
        )
        return True, "Жидкий азот додано до балансу"
        
    elif reward.asset_type == "powerbank":
        # Павер банк - додаємо до балансу винагород
        UserProfile.objects.filter(id=user.id).update(
            powerbank_reward_balance=F("powerbank_reward_balance") + int(reward.asset_quantity or 1)
        )
        return True, "Павер банк додано до балансу"
    
    elif reward.asset_type == "electrics":
        # Блокируем забор приза инженеров, если активна орбитальная (Special), гидро или Singularity
        is_blocked = (
            (user.has_orbital_station and not user.orbital_force_basic) or
            user.has_hydro_station or
            getattr(user, "has_singularity_station", False)
        )
        if is_blocked:
            return False, "Engineers reward cannot be claimed with active orbital (Special), hydro or singularity station"
        
        count = int(reward.asset_quantity or 1)
        if user.engineer_level + count > 49:
            return False, "Max engineer level reached"
        
        # Електрики - додаємо до кількості
        UserProfile.objects.filter(id=user.id).update(
            engineer_level=F("engineer_level") + count,
        )
        
        return True, "Електрики додано до балансу"

    elif reward.asset_type in ["jarvis", "magnit", "asic_manager", "repair_kit"]:
        # Бустери з терміном дії - перевіряємо обмеження
        days_to_add = int(reward.asset_quantity or 1)
        can_add, error_msg = check_booster_time_limit(user, reward.asset_type, days_to_add)
        
        if not can_add:
            return False, error_msg
            
        # Додаємо дні до відповідного бустера
        field_mapping = {
            'jarvis': 'jarvis_expires',
            'magnit': 'magnit_expires', 
            'asic_manager': 'manager_expires',
            'repair_kit': 'repair_kit_expires'
        }
        
        field_name = field_mapping[reward.asset_type]
        current_expiry = getattr(user, field_name)
        current_time = timezone.now()
        
        if current_expiry and current_expiry > current_time:
            # Продовжуємо існуючий бустер
            new_expiry = current_expiry + timezone.timedelta(days=days_to_add)
        else:
            # Активуємо новий бустер
            new_expiry = current_time + timezone.timedelta(days=days_to_add)
        
        update_data = {field_name: new_expiry}
        # Для repair_kit также сохраняем текущий уровень power
        if reward.asset_type == "repair_kit":
            update_data["repair_kit_power_level"] = user.power
            
        UserProfile.objects.filter(id=user.id).update(**update_data)
        return True, f"{reward.asset_type.title()} активовано на {days_to_add} днів"
        
    elif reward.asset_type == "ASIC":
        # ASIC - встановлюємо статус обробки для ручної видачі
        return True, "ASIC буде видано вручну"
        
    return False, "Невідомий тип винагороди"