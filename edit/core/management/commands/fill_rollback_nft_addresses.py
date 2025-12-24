from django.core.management.base import BaseCommand
from core.models import StationRollbackLog, UserProfile, LinkedUserNFT
from pytonapi import AsyncTonapi
from asgiref.sync import async_to_sync
import time

# Коллекция станций
STATION_COLLECTION = "EQB-pBhnWEYPbIu25uM1Yp5MqGFjQ-8Jes5CT2Dr-OVd705u"

# API ключ (использовать тот же, что в t.py)
API_KEY = "AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"

tonapi = AsyncTonapi(api_key=API_KEY)


async def get_user_nft_by_station_type(wallet_address, station_type):
    """
    Получить NFT адрес конкретной станции пользователя из TON API.
    
    Args:
        wallet_address: TON wallet адрес пользователя
        station_type: Тип станции из StationRollbackLog.from_station
    
    Returns:
        NFT адрес или None если не найден
    """
    try:
        # Маппинг типов станций из БД в названия в NFT метаданных
        # В БД: "Nuclear power plant" (с маленькой p)
        # В NFT metadata: "Nuclear Power Plant" (с заглавной P)
        # Пример из TonViewer: "Nuclear Power Plant" с атрибутами Level и Rarity
        station_type_mapping = {
            "Nuclear power plant": "Nuclear Power Plant",
            "Thermonuclear power plant": "Thermonuclear Power Plant",
            "Dyson Sphere": "Dyson Sphere",  # Без изменений
            "Neutron star": "Neutron Star",  # С заглавной S
            "Boiler house": "Boiler House",  # С заглавной H
        }
        
        # Получить ожидаемое название из метаданных
        expected_name = station_type_mapping.get(station_type, station_type)
        
        # Получить все NFT из коллекции станций
        # Нужно пройти по всем страницам
        all_nfts = []
        offset = 0
        limit = 1000
        
        while True:
            nfts = await tonapi.nft.get_items_by_collection_address(
                STATION_COLLECTION,
                limit=limit,
                offset=offset,
            )
            
            if not nfts.nft_items:
                break
            
            all_nfts.extend(nfts.nft_items)
            
            # Если получили меньше limit, значит это последняя страница
            if len(nfts.nft_items) < limit:
                break
            
            offset += limit
            # Rate limiting: небольшая задержка между страницами
            time.sleep(0.01)
        
        # Найти NFT, принадлежащий этому wallet и соответствующего типа станции
        for nft in all_nfts:
            if nft.owner.address.root == wallet_address:
                # Получить метаданные NFT
                meta = nft.metadata or {}
                name = meta.get("name", "")
                
                # Убрать уровень в скобках (например "Nuclear Power Plant (Level 3)" -> "Nuclear Power Plant")
                name_clean = name.split("(")[0].strip()
                
                # Пропускаем Hydroelectric и Orbital (они в другой коллекции)
                if name_clean in ["Hydroelectric Power Station", "Orbital Power Station"]:
                    continue
                
                # Проверить, что тип станции совпадает (case-insensitive для надежности)
                if name_clean.lower() == expected_name.lower():
                    return nft.address.root
        
        return None
    except Exception as e:
        print(f"Ошибка при получении NFT для {wallet_address}, станция {station_type}: {e}")
        return None


class Command(BaseCommand):
    help = 'Заполнить NFT адреса в StationRollbackLog из TON API'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Только показать, что будет сделано, без изменений',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Получить все записи без NFT адреса
        rollback_logs = StationRollbackLog.objects.filter(
            nft_address__isnull=True
        ).exclude(nft_address='').select_related('user')
        
        total = rollback_logs.count()
        self.stdout.write(f"Найдено записей без NFT адреса: {total}")
        
        filled = 0
        not_found = 0
        errors = 0
        
        for i, rollback_log in enumerate(rollback_logs, 1):
            user = rollback_log.user
            
            if not user.ton_wallet:
                self.stdout.write(
                    self.style.WARNING(
                        f"[{i}/{total}] User {user.user_id}: нет TON wallet"
                    )
                )
                not_found += 1
                continue
            
            self.stdout.write(
                f"[{i}/{total}] Обработка User {user.user_id} (wallet: {user.ton_wallet}, станция: {rollback_log.from_station})..."
            )
            
            # Проверка LinkedUserNFT для Hydroelectric/Orbital станций
            if rollback_log.from_station in ["Hydroelectric Power Station", "Orbital Power Station"]:
                linked = LinkedUserNFT.objects.filter(
                    user=user,
                    wallet=user.ton_wallet
                ).first()
                
                if linked:
                    if not dry_run:
                        rollback_log.nft_address = linked.nft_address
                        rollback_log.save(update_fields=['nft_address'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Найден NFT в LinkedUserNFT: {linked.nft_address}"
                        )
                    )
                    filled += 1
                    continue  # Пропустить запрос к API
            
            if not dry_run:
                # Получить NFT адрес конкретной станции из TON API
                nft_address = async_to_sync(get_user_nft_by_station_type)(
                    user.ton_wallet,
                    rollback_log.from_station
                )
                
                if nft_address:
                    rollback_log.nft_address = nft_address
                    rollback_log.save(update_fields=['nft_address'])
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ Найден NFT для {rollback_log.from_station}: {nft_address}"
                        )
                    )
                    filled += 1
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  NFT не найден в TON API для станции '{rollback_log.from_station}'"
                        )
                    )
                    not_found += 1
                
                # Rate limiting: 10ms между запросами
                time.sleep(0.01)
            else:
                # Dry run: только показать
                self.stdout.write(
                    f"  [DRY RUN] Будет запрошен NFT для wallet: {user.ton_wallet}, "
                    f"станция: {rollback_log.from_station}"
                )
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS(f"✅ Заполнено: {filled}"))
        self.stdout.write(self.style.WARNING(f"⚠️  Не найдено: {not_found}"))
        if errors > 0:
            self.stdout.write(self.style.ERROR(f"❌ Ошибок: {errors}"))
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nЭто был dry-run. Запустите без --dry-run для применения изменений.")
            )

