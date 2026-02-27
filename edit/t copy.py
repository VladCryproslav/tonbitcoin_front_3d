import csv
import logging
import os
import time
import traceback
from datetime import datetime, timedelta

from aiogram.types import User
import django
from django.utils import timezone
from pytonapi import AsyncTonapi

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()
from core.models import (
    AsicsCoefs,
    BoosterRefund,
    BufferTransaction,
    EngineerConfig,
    GenPowerStationConfig,
    NFTDatabase,
    NFTRentalAgreement,
    Notification,
    StationNFTOwner,
    StationRollbackLog,
    TimedUserNFT,
    UserProfile,
    LinkedUserNFT,
    StoragePowerStationConfig,
    GenPowerStationConfig,
    EngineerConfig,
    OrbitalOwner
)

tonapi = AsyncTonapi(
    api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
)
# AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA
# read data from asics.csv


def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,  # Set the minimum logging level for the root logger
        format="%(asctime)s - %(filename)s:%(lineno)d - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Log to the specified file
            logging.StreamHandler(),  # Log to the console
        ],
    )

    # Create a custom logger
    logger = logging.getLogger("my_logger_t")
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


logger = setup_logging("logs/t.log")


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
Common,Asic S1,100,Hour,1,"0,010",2
Common,Asic S3,200,Hour,2,"0,021",4
Rare,Asic S5+,400,Hour,4,"0,042",8
Rare,Asic S7+,1000,Hour,10,"0,104",16
Rare,Asic S9+,2500,Hour,23,"0,260",32
Epic,Asic S11 XP,6000,Hour,52,"0,625",64
Epic,Asic S15 XP,15000,Hour,125,"1,563",128
Epic,Asic S17 XP,40000,Hour,320,"4,167",256
Legendary,Asic S19 XP+,100000,Hour,670,"10,417",512
Legendary,Asic S21 XP+,250000,Hour,1460,"26,042",1024
Mythic,Asic SX Ultra Pro,600000,Hour,3000,"62,500",2048
Special,Asic S10 Maxx,1000,Hour,80,"0,21",32
Special,Asic S30 Maxx,2000,Hour,160,"0,42",64
Special,Asic S50 Maxx,2800,Hour,224,"0,63",128
Special,Asic S70 Maxx,5000,Hour,400,"1,04",128
Special,Asic S90 Maxx,7500,Hour,480,"1,67",256
"""

asics_data = parse_csv_to_dicts(csv_data)

from asgiref.sync import async_to_sync


async def get_trans(addr):
    return await tonapi.blockchain.get_account_transactions(account_id=addr, limit=100)


async def get_nfts(addr, i):
    return await tonapi.nft.get_items_by_collection_address(
        addr,
        limit=1000,
        offset=i * 1000,
    )
    # EQDJURRy7jc_GutdLdEvxfXL9D0wzByfDiOtLwA0bqniBYJe
    # EQAxJtx_PbO2kB63nejVSjCNfe1ROW0E1-vLIYxItTayW76t


from django.db import transaction
from django.db.models import F
from pytonapi.exceptions import TONAPIError
from django.core.cache import cache


def process_nft_rentals():
    """
    Process active NFT rentals and update user profiles accordingly.
    """
    logger.info("Processing NFT rentals...")
    now = timezone.now()

    # Fetch active rental agreements
    active_rentals = NFTRentalAgreement.objects.filter(end_date__gte=now)

    for rental in active_rentals:
        try:
            owner = rental.owner
            renter = rental.renter

            # Exclude rented NFT from owner's mining calculations
            if rental.nft in owner.nft_string.split(";"):
                owner_nfts = owner.nft_string.split(";")
                owner_nfts.remove(rental.nft)
                owner.nft_string = ";".join(owner_nfts)
                owner.nft_count -= 1
                owner.save()
                logger.info(
                    f"Excluded rented NFT {rental.nft} from owner {owner.user_id}"
                )

            # Ensure renter's profile reflects the rented NFT
            if renter:
                renter_nfts = renter.nft_string.split(";") if renter.nft_string else []
                if rental.nft not in renter_nfts:
                    renter_nfts.append(rental.nft)
                    renter.nft_string = ";".join(renter_nfts)
                    renter.nft_count += 1
                    renter.save()
                    logger.info(
                        f"Added rented NFT {rental.nft} to renter {renter.user_id}"
                    )

        except Exception:
            logger.exception(f"Error processing rental for NFT {rental.nft}")


def main():
    transactions = async_to_sync(get_trans)(
        "UQA1yfxD2yVTu_1QMycifyLMOhJoY_BiJBktI_dAeFjYHLid"
    )

    logger.info("")
    logger.info("print kw")

    for tx in transactions.transactions:
        try:
            buffer_tx = BufferTransaction.objects.get(tx_hash=tx.hash)
        except BufferTransaction.DoesNotExist:
            if tx.in_msg.decoded_body is None:
                continue
            sender = tx.in_msg.decoded_body.get("sender")
            amount = tx.in_msg.decoded_body.get("amount")
            if sender is None:
                continue
            if (
                tx.in_msg.source.address.root
                != "0:209a346dc1b4b4115593b0dfa9a33d0c2435115499033a99b788fa5924426e1c"
            ):
                continue
            
            if tx.utime < 1757425500:
                logger.info(f" | !! skip trans {sender} {amount} {tx.utime} {datetime.utcfromtimestamp(tx.utime)}")
                continue
            
            logger.info(f" | !! valid trans {sender} {amount} {tx.utime} {datetime.utcfromtimestamp(tx.utime)}")
            # logger.info(tx)
            with transaction.atomic():
                user = (
                    UserProfile.objects.select_for_update()
                    .filter(ton_wallet=sender)
                    .first()
                )
                if user is None:
                    continue
                logger.info(
                    f"{datetime.now()} | !!! found trans {user.user_id} +{(float(amount) / 1000000000)} kw"
                )
                BufferTransaction.objects.create(
                    tx_hash=tx.hash, address=sender, success=True
                )
                logger.info(
                    f"{datetime.now()} | USER {user.user_id} BALANCE BEFORE: {user.kw_wallet}"
                )
                UserProfile.objects.select_for_update().filter(
                    ton_wallet=sender
                ).update(kw_wallet=F("kw_wallet") + (float(amount) / 1000000000))
            user = UserProfile.objects.filter(ton_wallet=sender).first()
            logger.info(
                f"{datetime.now()} | USER {user.user_id} BALANCE AFTER: {user.kw_wallet}"
            )
        except Exception:
            logger.exception("trans error")

    time.sleep(1)

    transactions = async_to_sync(get_trans)(
        "UQB0ukWTZXHQhlhztL91277hD8xbFFKXiHVvSBNw-gcBKHfO"
    )

    logger.info("")
    logger.info("print tbtc")

    for tx in transactions.transactions:
        try:
            buffer_tx = BufferTransaction.objects.get(tx_hash=tx.hash)
        except BufferTransaction.DoesNotExist:
            if tx.in_msg.decoded_body is None:
                continue
            sender = tx.in_msg.decoded_body.get("sender")
            amount = tx.in_msg.decoded_body.get("amount")
            if sender is None:
                continue
            if (
                tx.in_msg.source.address.root
                != "0:c97a940cc829deea077a4bde919e708aa839607434c00340535dcbb94047cc28"
            ):
                continue
            
            if tx.utime < 1757425500:
                logger.info(f" | !! skip trans {sender} {amount} {tx.utime} {datetime.utcfromtimestamp(tx.utime)}")
                continue
            
            logger.info(f"{datetime.now()} | !! valid trans {sender} {amount}  {tx.utime} {datetime.utcfromtimestamp(tx.utime)}")
            # logger.info(tx)
            
            with transaction.atomic():
                user = (
                    UserProfile.objects.select_for_update()
                    .filter(ton_wallet=sender)
                    .first()
                )

                if user is None:
                    continue
                logger.info(
                    f"{datetime.now()} | !!! found trans {user.user_id} +{float(amount)/10000} tbtc"
                )
                BufferTransaction.objects.create(
                    tx_hash=tx.hash, address=sender, success=True
                )
                logger.info(
                    f"{datetime.now()} | USER {user.user_id} BALANCE BEFORE: {user.tbtc_wallet}"
                )
                UserProfile.objects.select_for_update().filter(
                    ton_wallet=sender
                ).update(tbtc_wallet=F("tbtc_wallet") + (float(amount) / 10000))
            user = UserProfile.objects.filter(ton_wallet=sender).first()
            logger.info(
                f"{datetime.now()} | USER {user.user_id} BALANCE AFTER: {user.tbtc_wallet}"
            )

        except Exception:
            logger.exception("trans error")


from pytonapi.schema.nft import NftItem

from tasks.models import Booster
from tasks.services import get_booster_price_hashrate


async def get_nft_owner_by_address(nft_address: str):
    """
    Получить текущего владельца NFT по адресу через прямой запрос к TON API.
    Используется для проверки перед отключением hydro/orbital — отключаем только
    если владелец действительно сменился (не полагаемся только на список по коллекции).

    Returns:
        str: адрес владельца (owner.address.root) или None при ошибке/ненайденном NFT.
    """
    if not nft_address or not nft_address.strip():
        return None
    try:
        item = await tonapi.nft.get_item_by_address(nft_address.strip())
        if item and getattr(item, "owner", None) and getattr(item.owner, "address", None):
            return getattr(item.owner.address, "root", None) or str(item.owner.address)
        return None
    except Exception as e:
        logger.warning(f"get_nft_owner_by_address({nft_address[:20]}...): {e}")
        return None


def get_nfts_with_retry(addr, page, max_retries=3, delay=1):
    """
    Получить NFT с повторными попытками при ошибке.
    
    Args:
        addr: Адрес коллекции
        page: Номер страницы
        max_retries: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
    
    Returns:
        Результат запроса или None при неудаче
    """
    for attempt in range(max_retries):
        try:
            if attempt > 0:  # Не задерживаем первую попытку
                time.sleep(0.5)  # 500ms задержка между повторными запросами для rate limiting
            result = async_to_sync(get_nfts)(addr, page)
            return result
        except (TONAPIError, Exception) as e:
            if attempt == max_retries - 1:
                logger.error(
                    f"Failed to fetch NFTs page {page} after {max_retries} attempts: {e}"
                )
                return None
            wait_time = delay * (2 ** attempt)  # Экспоненциальная задержка: 1s, 2s, 4s
            logger.warning(
                f"Error fetching NFTs page {page}, attempt {attempt + 1}/{max_retries}: {e}. "
                f"Retrying in {wait_time}s..."
            )
            time.sleep(wait_time)
    return None


def is_data_complete(all_nfts, collection_addr, failed_pages=None):
    """
    Проверить полноту данных NFT.
    
    Args:
        all_nfts: Список полученных NFT
        collection_addr: Адрес коллекции
        failed_pages: Список страниц, которые не удалось получить (опционально)
    
    Returns:
        True если данные полные, False если неполные
    """
    # Получить ожидаемое количество из кэша
    cache_key = f"expected_nft_count_{collection_addr}"
    expected_count = cache.get(cache_key)
    
    if expected_count is None:
        # Если нет кэша (первый запуск), проверяем на наличие ошибок
        if failed_pages and len(failed_pages) > 0:
            logger.warning(
                f"No cached NFT count for {collection_addr}, but {len(failed_pages)} pages failed. "
                f"Assuming data is incomplete."
            )
            return False
        
        # Первый запуск без ошибок - считаем данные полными
        logger.info(f"No cached NFT count for {collection_addr}, assuming data is complete (first run)")
        return True
    
    # Проверяем, что получено не менее 90% ожидаемого количества
    threshold = expected_count * 0.9
    actual_count = len(all_nfts)
    
    if actual_count < threshold:
        logger.warning(
            f"API returned incomplete data: {actual_count}/{expected_count} "
            f"({actual_count/expected_count*100:.1f}%)"
        )
        return False
    
    logger.info(
        f"Data completeness check passed: {actual_count}/{expected_count} "
        f"({actual_count/expected_count*100:.1f}%)"
    )
    return True


def save_expected_nft_count(collection_addr, count):
    """
    Сохранить ожидаемое количество NFT в кэш.
    
    Args:
        collection_addr: Адрес коллекции
        count: Количество NFT
    """
    cache_key = f"expected_nft_count_{collection_addr}"
    cache.set(cache_key, count, timeout=86400)  # 24 часа
    logger.info(f"Saved expected NFT count for {collection_addr}: {count}")


def main_mint():
    COLLECTION = "EQB-pBhnWEYPbIu25uM1Yp5MqGFjQ-8Jes5CT2Dr-OVd705u"

    users = {}
    all_nfts: list[NftItem] = []
    PAGES = 2
    for collection_addr in [
        COLLECTION,
    ]:
        i = 0
        failed_pages = []
        while True:
            # Fetch pages in batch
            pages = list(range(i, i + PAGES))
            results = []
            
            for page in pages:
                result = get_nfts_with_retry(collection_addr, page)
                if result is None:
                    failed_pages.append(page)
                    logger.error(f"Failed to fetch page {page} after all retries")
                else:
                    results.append(result)
                
                # Rate limiting: минимум 1 секунда между запросами для снижения нагрузки на API
                if page != pages[-1]:  # Не задерживаем после последнего запроса
                    time.sleep(1)
            
            # Если все страницы не удалось получить, прерываем
            if not results:
                logger.error(f"Failed to fetch any pages starting from {i}, aborting")
                break
            
            has_short_page = False
            for data in results:
                if data is not None:
                    all_nfts.extend(data.nft_items)
                    logging.info(f"{len(data.nft_items)}")
                    if len(data.nft_items) < 1000:
                        has_short_page = True
            
            # Если были ошибки, но получили хотя бы часть данных, продолжаем
            if failed_pages:
                logger.warning(f"Some pages failed: {failed_pages}, but continuing with available data")
            
            if has_short_page:
                break
            i += PAGES

    logging.info(f"FINAL {len(all_nfts)}")

    # Флаг полноты данных - используется для принятия решения об откате
    # Данные полные ТОЛЬКО если: is_data_complete вернул True И не было failed_pages
    data_is_complete = is_data_complete(all_nfts, collection_addr, failed_pages) and len(failed_pages) == 0

    # Сохранять ожидаемое количество ТОЛЬКО при полных данных (иначе занижаем порог и возможны ложные откаты)
    if len(all_nfts) > 0 and data_is_complete:
        save_expected_nft_count(collection_addr, len(all_nfts))

    # Флаг: использовали ли кэш (для правильной обработки hydro/orbital owners)
    used_cache = False

    # Проверка на полноту данных
    if not is_data_complete(all_nfts, collection_addr, failed_pages):
        logger.error(
            f"API returned incomplete data for collection {collection_addr}. "
            f"Received {len(all_nfts)} NFTs. Skipping station check to prevent mass rollback."
        )
        # Попытка использовать кэш из предыдущего успешного запроса
        cache_key = f"last_successful_nfts_{collection_addr}"
        cached_nfts = cache.get(cache_key)
        if cached_nfts:
            logger.info(f"Using cached NFT data from previous successful request")
            all_nfts = cached_nfts
            used_cache = True  # Отмечаем, что использовали кэш
            # Пересоздаем users dict из кэшированных данных
            users = {}
            for nft in all_nfts:
                address = nft.owner.address.root
                nft_address = nft.address.root
                users.setdefault(address, {"mint_string": []})
                users[address]["mint_string"].append(nft_address)
        else:
            logger.error("No cached data available, aborting to prevent mass rollback")
            return  # НЕ проверяем станции при неполных данных

    # Сохранить успешные данные в кэш
    if len(all_nfts) > 0:
        cache_key = f"last_successful_nfts_{collection_addr}"
        cache.set(cache_key, all_nfts, timeout=600)  # 10 минут
        logger.info(f"Cached {len(all_nfts)} NFTs for fallback use")

    if len(all_nfts) < 1:
        logging.info(f"BREAK")
        return

    nfts_info: dict[str, NftItem] = {}
    hydro_owners = dict()
    orbital_owners = dict()
    
    # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: При использовании кэша НЕ строим hydro_owners/orbital_owners из кэша
    # Вместо этого используем данные из БД, чтобы избежать ложных откатов из-за устаревшего/неполного кэша
    # При использовании кэша data_is_complete = False, поэтому отключения не произойдет
    # Но мы все равно строим словари для консистентности кода
    if used_cache:
        logger.info("Using database data for hydro/orbital owners (cache was used, data_is_complete=False, no rollbacks will occur)")
        
        # Получаем hydro owners из LinkedUserNFT
        # НЕ проверяем кэш, так как он может быть неполным/устаревшим
        # При использовании кэша data_is_complete = False, поэтому отключения не произойдет в любом случае
        hydro_linked = LinkedUserNFT.objects.select_related("user").filter(
            nft_address__in=[nft.address.root for nft in all_nfts 
                            if nft.metadata and nft.metadata.get("name", "").split("(")[0].strip() == "Hydroelectric Power Station"]
        )
        for linked in hydro_linked:
            if linked.user:
                hydro_owners[linked.user.user_id] = {"nft_address": linked.nft_address}
        
        # Получаем orbital owners из OrbitalOwner
        orbital_db = OrbitalOwner.objects.select_related("user").all()
        for orbital in orbital_db:
            if orbital.user:
                orbital_owners[orbital.user.user_id] = {"nft_address": orbital.nft_address}
        
        logger.info(f"Loaded from DB: {len(hydro_owners)} hydro owners, {len(orbital_owners)} orbital owners")
    else:
        # При полных данных строим из API ответа (существующий код)
        # Process default NFTs
        for nft in all_nfts:
            address = nft.owner.address.root
            nft_address = nft.address.root
            sale = nft.sale
            meta: dict = nft.metadata
            name = meta.get("name")
            
            name = name.split("(")[0].strip()
            
            if name in ["Hydroelectric Power Station", "Orbital Power Station"]:
                full_name = meta.get("name")
                linked = LinkedUserNFT.objects.select_related("user").filter(nft_address=nft_address).first()
                    
                if linked and (
                    linked.wallet != address or # owner_changed
                    (linked.user and linked.user.ton_wallet and linked.user.ton_wallet != linked.wallet) or # user_changed_wallet
                    (linked.user and UserProfile.objects.filter(ton_wallet=linked.wallet).exclude(id=linked.user.id).exists()) # someone_else_has_wallet
                ):
                    print(f"linked {linked} owner changed {linked.wallet} != {address} or user changed {linked.user} != {linked.wallet}")
                    linked.delete()
                    linked = None

                
                if linked is None:
                    linked = LinkedUserNFT.objects.create(
                        user=UserProfile.objects.filter(ton_wallet=address).first(),
                        wallet=address,
                        nft_address=nft_address,
                    )
                    
                user = linked.user
                if user is None:
                    user = UserProfile.objects.filter(ton_wallet=address).first()
                    if user:
                        LinkedUserNFT.objects.filter(wallet=address).update(
                            user=user
                        )
                    continue
                
                # JARVIS
                if name == "Hydroelectric Power Station":
                    hydro_owners[user.user_id] = {"nft_address": nft_address}
                if name == "Orbital Power Station":
                    if not OrbitalOwner.objects.filter(nft_address=nft_address).exists():
                        # if this is new orbital station, assign it to the first owner
                        OrbitalOwner.objects.create(
                            user=user,
                            nft_address=nft_address
                        )
                    orbital_owners[user.user_id] = {"nft_address": nft_address}
                continue

        users.setdefault(
            address,
            {
                "mint_string": [],
            },
        )
        nfts_info.setdefault(
            nft_address,
            {
                "nft": nft,
            },
        )

        users[address]["mint_string"].append(nft_address)

    # orbital_owners[558867002] = {"nft_address": "0:da83eac8d47b0945825c5d71fb6e9d9fa0e0aaf10fc186747a59ba80424ed6a0"}
    # orbital_owners[5141702856] = {"nft_address": "0:da83eac8d47b0945825c5d71fb6e9d9fa0e0aaf10fc186747a59ba80424ed6a0"}
    # print(hydro_owners)
    
    # print("hello2")
    # Отключаем hydro только при полных данных API (иначе возможны ложные откаты)
    if data_is_complete:
        # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: убедиться, что hydro_owners не пустой
        # Если пустой при полных данных, это может означать проблему с данными
        if len(hydro_owners) == 0:
            logger.warning(
                "hydro_owners is empty despite data_is_complete=True, "
                "skipping disconnect to prevent false rollback"
            )
        else:
            for u in UserProfile.objects.filter(
                has_hydro_station=True,
                has_orbital_station=False,
            ).exclude(user_id__in=list(hydro_owners.keys())):
                try:
                    # Обновляем объект для получения актуальных значений
                    u.refresh_from_db()

                    # КРИТИЧНО: проверяем владельца NFT прямым запросом — отключаем только при реальной смене владельца
                    if u.current_station_nft and u.ton_wallet:
                        current_owner = async_to_sync(get_nft_owner_by_address)(u.current_station_nft)
                        time.sleep(0.5)  # пауза между прямыми запросами к API для rate limiting
                        if current_owner is None:
                            logger.warning(
                                f"Skipping hydro disconnect for user_id={u.user_id}: "
                                "direct NFT owner check failed (API error?), keeping station"
                            )
                            continue
                        if (current_owner or "").strip() == (u.ton_wallet or "").strip():
                            logger.warning(
                                f"Skipping hydro disconnect for user_id={u.user_id}: "
                                "NFT still owned by user (API list was incomplete?), keeping station"
                            )
                            continue

                    with transaction.atomic():
                        # Логируем баланс энергии на момент отката hydro станции
                        StationRollbackLog.objects.create(
                            user=u,
                            from_station=u.station_type,
                            generation_level=u.generation_level,
                            storage_level=u.storage_level,
                            engineer_level=u.engineer_level,
                            energy=u.energy,
                            nft_address=(
                                u.current_station_nft if u.current_station_nft else ""
                            ),
                        )

                        UserProfile.objects.filter(user_id=u.user_id).update(
                            current_station_nft="",
                            has_hydro_station=False,
                            energy=F("hydro_prev_energy"),
                            power=F("hydro_prev_power"),
                            hydro_prev_power=F("power"),
                            station_type=F("hydro_prev_station_type"),
                            storage_level=F("hydro_prev_storage_level"),
                            generation_level=F("hydro_prev_generation_level"),
                            engineer_level=F("hydro_prev_engineer_level"),
                            storage=0,
                            storage_limit=StoragePowerStationConfig.objects.filter(
                                station_type=u.hydro_prev_station_type,
                                level=u.hydro_prev_storage_level,
                            )
                            .first()
                            .storage_limit,
                            generation_rate=GenPowerStationConfig.objects.filter(
                                station_type=u.hydro_prev_station_type,
                                level=u.hydro_prev_generation_level,
                            )
                            .first()
                            .generation_rate,
                            kw_per_tap=EngineerConfig.objects.get(
                                level=u.hydro_prev_engineer_level
                            ).tap_power,
                        )
                        # u.check_storage_generation()
                except Exception:
                    # traceback.print_exc()
                    print("user_id", u.user_id)
                    continue
    else:
        logger.info("Skipping hydro disconnect: data_is_complete=False")
    
    for u in UserProfile.objects.filter(
        user_id__in=list(hydro_owners.keys())
    ).exclude(has_hydro_station=True).exclude(has_orbital_station=True):
        with transaction.atomic():
            UserProfile.objects.filter(user_id=u.user_id).update(
                current_station_nft=hydro_owners[u.user_id]["nft_address"],
                has_hydro_station=True,
                hydro_prev_energy=F("energy"),
                power=F("hydro_prev_power"),
                hydro_prev_power=F("power"),
                hydro_prev_station_type=F("station_type"),
                hydro_prev_storage_level=F("storage_level"),
                hydro_prev_generation_level=F("generation_level"),
                hydro_prev_engineer_level=F("engineer_level"),
                station_type="Nuclear power plant",
                storage_level=3,
                generation_level=3,
                engineer_level=30,
                energy=0,
                storage=1000,
                storage_limit=1000,
            generation_rate=250,
            kw_per_tap=EngineerConfig.objects.get(
                level=30
            ).tap_power
            )
            
            # u.check_storage_generation()

    # Отключаем orbital только при полных данных API (иначе возможны ложные откаты)
    if data_is_complete:
        # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: убедиться, что orbital_owners не пустой
        # Если пустой при полных данных, это может означать проблему с данными
        if len(orbital_owners) == 0:
            logger.warning(
                "orbital_owners is empty despite data_is_complete=True, "
                "skipping disconnect to prevent false rollback"
            )
        else:
            for u in UserProfile.objects.filter(
                has_orbital_station=True,
                has_hydro_station=False,
            ).exclude(user_id__in=list(orbital_owners.keys())):
                try:
                    # Обновляем объект для получения актуальных значений
                    u.refresh_from_db()

                    # КРИТИЧНО: проверяем владельца NFT прямым запросом — отключаем только при реальной смене владельца
                    if u.current_station_nft and u.ton_wallet:
                        current_owner = async_to_sync(get_nft_owner_by_address)(u.current_station_nft)
                        time.sleep(0.5)  # пауза между прямыми запросами к API для rate limiting
                        if current_owner is None:
                            logger.warning(
                                f"Skipping orbital disconnect for user_id={u.user_id}: "
                                "direct NFT owner check failed (API error?), keeping station"
                            )
                            continue
                        if (current_owner or "").strip() == (u.ton_wallet or "").strip():
                            logger.warning(
                                f"Skipping orbital disconnect for user_id={u.user_id}: "
                                "NFT still owned by user (API list was incomplete?), keeping station"
                            )
                            continue

                    with transaction.atomic():
                        # Логируем баланс энергии на момент отката orbital станции
                        StationRollbackLog.objects.create(
                            user=u,
                            from_station=u.station_type,
                            generation_level=u.generation_level,
                            storage_level=u.storage_level,
                            engineer_level=u.engineer_level,
                            energy=u.energy,
                            nft_address=(
                                u.current_station_nft if u.current_station_nft else ""
                            ),
                        )

                        UserProfile.objects.filter(user_id=u.user_id).update(
                            current_station_nft="",
                            orbital_force_basic=False,
                            has_orbital_station=False,
                            energy=F("hydro_prev_energy")
                            + (
                                F("energy")
                                if (
                                    u.orbital_first_owner and not u.orbital_is_blue
                                )
                                else 0
                            ),
                            power=F("hydro_prev_power"),
                            hydro_prev_power=F("power"),
                            station_type=F("hydro_prev_station_type"),
                            storage_level=F("hydro_prev_storage_level"),
                            generation_level=F("hydro_prev_generation_level"),
                            engineer_level=F("hydro_prev_engineer_level"),
                            storage=0,
                            storage_limit=StoragePowerStationConfig.objects.filter(
                                station_type=u.hydro_prev_station_type,
                                level=u.hydro_prev_storage_level,
                            )
                            .first()
                            .storage_limit,
                            generation_rate=GenPowerStationConfig.objects.filter(
                                station_type=u.hydro_prev_station_type,
                                level=u.hydro_prev_generation_level,
                            )
                            .first()
                            .generation_rate,
                            kw_per_tap=EngineerConfig.objects.get(
                                level=u.hydro_prev_engineer_level
                            ).tap_power,
                        )
                        # u.check_storage_generation()
                except Exception:
                    # traceback.print_exc()
                    print("user_id", u.user_id)
                    continue
    else:
        logger.info("Skipping orbital disconnect: data_is_complete=False")
    
    for u in UserProfile.objects.filter(
        user_id__in=list(orbital_owners.keys())
    ).exclude(has_orbital_station=True).exclude(has_hydro_station=True):
        with transaction.atomic():
            UserProfile.objects.filter(user_id=u.user_id).update(
                current_station_nft=orbital_owners[u.user_id]["nft_address"],
                orbital_force_basic=False,
                has_orbital_station=True,
                hydro_prev_energy=F("energy"),
                hydro_prev_station_type=F("station_type"),
                hydro_prev_storage_level=F("storage_level"),
                hydro_prev_generation_level=F("generation_level"),
                hydro_prev_engineer_level=F("engineer_level"),
                station_type="Dyson Sphere",
                storage_level=3,
                generation_level=3,
                engineer_level=45,
                energy=0,
                storage=2320,
                storage_limit=2320,
            generation_rate=290 if u.orbital_first_owner else 580,
            kw_per_tap=EngineerConfig.objects.get(
                level=45
            ).tap_power
            )

    # КРИТИЧЕСКАЯ ЗАЩИТА: Проверка полноты данных перед проверкой станций
    if not is_data_complete(all_nfts, collection_addr, failed_pages):
        logger.error(
            "CRITICAL: API data incomplete before station check. "
            "Skipping station check to prevent mass rollback."
        )
        # Попытка использовать кэш
        cache_key = f"last_successful_nfts_{collection_addr}"
        cached_nfts = cache.get(cache_key)
        if cached_nfts and len(cached_nfts) > len(all_nfts) * 1.1:
            logger.warning("Using cached data as it's more complete")
            all_nfts = cached_nfts
            # Пересоздаем users dict
            users = {}
            nfts_info = {}
            for nft in all_nfts:
                address = nft.owner.address.root
                nft_address = nft.address.root
                users.setdefault(address, {"mint_string": []})
                users[address]["mint_string"].append(nft_address)
                nfts_info[nft_address] = {"nft": nft}
            # Обновляем флаг полноты данных - кэш считается полными данными
            data_is_complete = True
            logger.info("Using cached data, marking as complete for station check")
        else:
            logger.error("No valid cached data available. ABORTING station check.")
            return

    logging.info("")
    logging.info("checking nfts")
    for station_nft in StationNFTOwner.objects.filter(nft__isnull=False).exclude(
        nft=""
    ):
        try:
            user = users.get(station_nft.wallet or "")
            if user is None:
                # КРИТИЧЕСКАЯ ПРОВЕРКА: Если пользователь не найден, это может быть из-за ошибки API
                # Проверяем, не является ли это массовой проблемой
                missing_users_count = StationNFTOwner.objects.filter(
                    nft__isnull=False
                ).exclude(nft="").exclude(wallet__in=users.keys()).count()
                
                if missing_users_count > 50:  # Порог массовой проблемы
                    logger.error(
                        f"CRITICAL: {missing_users_count} station owners not found in users dict. "
                        f"This indicates API data incompleteness. ABORTING station check."
                    )
                    break  # Прерываем проверку, чтобы не откатить все станции
                
                # ✅ ИЗМЕНЕНИЕ: Если кошелек не найден - НЕ откатывать, а пропустить
                # Это может быть из-за неполных данных API, а не реального отсутствия NFT
                logger.warning(
                    f"Station NFT {station_nft.nft} owner wallet {station_nft.wallet} not found in users dict. "
                    f"Skipping to prevent false rollback. Data complete: {data_is_complete}"
                )
                continue  # ✅ Пропускаем, НЕ откатываем
            
            mint_string = ";".join(user["mint_string"])
            
            # Дополнительная проверка: убедиться, что nft_info содержит этот NFT
            if station_nft.nft not in nfts_info:
                logger.warning(
                    f"Station NFT {station_nft.nft} not found in nfts_info. "
                    f"This may indicate incomplete API data. Skipping this station."
                )
                continue
            
            if (
                station_nft.nft not in mint_string
                or nfts_info[station_nft.nft]["nft"].sale is not None
            ):
                # ✅ ИЗМЕНЕНИЕ: Откатывать ТОЛЬКО если данные полные
                if not data_is_complete:
                    logger.warning(
                        f"Station NFT {station_nft.nft} appears to be missing, but data is incomplete. "
                        f"Skipping rollback to prevent false positive. Will check again on next run."
                    )
                    continue  # Пропускаем откат при неполных данных
                
                # Данные полные - можно безопасно откатывать
                Notification.objects.create(
                    user=station_nft.user, notif_type="nft_not_found"
                )
                station_nft.user.reset_station()
                logger.info(
                    f"Rolled back station for user {station_nft.user.user_id}: "
                    f"NFT {station_nft.nft} not found in mint_string or on sale"
                )
                logger.info(f"station_nft not in mint string {station_nft.nft} | {mint_string}")
                logger.info(station_nft)

        except KeyError as e:
            logger.error(f"KeyError in station check: {e}. NFT may be missing from nfts_info.")
            continue
        except Exception:
            logger.exception("err profile")

    # for profile in UserProfile.objects.all():
    #     try:
    #         user = users.get(profile.ton_wallet or "")
    #         if user is None:
    #             new_mint_string = ""
    #         else:
    #             new_mint_string = ";".join(user["mint_string"])
    #         if profile.mint_string != new_mint_string:
    #             logger.info(
    #                 f"different mint nft string {profile.mint_string} -> {new_mint_string}"
    #             )

    #             if user is None:
    #                 user = {
    #                     "mint_string": [],
    #                 }
    #             logger.info(profile)

    #             station_nft = (
    #                 StationNFTOwner.objects.filter(user=profile).first()
    #             )
    #             if station_nft and station_nft.:
    #                 profile.reset_station()

    #             # if (
    #             #     profile.current_mint
    #             #     and profile.current_mint in profile.mint_string
    #             #     and profile.current_mint not in new_mint_string
    #             # ):
    #             #     profile.reset_station()

    #             UserProfile.objects.filter(user_id=profile.user_id).update(
    #                 mint_string=new_mint_string,
    #             )

    #     except Exception:
    #         logger.exception("err profile")

def main_boosters():
    OFFICIAL_COLLECTION = "EQDJURRy7jc_GutdLdEvxfXL9D0wzByfDiOtLwA0bqniBYJe"
    PRELAUNCH_COLLECTION = "EQAxJtx_PbO2kB63nejVSjCNfe1ROW0E1-vLIYxItTayW76t"

    users = {}
    all_nfts = []
    for pages, collection_addr in ((4,OFFICIAL_COLLECTION), (1, PRELAUNCH_COLLECTION)):
        i = 0
        while True:
            pages = list(range(i, i + pages))
            # Последовательные запросы с задержками для rate limiting
            results = []
            for page in pages:
                results.append(async_to_sync(get_nfts)(collection_addr, page))
                if page != pages[-1]:  # Задержка между запросами, кроме последнего
                    time.sleep(0.5)

            has_short_page = False
            for data in results:
                all_nfts.extend(data.nft_items)
                logging.info(f"{len(data.nft_items)}")
                if len(data.nft_items) < 1000:
                    has_short_page = True

            if has_short_page:
                break
            i += pages
    logging.info(f"FINAL {len(all_nfts)}")

    if len(all_nfts) < 3200:
        logging.info(f"BREAK")
        return

    prelaunch_coef_obj = AsicsCoefs.objects.filter(address="prelaunch_coef").first()
    prelaunch_coef = prelaunch_coef_obj.coef if prelaunch_coef_obj else 1
    standart_coef_obj = AsicsCoefs.objects.filter(address="standart_coef").first()
    standart_coef = standart_coef_obj.coef if standart_coef_obj else 0.5
    magnit_booster = Booster.objects.filter(slug="magnit").first()
    manager_booster = Booster.objects.filter(slug="asic_manager").first()

    # Process active NFT rentals
    # now = timezone.now()
    # active_rentals = NFTRentalAgreement.objects.filter(end_date__gte=now)
    # for rental in active_rentals:
    #     renter = rental.renter
    #     if renter:
    #         stats = asics_data.get(rental.nft, None)
    #         if stats:
    #             users.setdefault(
    #                 renter.ton_wallet,
    #                 {
    #                     "nft_count": 0,
    #                     "mining_power": 0,
    #                     "tbtc_speed": 0,
    #                     "consumption_kw": 0,
    #                     "energy_left": 0,
    #                     "nft_string": [],
    #                     "powerbank_max_consume": 0,
    #                 },
    #             )
    #             users[renter.ton_wallet]["nft_count"] += 1
    #             users[renter.ton_wallet]["nft_string"].append(rental.nft)
    #             users[renter.ton_wallet]["mining_power"] += stats["hash_rate"]
    #             users[renter.ton_wallet]["tbtc_speed"] += stats["mining_speed_tbtc"]
    #             users[renter.ton_wallet]["consumption_kw"] += stats["consumption_kw"]

    # Process default NFTs
    sbt_owners = dict()
    jarvis_owners = dict()
    cryo_owners = dict()
    asic_owners = dict()
    magnit_owners = dict()
    repair_kit_owners = dict()
    
    infinite_date = timezone.make_aware(datetime(2100, 1, 1, 0, 0, 0))

    for nft in all_nfts:
        address = nft.owner.address.root
        collection_address = nft.collection.address.root
        nft_address = nft.address.root
        meta: dict = nft.metadata
        name = meta.get("name")
        if not name:
            continue

        name = name.split("(")[0].strip()


        if name in ["Jarvis Bot", "Cryochamber", "ASIC Manager", "Magnetic ring", "Repair Kit"]:
            full_name = meta.get("name")
            linked = LinkedUserNFT.objects.filter(nft_address=nft_address).first()
            
            if linked and (
                linked.wallet != address or # owner_changed
                (linked.user and linked.user.ton_wallet and linked.user.ton_wallet != linked.wallet) or # user_changed_wallet
                (linked.user and UserProfile.objects.filter(ton_wallet=linked.wallet).exclude(id=linked.user.id).exists()) # someone_else_has_wallet
            ):
                print(f"linked {linked} owner changed {linked.wallet} != {address} or user changed {linked.user} != {linked.wallet}")
                linked.delete()
                linked = None
            
            if linked is None:
                linked = LinkedUserNFT.objects.create(
                    user=UserProfile.objects.filter(ton_wallet=address).first(),
                    wallet=address,
                    nft_address=nft_address,
                )
                
                
            user = linked.user
            if user is None:
                user = UserProfile.objects.filter(ton_wallet=address).first()
                if user:
                    LinkedUserNFT.objects.filter(wallet=address).update(
                        user=user
                    )
                continue
            
            
            print()
            if TimedUserNFT.objects.filter(
                    user__user_id=user.user_id, nft_address=nft_address, block_until__gt=timezone.now()
                ).exists():
                continue
            
            # JARVIS
            if name == "Jarvis Bot":
                print(user.user_id, nft_address)
                station_level = user.get_station_level() + 1
                good = False
                if full_name == "Jarvis Bot (4 class)" and 1 <= station_level <= 3:
                    good = True
                elif full_name == "Jarvis Bot (3 class)" and 4 <= station_level <= 5:
                    good = True
                elif full_name == "Jarvis Bot (2 class)" and 6 <= station_level <= 7:
                    good = True
                elif full_name == "Jarvis Bot (1 class)" and 8 <= station_level <= 9:
                    good = True
                if good:
                    jarvis_owners[user.user_id] = True
            elif name == "Cryochamber":
                cryo_owners[user.user_id] = True
            elif name == "ASIC Manager":
                hashrate = int(user.mining_farm_speed)
                good = False
                if full_name == "ASIC Manager (3 class)" and 1 <= hashrate <= 299:
                    good = True
                elif full_name == "ASIC Manager (2 class)" and 300 <= hashrate <= 1199:
                    good = True
                elif full_name == "ASIC Manager (1 class)" and hashrate >= 1200:
                    good = True
                if good:
                    asic_owners[user.user_id] = True
            elif name == "Magnetic ring":
                hashrate = int(user.mining_farm_speed)
                good = False
                if full_name == "Magnetic ring (2 class)" and 1 <= hashrate <= 249:
                    good = True
                elif full_name == "Magnetic ring (1 class)" and 250 <= hashrate <= 599:
                    good = True
                if good:
                    magnit_owners[user.user_id] = True
            elif name == "Repair Kit":
                station_level = user.get_station_level() + 1
                good = False
                # Логика классов: 3 класс для станций 3-5, 2 класс для 6-7, 1 класс для 8-9
                if full_name == "Repair Kit (3 class)" and 3 <= station_level <= 5:
                    good = True
                elif full_name == "Repair Kit (2 class)" and 6 <= station_level <= 7:
                    good = True
                elif full_name == "Repair Kit (1 class)" and 8 <= station_level <= 9:
                    good = True
                if good:
                    repair_kit_owners[user.user_id] = True
                    logging.info(f"Repair Kit VALID: user {user.user_id}, station_level {station_level}, full_name '{full_name}'")
                else:
                    logging.info(f"Repair Kit INVALID: user {user.user_id}, station_level {station_level}, full_name '{full_name}' (expected: 3 class for 3-5, 2 class for 6-7, 1 class for 8-9)")
            
            continue
        
        # continue
        
        # else:
        #     if nft_rental.renter:
        #         renter_address = nft_rental.renter.ton_wallet
        #         users[address]["nft_count"] += 1
        #         users[address]["mining_power"] += stats["hash_rate"]
        #         users[address]["tbtc_speed"] += stats["mining_speed_tbtc"] * coef
        #         users[address]["consumption_kw"] += stats["consumption_kw"]

    # if 1 <= UserProfile.objects.get(user_id=678886913).get_station_level() + 1 <= 3:
    #     jarvis_owners[678886913] = True
    # Сбрасываем jarvis_expires для пользователей, у которых больше нет NFT Jarvis Bot
    UserProfile.objects.filter(
        jarvis_expires__year=2100,
    ).exclude(user_id__in=list(jarvis_owners.keys())).update(
        jarvis_expires=None,
    )
    # Также сбрасываем для пользователей с jarvis_expires = 2099 (старая запись)
    UserProfile.objects.filter(
        jarvis_expires__year=2099,
    ).exclude(user_id__in=list(jarvis_owners.keys())).update(
        jarvis_expires=None,
    )
    # Устанавливаем бесконечный jarvis_expires для пользователей с NFT Jarvis Bot
    UserProfile.objects.filter(
        user_id__in=list(jarvis_owners.keys())
    ).exclude(jarvis_expires__year=2100).update(
        jarvis_expires=infinite_date,
    )
    
    UserProfile.objects.filter(
        cryo_expires__year=2100,
    ).exclude(user_id__in=list(cryo_owners.keys())).update(
        cryo_expires=None,
    )
    UserProfile.objects.filter(
        user_id__in=list(cryo_owners.keys())
    ).exclude(cryo_expires__year=2100).update(
        cryo_expires=infinite_date,
    )
    
    UserProfile.objects.filter(
        manager_expires__year=2100,
    ).exclude(user_id__in=list(asic_owners.keys())).update(
        manager_expires=None,
    )
    UserProfile.objects.filter(
        user_id__in=list(asic_owners.keys())
    ).exclude(manager_expires__year=2100).update(
        manager_expires=infinite_date,
    )
    
    UserProfile.objects.filter(
        magnit_expires__year=2100,
    ).exclude(user_id__in=list(magnit_owners.keys())).update(
        magnit_expires=None,
    )
    UserProfile.objects.filter(
        user_id__in=list(magnit_owners.keys())
    ).exclude(magnit_expires__year=2100).update(
        magnit_expires=infinite_date,
    )
    
    # Сбрасываем repair_kit_expires для пользователей, у которых нет подходящего NFT
    UserProfile.objects.filter(
        repair_kit_expires__year=2100,
    ).exclude(user_id__in=list(repair_kit_owners.keys())).update(
        repair_kit_expires=None,
        repair_kit_power_level=None,
    )
    # Устанавливаем repair_kit_expires = infinite_date только для пользователей с подходящим NFT
    # Также устанавливаем repair_kit_power_level на текущий power, если он не установлен
    for user_id in repair_kit_owners.keys():
        try:
            user = UserProfile.objects.get(user_id=user_id)
            update_data = {}
            if user.repair_kit_expires is None or user.repair_kit_expires.year != 2100:
                update_data["repair_kit_expires"] = infinite_date
            # Устанавливаем repair_kit_power_level на текущий power, если он не установлен
            if user.repair_kit_power_level is None:
                update_data["repair_kit_power_level"] = user.power
            if update_data:
                UserProfile.objects.filter(user_id=user_id).update(**update_data)
        except UserProfile.DoesNotExist:
            continue

def main2():
    OFFICIAL_COLLECTION = "EQDJURRy7jc_GutdLdEvxfXL9D0wzByfDiOtLwA0bqniBYJe"
    PRELAUNCH_COLLECTION = "EQAxJtx_PbO2kB63nejVSjCNfe1ROW0E1-vLIYxItTayW76t"

    users = {}
    all_nfts = []
    for pages, collection_addr in ((4,OFFICIAL_COLLECTION), (1, PRELAUNCH_COLLECTION)):
        i = 0
        while True:
            pages = list(range(i, i + pages))
            # Последовательные запросы с задержками для rate limiting
            results = []
            for page in pages:
                results.append(async_to_sync(get_nfts)(collection_addr, page))
                if page != pages[-1]:  # Задержка между запросами, кроме последнего
                    time.sleep(0.5)

            has_short_page = False
            for data in results:
                all_nfts.extend(data.nft_items)
                logging.info(f"{len(data.nft_items)}")
                if len(data.nft_items) < 1000:
                    has_short_page = True

            if has_short_page:
                break
            i += pages
    logging.info(f"FINAL {len(all_nfts)}")

    if len(all_nfts) < 3200:
        logging.info(f"BREAK")
        return

    prelaunch_coef_obj = AsicsCoefs.objects.filter(address="prelaunch_coef").first()
    prelaunch_coef = prelaunch_coef_obj.coef if prelaunch_coef_obj else 1
    standart_coef_obj = AsicsCoefs.objects.filter(address="standart_coef").first()
    standart_coef = standart_coef_obj.coef if standart_coef_obj else 0.5
    magnit_booster = Booster.objects.filter(slug="magnit").first()
    manager_booster = Booster.objects.filter(slug="asic_manager").first()

    # Process active NFT rentals
    # now = timezone.now()
    # active_rentals = NFTRentalAgreement.objects.filter(end_date__gte=now)
    # for rental in active_rentals:
    #     renter = rental.renter
    #     if renter:
    #         stats = asics_data.get(rental.nft, None)
    #         if stats:
    #             users.setdefault(
    #                 renter.ton_wallet,
    #                 {
    #                     "nft_count": 0,
    #                     "mining_power": 0,
    #                     "tbtc_speed": 0,
    #                     "consumption_kw": 0,
    #                     "energy_left": 0,
    #                     "nft_string": [],
    #                     "powerbank_max_consume": 0,
    #                 },
    #             )
    #             users[renter.ton_wallet]["nft_count"] += 1
    #             users[renter.ton_wallet]["nft_string"].append(rental.nft)
    #             users[renter.ton_wallet]["mining_power"] += stats["hash_rate"]
    #             users[renter.ton_wallet]["tbtc_speed"] += stats["mining_speed_tbtc"]
    #             users[renter.ton_wallet]["consumption_kw"] += stats["consumption_kw"]

    # Process default NFTs
    sbt_owners = dict()
    jarvis_owners = dict()
    cryo_owners = dict()
    asic_owners = dict()
    magnit_owners = dict()
    repair_kit_owners = dict()
    
    infinite_date = timezone.make_aware(datetime(2100, 1, 1, 0, 0, 0))

    for nft in all_nfts:
        address = nft.owner.address.root
        collection_address = nft.collection.address.root
        nft_address = nft.address.root
        meta: dict = nft.metadata
        name = meta.get("name")
        if not name:
            continue

        name = name.split("(")[0].strip()
        coef = standart_coef
        if (
            collection_address
            == "0:3126dc7f3db3b6901eb79de8d54a308d7ded51396d04d7ebcb218c48b536b25b"
        ):
            coef = prelaunch_coef
        else:
            coef = standart_coef

        if name == "Special SBT":
            sbt_owners.setdefault(address, {"is_gold": False, "is_silver": False})
            rarity_value = next(
                item["value"]
                for item in meta["attributes"]
                if item["trait_type"] == "Rarity"
            )
            if rarity_value == "1 class":
                sbt_owners[address]["is_gold"] = True
            elif rarity_value == "2 class":
                sbt_owners[address]["is_silver"] = True
            continue

        # if name in ["Jarvis Bot", "Cryochamber", "ASIC Manager", "Magnetic ring"]:
        #     full_name = meta.get("name")
        #     linked = LinkedUserNFT.objects.filter(nft_address=nft_address).first()
            
        #     if linked and (
        #         linked.wallet != address or # owner_changed
        #         (linked.user and linked.user.ton_wallet and linked.user.ton_wallet != linked.wallet) or # user_changed_wallet
        #         (linked.user and UserProfile.objects.filter(ton_wallet=linked.wallet).exclude(id=linked.user.id).exists()) # someone_else_has_wallet
        #     ):
        #         print(f"linked {linked} owner changed {linked.wallet} != {address} or user changed {linked.user} != {linked.wallet}")
        #         linked.delete()
        #         linked = None
            
        #     if linked is None:
        #         linked = LinkedUserNFT.objects.create(
        #             user=UserProfile.objects.filter(ton_wallet=address).first(),
        #             wallet=address,
        #             nft_address=nft_address,
        #         )
                
                
        #     user = linked.user
        #     if user is None:
        #         user = UserProfile.objects.filter(ton_wallet=address).first()
        #         if user:
        #             LinkedUserNFT.objects.filter(wallet=address).update(
        #                 user=user
        #             )
        #         continue
            
            
        #     # JARVIS
        #     if name == "Jarvis Bot":
        #         station_level = user.get_station_level() + 1
        #         good = False
        #         if full_name == "Jarvis Bot (4 class)" and 1 <= station_level <= 3:
        #             good = True
        #         elif full_name == "Jarvis Bot (3 class)" and 4 <= station_level <= 5:
        #             good = True
        #         elif full_name == "Jarvis Bot (2 class)" and 6 <= station_level <= 7:
        #             good = True
        #         elif full_name == "Jarvis Bot (1 class)" and 8 <= station_level <= 9:
        #             good = True
        #         if good:
        #             jarvis_owners[user.user_id] = True
        #     elif name == "Cryochamber":
        #         cryo_owners[user.user_id] = True
        #     elif name == "ASIC Manager":
        #         hashrate = int(user.mining_farm_speed*1000)
        #         good = False
        #         if full_name == "ASIC Manager (3 class)" and 1 <= hashrate <= 299:
        #             good = True
        #         elif full_name == "ASIC Manager (2 class)" and 300 <= hashrate <= 1199:
        #             good = True
        #         elif full_name == "ASIC Manager (1 class)" and hashrate >= 1200:
        #             good = True
        #         if good:
        #             asic_owners[user.user_id] = True
        #     elif name == "Magnetic ring":
        #         hashrate = int(user.mining_farm_speed*1000)
        #         good = False
        #         if full_name == "Magnetic ring (2 class)" and 1 <= hashrate <= 249:
        #             good = True
        #         elif full_name == "Magnetic ring (1 class)" and 250 <= hashrate <= 599:
        #             good = True
        #         if good:
        #             magnit_owners[user.user_id] = True
            
        #     continue
        
        # continue
        
        # ASIC
        stats = asics_data.get(name, None)
        if stats is None:
            # print(meta)
            continue
        
        admin_coef = AsicsCoefs.objects.filter(address=nft_address).first()
        if admin_coef:
            coef = admin_coef.coef

        users.setdefault(
            address,
            {
                "nft_count": 0,
                "mining_power": 0,
                "tbtc_speed": 0,
                "consumption_kw": 0,
                "energy_left": 0,
                "nft_string": [],
                "powerbank_max_consume": 0,
            },
        )

        if stats["consumption_kw"] > users[address]["powerbank_max_consume"]:
            users[address]["powerbank_max_consume"] = stats["consumption_kw"]

        users[address]["nft_string"].append(nft_address)
        
        # TIMED NFT
        timed = TimedUserNFT.objects.select_related("user").filter(nft_address=nft_address).first()
        
        # if link
                
        # if linked and (
        #     linked.wallet != address or # owner_changed
        #     (linked.user and linked.user.ton_wallet and linked.user.ton_wallet != linked.wallet) or # user_changed_wallet
        #     (linked.user and UserProfile.objects.filter(ton_wallet=linked.wallet).exclude(id=linked.user.id).exists()) # someone_else_has_wallet
        # ):
        #     print(f"linked {linked} owner changed {linked.wallet} != {address} or user changed {linked.user} != {linked.wallet}")
        #     linked.delete()
        #     linked = None

        
        if timed is None:
            timed = TimedUserNFT.objects.create(
                user=UserProfile.objects.filter(ton_wallet=address).first(),
                wallet=address,
                nft_address=nft_address,
            )
            
        user = timed.user
        if user is None:
            user = UserProfile.objects.filter(ton_wallet=address).first()
            if user:
                TimedUserNFT.objects.filter(wallet=address).update(
                    user=user
                )
            continue
        # TIMED NFT END
        
        
        nft_rental = NFTRentalAgreement.objects.filter(nft=nft_address).first()
        # if nft_rental is None:
        users[address]["nft_count"] += 1
        users[address]["mining_power"] += stats["hash_rate"]
        users[address]["tbtc_speed"] += stats["mining_speed_tbtc"] * coef
        users[address]["consumption_kw"] += stats["consumption_kw"]

        NFTDatabase.objects.update_or_create(
            nft=nft_address,
            defaults={
                "wallet": address,
                "collection": collection_address,
                "hashrate": stats["hash_rate"],
                "name": name,
                "mining_speed_tbtc": stats["mining_speed_tbtc"] * coef,
                "consumption_kw": stats["consumption_kw"],
            },
        )
        # else:
        #     if nft_rental.renter:
        #         renter_address = nft_rental.renter.ton_wallet
        #         users[address]["nft_count"] += 1
        #         users[address]["mining_power"] += stats["hash_rate"]
        #         users[address]["tbtc_speed"] += stats["mining_speed_tbtc"] * coef
        #         users[address]["consumption_kw"] += stats["consumption_kw"]

    # if 1 <= UserProfile.objects.get(user_id=678886913).get_station_level() + 1 <= 3:
    #     jarvis_owners[678886913] = True
    # UserProfile.objects.filter(
    #     jarvis_expires__year=2100,
    # ).exclude(user_id__in=list(jarvis_owners.keys())).update(
    #     jarvis_expires=None,
    # )
    # UserProfile.objects.filter(
    #     user_id__in=list(jarvis_owners.keys())
    # ).exclude(jarvis_expires__year=2100).update(
    #     jarvis_expires=infinite_date,
    # )
    
    # UserProfile.objects.filter(
    #     cryo_expires__year=2100,
    # ).exclude(user_id__in=list(cryo_owners.keys())).update(
    #     cryo_expires=None,
    # )
    # UserProfile.objects.filter(
    #     user_id__in=list(cryo_owners.keys())
    # ).exclude(cryo_expires__year=2100).update(
    #     cryo_expires=infinite_date,
    # )
    
    # UserProfile.objects.filter(
    #     manager_expires__year=2100,
    # ).exclude(user_id__in=list(asic_owners.keys())).update(
    #     manager_expires=None,
    # )
    # UserProfile.objects.filter(
    #     user_id__in=list(asic_owners.keys())
    # ).exclude(manager_expires__year=2100).update(
    #     manager_expires=infinite_date,
    # )
    
    # UserProfile.objects.filter(
    #     magnit_expires__year=2100,
    # ).exclude(user_id__in=list(magnit_owners.keys())).update(
    #     magnit_expires=None,
    # )
    # UserProfile.objects.filter(
    #     user_id__in=list(magnit_owners.keys())
    # ).exclude(magnit_expires__year=2100).update(
    #     magnit_expires=infinite_date,
    # )

    logging.info("")
    logging.info("checking nfts")
    for profile in UserProfile.objects.all():
        try:
            user = users.get(profile.ton_wallet or "")
            if user is None:
                nft_string = ""
            else:
                nft_string = ";".join(user["nft_string"])
            sbt_info = sbt_owners.get(profile.ton_wallet or "")
            if sbt_info is None:
                sbt_info = {
                    "is_gold": False,
                    "is_silver": False,
                }
            if sbt_info["is_gold"] != profile.has_gold_sbt_nft:
                UserProfile.objects.filter(user_id=profile.user_id).update(
                    has_gold_sbt_nft=sbt_info["is_gold"]
                )
            if sbt_info["is_silver"] != profile.has_silver_sbt_nft:
                UserProfile.objects.filter(user_id=profile.user_id).update(
                    has_silver_sbt_nft=sbt_info["is_silver"]
                )
            if profile.nft_string != nft_string:
                profile.stop_mining(
                    f"different nft string {profile.nft_string} -> {nft_string}"
                )

                # for r in profile.rented_nfts:
                #     if not r.nft in nft_string:
                # print(r.nft, r.owner.first_name)
                # r.stop_rent()

                if user is None:
                    user = {
                        "nft_count": 0,
                        "mining_power": 0,
                        "tbtc_speed": 0,
                        "consumption_kw": 0,
                        "energy_left": 0,
                        "nft_string": [],
                        "powerbank_max_consume": 0,
                    }
                logger.info(profile)
                kwargs = {}
                mining_power = user["mining_power"] / 1000
                if profile.magnit_expires and timezone.now() < profile.magnit_expires:
                    old_magnit_price = get_booster_price_hashrate(
                        profile.magnit_buy_hashrate, magnit_booster
                    )
                    new_magmit_price = get_booster_price_hashrate(
                        mining_power, magnit_booster
                    )
                    if old_magnit_price < new_magmit_price:
                        days_left = (profile.magnit_expires - timezone.now()).days
                        BoosterRefund.objects.create(
                            user=profile,
                            booster=magnit_booster,
                            days_left=days_left,
                            old_price=old_magnit_price,
                            new_price=new_magmit_price,
                            total_amount=old_magnit_price * days_left,
                        )
                        kwargs["magnit_expires"] = None
                if profile.manager_expires and timezone.now() < profile.manager_expires:
                    old_manager_price = get_booster_price_hashrate(
                        profile.manager_buy_hashrate, manager_booster
                    )
                    new_manager_price = get_booster_price_hashrate(
                        mining_power, manager_booster
                    )
                    if old_manager_price < new_manager_price:
                        days_left = (profile.manager_expires - timezone.now()).days
                        BoosterRefund.objects.create(
                            user=profile,
                            booster=manager_booster,
                            days_left=days_left,
                            old_price=old_manager_price,
                            new_price=new_manager_price,
                            total_amount=old_manager_price * days_left,
                        )
                        kwargs["manager_expires"] = None

                UserProfile.objects.filter(user_id=profile.user_id).update(
                    nft_string=nft_string,
                    nft_count=user["nft_count"],
                    mining_farm_speed=mining_power,
                    total_mining_speed=user["tbtc_speed"],
                    total_farm_consumption=user["consumption_kw"],
                    farm_runtime=(
                        profile.kw_wallet / user["consumption_kw"]
                        if user["consumption_kw"] != 0
                        else 0
                    ),
                    powerbank_max_consume=user["powerbank_max_consume"],
                    **kwargs,
                )

            if user and profile.total_mining_speed != user["tbtc_speed"]:
                logging.info(
                    f"upd {profile.user_id} speed {profile.total_mining_speed} -> {user['tbtc_speed']}"
                )
                UserProfile.objects.filter(user_id=profile.user_id).update(
                    total_mining_speed=user["tbtc_speed"],
                )

            if user and profile.mining_farm_speed != user["mining_power"] / 1000:
                logging.info(
                    f"upd {profile.user_id} power {profile.total_mining_speed} -> {user['mining_power'] / 1000}"
                )
                UserProfile.objects.filter(user_id=profile.user_id).update(
                    mining_farm_speed=user["mining_power"] / 1000,
                )
            if user and profile.total_farm_consumption != user["consumption_kw"]:
                logging.info(
                    f"upd {profile.user_id} consumption {profile.total_farm_consumption} -> {user['consumption_kw']}"
                )
                UserProfile.objects.filter(user_id=profile.user_id).update(
                    total_farm_consumption=user["consumption_kw"]
                )

            if user and profile.powerbank_max_consume != user["powerbank_max_consume"]:
                logging.info(
                    f"upd {profile.user_id} powerbank_max_consume {profile.powerbank_max_consume} -> {user['powerbank_max_consume']}"
                )
                UserProfile.objects.filter(user_id=profile.user_id).update(
                    powerbank_max_consume=user["powerbank_max_consume"]
                )
        except Exception:
            logger.exception("err profile")



def main_timed():
    OFFICIAL_COLLECTION = "EQDJURRy7jc_GutdLdEvxfXL9D0wzByfDiOtLwA0bqniBYJe"
    PRELAUNCH_COLLECTION = "EQAxJtx_PbO2kB63nejVSjCNfe1ROW0E1-vLIYxItTayW76t"
    STATION_COLLECTION = "EQB-pBhnWEYPbIu25uM1Yp5MqGFjQ-8Jes5CT2Dr-OVd705u"

    users = {}
    all_nfts = []
    for pages, collection_addr in ((4,OFFICIAL_COLLECTION), (1, PRELAUNCH_COLLECTION), (2, STATION_COLLECTION)):
        i = 0
        while True:
            pages = list(range(i, i + pages))
            # Последовательные запросы с задержками для rate limiting
            results = []
            for page in pages:
                results.append(async_to_sync(get_nfts)(collection_addr, page))
                if page != pages[-1]:  # Задержка между запросами, кроме последнего
                    time.sleep(0.5)

            has_short_page = False
            for data in results:
                all_nfts.extend(data.nft_items)
                logging.info(f"{len(data.nft_items)}")
                if len(data.nft_items) < 1000:
                    has_short_page = True

            if has_short_page:
                break
            i += pages
    logging.info(f"FINAL {len(all_nfts)}")

    if len(all_nfts) < 3200:
        logging.info(f"BREAK")
        return


    for nft in all_nfts:
        address = nft.owner.address.root
        collection_address = nft.collection.address.root
        is_asic = collection_address in [OFFICIAL_COLLECTION, PRELAUNCH_COLLECTION]
        nft_address = nft.address.root
        meta: dict = nft.metadata
        name = meta.get("name")
        if not name:
            continue

        name = name.split("(")[0].strip()
        
        # TIMED NFT
        timed = TimedUserNFT.objects.select_related("user").filter(nft_address=nft_address).first()
        
        if timed is None:
            timed = TimedUserNFT.objects.create(
                user=UserProfile.objects.filter(ton_wallet=address).first(),
                name=name,
                collection=collection_address,
                wallet=address,
                nft_address=nft_address,
            )
        
        if timed.wallet != address:
            if timed.user and is_asic:
                timed.user.stop_mining()
            TimedUserNFT.objects.filter(nft_address=nft_address).update(
                user=None,
                wallet=address,
                block_until=timezone.now() + timedelta(days=1),
            )
            new_user = UserProfile.objects.filter(ton_wallet=address).first()
            if new_user:
                if is_asic:
                    new_user.stop_mining()
                TimedUserNFT.objects.filter(nft_address=nft_address).update(
                    user=new_user,
                )
            continue        
        
        
            
        user = timed.user
        if user is None:
            user = UserProfile.objects.filter(ton_wallet=address).first()
            if user:
                TimedUserNFT.objects.filter(wallet=address).update(
                    user=user
                )
            continue
        
        if timed.user:
            if timed.user.ton_wallet and timed.user.ton_wallet != address:
                # print(f"timed user {timed.user} wallet {timed.user.ton_wallet} != {address}")
                new_user = UserProfile.objects.filter(ton_wallet=address).first()
                if new_user:
                    TimedUserNFT.objects.filter(nft_address=nft_address).update(
                        user=new_user,
                        block_until=timezone.now() + timedelta(days=1),
                    )
                else:
                    TimedUserNFT.objects.filter(nft_address=nft_address).update(
                        user=None,
                    )
                continue
        # if link
                
        # if linked and (
        #     linked.wallet != address or # owner_changed
        #     (linked.user and linked.user.ton_wallet and linked.user.ton_wallet != linked.wallet) or # user_changed_wallet
        #     (linked.user and UserProfile.objects.filter(ton_wallet=linked.wallet).exclude(id=linked.user.id).exists()) # someone_else_has_wallet
        # ):
        #     print(f"linked {linked} owner changed {linked.wallet} != {address} or user changed {linked.user} != {linked.wallet}")
        #     linked.delete()
        #     linked = None

        

        # TIMED NFT END
        


if __name__ == "__main__":
    import asyncio
    import threading

    def run_main():
        while True:
            try:
                main()
                time.sleep(5)  # Задержка между итерациями для снижения нагрузки
            except Exception:
                logger.exception("Error in main transaction processing")
                time.sleep(10)  # Большая задержка при ошибке

    def run_main_mint():
        while True:
            try:
                main_mint()
                time.sleep(15)  # Задержка между проверками NFT станций (есть кэш на 10 минут)
            except Exception:
                logger.exception("Error in main mint processing")
                time.sleep(30)  # Большая задержка при ошибке

    def run_main2():
        while True:
            try:
                main2()
                time.sleep(15)  # Задержка между обновлениями ASIC NFT профилей
            except Exception:
                logger.exception("Error in main2 processing")
                time.sleep(30)  # Большая задержка при ошибке

    def run_main_boosters():
        while True:
            try:
                main_boosters()
                time.sleep(20)  # Задержка между проверками бустеров (не критично)
            except Exception:
                logger.exception("Error in main boosters processing")
                time.sleep(40)  # Большая задержка при ошибке
    
    def run_main_timed():
        while True:
            try:
                main_timed()
                time.sleep(20)  # Задержка между проверками timed NFT (не критично)
            except Exception:
                logger.exception("Error in main timed processing")
                time.sleep(40)  # Большая задержка при ошибке

    # Start threads
    t1 = threading.Thread(target=run_main, daemon=True)
    t2 = threading.Thread(target=run_main_mint, daemon=True)
    t3 = threading.Thread(target=run_main2, daemon=True)
    t4 = threading.Thread(target=run_main_boosters, daemon=True)
    t5 = threading.Thread(target=run_main_timed, daemon=True)

    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()

    # Keep main thread alive
    while True:
        time.sleep(1)

        # try:
        #     process_nft_rentals()
        #     time.sleep(1)
        # except Exception:
        #     logger.exception("Error in NFT rental processing")

        # time.sleep(10)
