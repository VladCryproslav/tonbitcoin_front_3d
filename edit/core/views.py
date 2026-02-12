import decimal

# import logging
import math
from datetime import datetime
import traceback

from aiogram.types import user
from amqp import NotAllowed
import django
import django.http

# Create your views here.
import django_filters
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render
from rest_framework.viewsets import ReadOnlyModelViewSet

from core.utils import add_chart_kw
from tasks.models import Booster
from tasks.serializers import UserStakingSerializer

from .models import (  # Import the Notification model
    AutoWithdrawalRequest,
    ChartData,
    EngineerConfig,
    GlobalSpendStats,
    HashrateInfo,
    MiningStats,
    NFTDatabase,
    NFTRentalAgreement,
    NFTRentalConfig,
    Notification,
    OrbitalOwner,
    RepairPowerStationConfig,
    RoadmapItem,
    SpecialAsicStaking,
    StakingPeriodConfig,
    GradationConfig,
    StationNFTOwner,
    TimedUserNFT,
    UserBurnedTBTC,
    UserStaking,
    WalletInfo,
    WithdrawalConfig,
    add_kw_commission,
    add_mining_commission,
    add_tbtc_commission,
)
from .serializers import (
    GradationConfigSerializer,
    NFTRentalAgreementSerializer,
    TimedUserNFTSerializer,  # Import the NFTRentalAgreement serializer
    WalletInfoSerializer
)
from .serializers import NotificationSerializer  # Import the Notification serializer
from .serializers import (
    EngineerConfigSerializer,
    HashrateInfoSerializer,
    NFTRentalConfigSerializer,
    RoadmapItemSerializer,
    StakingPeriodConfigSerializer,
    WithdrawConfigSerializer,
    UserBurnedTBTCSerializer,  # Import the missing serializer
)


class RoadmapItemViewSet(ReadOnlyModelViewSet):
    queryset = RoadmapItem.objects.all().order_by("order")  # Сортування за order
    serializer_class = RoadmapItemSerializer


import random
from datetime import timedelta

from asgiref.sync import async_to_sync
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotAuthenticated, NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from shared import setup_logger
from tgbot.utils import parse_init_data

from .models import MintRequest  # New import
from .models import NFTStation  # New import
from .models import OverheatConfig  # New import
from .models import StationRollbackLog  # New import
from .models import UserActionLog  # New import
from .models import (
    BufferTransaction,
    GenPowerStationConfig,
    StoragePowerStationConfig,
    UserProfile,
    WithdrawalRequest,
)
from .serializers import NFTStationSerializer  # New import
from .serializers import StationRollbackLogSerializer  # New import
from .serializers import UserActionLogSerializer  # New import
from .serializers import UserProfileSerializer, WithdrawalRequestSerializer

# import sentry_sdk

action_logger = setup_logger()
# def setup_logger2222(log_file="logs/debug.log"):
#     """Sets up a logger that logs to a single file."""
#     logger = logging.getLogger("debugdebug")
#     logger.setLevel(logging.DEBUG)

#     # Create file handler
#     file_handler = logging.FileHandler(log_file)
#     file_handler.setLevel(logging.DEBUG)

#     # Create formatter and add it to the handler
#     formatter = logging.Formatter(
#         "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
#     )
#     file_handler.setFormatter(formatter)

#     # Avoid adding handlers multiple times
#     if not logger.handlers:
#         logger.addHandler(file_handler)

#     return logger

# loger222 = setup_logger2222("logs/debug.log")


def require_auth(view_func):
    def wrapper(self, request, *args, **kwargs):
        # return NotAllowed()
        
        data = request.headers.get("X-Custom-Token")

        init_data = parse_init_data(settings.BOT_TOKEN, data)

        if not init_data:
            raise NotAuthenticated("Invalid or missing token.")

        request.init_data = init_data
        user_id = init_data["user"]["id"]
        # if user_id == 678886913:
        #     user_id = 5141702856
        request.user_id = user_id
        try:
            user = UserProfile.objects.get(user_id=user_id)
            UserProfile.objects.filter(user_id=user_id).update(
                first_name=init_data["user"]["first_name"],
                username=init_data["user"].get("username", None),
            )
        except UserProfile.DoesNotExist:
            user = UserProfile.objects.create(
                user_id=user_id,
                first_name=init_data["user"]["first_name"],
                username=init_data["user"].get("username", None),
                ton_wallet="",  # Initialize with an empty string or appropriate default value
            )
            user.storage_limit = StoragePowerStationConfig.objects.get(
                station_type=user.station_type, level=user.storage_level
            ).storage_limit
            user.generation_rate = GenPowerStationConfig.objects.get(
                station_type=user.station_type, level=user.generation_level
            ).generation_rate
            user.kw_per_tap = EngineerConfig.objects.get(
                level=user.engineer_level
            ).tap_power
            user.save()

            try:
                code = init_data["start_param"]
                if code and code.startswith("ref_id"):
                    ref_id = int(code.replace("ref_id", ""))
                    referrer = UserProfile.objects.filter(user_id=ref_id).first()
                    if referrer is not None:
                        UserProfile.objects.filter(user_id=user_id).update(
                            referrer=referrer,
                            referrer_level_2=referrer.referrer,
                        )
            except Exception as e:
                action_logger.exception(f"startapp data {user_id}")

        user.refresh_from_db()
        request.user_profile = user

        if user.blocked:
            return django.http.JsonResponse({"error": "User is blocked"}, status=400)

        return view_func(self, request, *args, **kwargs)

    return wrapper


from django.db.models import F, Case, When
from rest_framework.decorators import api_view, throttle_classes

# class UserProfileThrottle(SimpleRateThrottle):
#     """
#     Limits the rate of API calls that may be made by a given user.

#     The user id will be used as a unique cache key if the user is
#     authenticated.  For anonymous requests, the IP address of the request will
#     be used.
#     """

#     scope = "tap"
#     rate = "1/s"

#     def get_cache_key(self, request, view):
#         ident = request.user_profile.user_id

#         return self.cache_format % {"scope": self.scope, "ident": ident}


overheat_hours_by_type = {
    "Thermal power plant": 4,  # station #3
    "Geothermal power plant": 2,  # station #4
    "Nuclear power plant": 2,  # station #5
    "Thermonuclear power plant": 1,  # station #6
    "Dyson Sphere": 1,  # station #7
}

from rest_framework.throttling import SimpleRateThrottle


class TapEnergyThrottle(SimpleRateThrottle):
    rate = '5/s'
    
    def get_cache_key(self, request, view):
        ident = getattr(request, 'user_id', None)
        if ident is None:
            return None
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }

class TapEnergyView(APIView):
    # throttle_classes = []
    def get_throttles(self):
        return [TapEnergyThrottle()]
    
    @swagger_auto_schema(
        tags=["station"],
        operation_description="Додає енергії за один тап",
        responses={
            200: openapi.Response(
                description="Успішне оновлення енергії",
                examples={
                    "application/json": {
                        "message": "Energy updated",
                        "energy_added": 0.1,
                        "total_energy": 10.5,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        self.check_throttles(request)
        user_id = request.user_profile.user_id
        # if user_id==678886913:
        #     loger222.info(f"tap {user_id}")

        last_tap_time = cache.get(f"last_tap_time_{user_id}")

        if last_tap_time and (timezone.now() - last_tap_time).total_seconds() < 0.15:
            return Response(
                {"error": "Taps are too frequent. Please wait a moment."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        user_profile: UserProfile = request.user_profile
        cache.set(f"last_tap_time_{user_id}", timezone.now(), timeout=1)

        if user_profile.jarvis_expires and user_profile.jarvis_expires > timezone.now():
            return Response(
                {"error": "Jarvis is active. Please wait until it expires."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user_profile.is_building():
            return Response({"error": "Station is under construction"})

        if WalletInfo.objects.filter(user=user_profile, wallet=user_profile.ton_wallet, block_until__gt=timezone.now()).exists():
            return Response({"error": "Wallet is blocked until cooldown period ends."})

        orbital_nft = user_profile.current_station_nft
        if orbital_nft:
            orbital_owner = OrbitalOwner.objects.filter(nft_address=orbital_nft).first()
            if orbital_owner is not None and orbital_owner.user.user_id != user_profile.user_id:
                UserProfile.objects.filter(
                    user_id=orbital_owner.user.user_id
                ).update(orbital_first_owner=False, orbital_is_blue=False)
                orbital_owner.user.refresh_from_db()
                orbital_owner.user.check_storage_generation()

        overheat_config = OverheatConfig.objects.first() or OverheatConfig(
            taps_before_power_reduction=5,
            power_reduction_percentage=1,
            min_duration=15,
            max_duration=300,
        )
        try:
            # OVERHEAT
            if user_profile.overheated_until:
                is_repair_kit_active = (
                    user_profile.repair_kit_expires and
                    timezone.now() < user_profile.repair_kit_expires
                )
                if user_profile.tap_count_since_overheat >= (
                    overheat_config.taps_before_power_reduction
                ):
                    if not is_repair_kit_active:
                        UserProfile.objects.filter(
                            user_id=request.user_profile.user_id
                        ).update(
                            tap_count_since_overheat=F("tap_count_since_overheat") + 1,
                            power=F("power") - overheat_config.power_reduction_percentage,
                        )
                    else:
                        # repair_kit active, no power reduction during overheat
                        UserProfile.objects.filter(
                            user_id=request.user_profile.user_id
                        ).update(
                            tap_count_since_overheat=F("tap_count_since_overheat") + 1,
                        )
                    UserProfile.objects.filter(
                        user_id=request.user_profile.user_id, power__lt=0
                    ).update(power=0)
                else:
                    UserProfile.objects.filter(
                        user_id=request.user_profile.user_id
                    ).update(
                        tap_count_since_overheat=F("tap_count_since_overheat") + 1,
                    )
                user_profile.refresh_from_db()
                return Response(
                    {
                        "message": "Station is overheated. Please wait until it cools down.",
                        "overheated_until": user_profile.overheated_until,
                        "total_energy": user_profile.energy,
                        "power": user_profile.power,
                        "storage": user_profile.storage,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            # END OVERHEAT
            
            user_profile.check_storage_generation()

            real_engs = user_profile.get_real_engs()
            kw_per_tap = EngineerConfig.objects.get(level=real_engs).tap_power
            tapped_kw = (
                kw_per_tap * user_profile.sbt_get_tap_power_bonus()
            )
            if kw_per_tap > user_profile.storage:
                tapped_kw = user_profile.storage

            if tapped_kw <= 0:
                return Response(
                    {"error": "Not enough energy in storage"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # withdraw_config = WithdrawalConfig.objects.first() or None
            # tap_power_config = getattr(withdraw_config, "tap_power", 0.5)
            final_power_minus = (
                tapped_kw / F("generation_rate") / 2 * user_profile.sbt_get_power()
            )
            GlobalSpendStats.objects.update(
                total_energy_accumulated=F("total_energy_accumulated") + tapped_kw
            )
            
            # Проверяем активность Repair Kit
            is_repair_kit_active = (
                user_profile.repair_kit_expires and
                timezone.now() < user_profile.repair_kit_expires
            )
            
            update_data = {
                "energy": F("energy") + tapped_kw,
                "tap_count": F("tap_count") + 1,
                "storage": F("storage") - tapped_kw,
                "overheat_energy_collected": F("overheat_energy_collected") + tapped_kw,
            }
            
            if is_repair_kit_active:
                # Если Repair Kit активен, но repair_kit_power_level не установлен, фиксируем текущий power
                if user_profile.repair_kit_power_level is None:
                    update_data["repair_kit_power_level"] = user_profile.power
                    repair_kit_power_level = user_profile.power
                else:
                    repair_kit_power_level = user_profile.repair_kit_power_level

                # При активном Repair Kit power вообще не должен снижаться:
                # - если текущий power ниже зафиксированного уровня, поднимаем его до repair_kit_power_level
                # - если выше или равен, оставляем без изменений (не вычитаем final_power_minus)
                update_data["power"] = Case(
                    When(power__lt=repair_kit_power_level, then=repair_kit_power_level),
                    default=F("power"),
                )
            else:
                # Обычное снижение power
                update_data["power"] = F("power") - final_power_minus
            
            UserProfile.objects.filter(user_id=request.user_profile.user_id).update(**update_data)
            UserProfile.objects.filter(
                user_id=request.user_profile.user_id, power__lt=0
            ).update(power=0)
            WalletInfo.objects.filter(user=user_profile, wallet=user_profile.ton_wallet).update(kw_amount=F("kw_amount") + tapped_kw)
            add_chart_kw(tapped_kw)
            user_profile = UserProfile.objects.get(user_id=request.user_profile.user_id)
            try:
                if user_profile.referrer:
                    UserProfile.objects.filter(
                        user_id=user_profile.referrer.user_id
                    ).update(bonus_kw_level_1=F("bonus_kw_level_1") + tapped_kw * 0.1)

                    UserProfile.objects.filter(user_id=user_profile.user_id).update(
                        bring_bonus_kw_level_1=F("bring_bonus_kw_level_1")
                        + tapped_kw * 0.1
                    )

                    if user_profile.referrer_level_2:
                        UserProfile.objects.filter(
                            user_id=user_profile.referrer_level_2.user_id
                        ).update(
                            bonus_kw_level_2=F("bonus_kw_level_2") + tapped_kw * 0.05
                        )

                        UserProfile.objects.filter(
                            user_id=user_profile.referrer.user_id
                        ).update(
                            bring_bonus_kw_level_2=F("bring_bonus_kw_level_2")
                            + tapped_kw * 0.05
                        )

            except Exception as e:
                pass

            user_profile.refresh_from_db()
            needed_hours = overheat_hours_by_type.get(user_profile.station_type, None)
            is_cryo_active = (
                user_profile.cryo_expires and timezone.now() < user_profile.cryo_expires
            )
            if needed_hours and not is_cryo_active:
                if user_profile.was_overheated:
                    if (
                        user_profile.overheat_energy_collected
                        >= float(user_profile.generation_rate) * needed_hours
                    ):
                        UserProfile.objects.filter(
                            user_id=request.user_profile.user_id
                        ).update(
                            was_overheated=False,
                            overheat_energy_collected=0,
                            overheat_goal=None,
                        )
                else:
                    if user_profile.overheat_goal is None:
                        UserProfile.objects.filter(
                            user_id=request.user_profile.user_id
                        ).update(
                            overheat_goal=random.uniform(
                                0,
                                float(user_profile.generation_rate)
                                * needed_hours
                                * float(user_profile.power / 100),
                            )
                        )
                    user_profile.refresh_from_db()
                    if (
                        user_profile.overheat_energy_collected
                        >= user_profile.overheat_goal
                    ):
                        duration = random.randint(
                            overheat_config.min_duration, overheat_config.max_duration
                        )
                        UserProfile.objects.filter(
                            user_id=request.user_profile.user_id
                        ).update(
                            overheated_until=timezone.now()
                            + timedelta(seconds=duration),
                            was_overheated=True,
                        )

            user_profile.refresh_from_db()
            return Response(
                {
                    "message": "Energy updated",
                    "energy_added": tapped_kw,
                    "total_energy": user_profile.energy,
                    "power": user_profile.power,
                    "storage": user_profile.storage,
                    "overheated_until": user_profile.overheated_until,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class GameRunUpdateOverheatView(APIView):
    """Обновляет состояние перегрева во время забега (только логика перегрева, без обновления energy/storage/power)"""
    
    @require_auth
    def post(self, request):
        user_profile = request.user_profile
        now = timezone.now()
        
        # Получаем количество собранной энергии из забега
        collected_amount = float(request.data.get('amount', 0))
        
        if collected_amount <= 0:
            return Response(
                {"error": "Invalid amount"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверяем активность Cryo (перегрев невозможен если Cryo активен)
        is_cryo_active = (
            user_profile.cryo_expires and
            timezone.now() < user_profile.cryo_expires
        )
        
        # Получаем конфигурацию перегрева
        overheat_config = OverheatConfig.objects.first() or OverheatConfig(
            taps_before_power_reduction=5,
            power_reduction_percentage=1,
            min_duration=15,
            max_duration=300,
        )
        
        # Проверяем активный перегрев
        if user_profile.overheated_until and user_profile.overheated_until > now:
            # Перегрев уже активен, возвращаем состояние
            user_profile.refresh_from_db()
            return Response({
                "overheated": True,
                "overheated_until": user_profile.overheated_until.isoformat(),
                "overheat_energy_collected": user_profile.overheat_energy_collected,
                "overheat_goal": user_profile.overheat_goal,
                "was_overheated": user_profile.was_overheated,
            })
        
        # ВАЖНО: Power больше не участвует в системе перегрева
        # Не обновляем power при перегреве (в отличие от старой системы тапов)
        
        # Обновляем накопленную энергию для перегрева
        needed_hours = overheat_hours_by_type.get(user_profile.station_type, None)
        
        # ВАЖНО: Если криокамера активна, перегрев не может активироваться
        if needed_hours and not is_cryo_active:
            # Обновляем overheat_energy_collected
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                overheat_energy_collected=F("overheat_energy_collected") + collected_amount
            )
            user_profile.refresh_from_db()
            
            # Используем существующую логику перегрева из TapEnergyView (строки 448-491)
            if user_profile.was_overheated:
                if (
                    user_profile.overheat_energy_collected
                    >= float(user_profile.generation_rate) * needed_hours
                ):
                    UserProfile.objects.filter(
                        user_id=user_profile.user_id
                    ).update(
                        was_overheated=False,
                        overheat_energy_collected=0,
                        overheat_goal=None,
                    )
            else:
                if user_profile.overheat_goal is None:
                    UserProfile.objects.filter(
                        user_id=user_profile.user_id
                    ).update(
                        overheat_goal=random.uniform(
                            0,
                            float(user_profile.generation_rate)
                            * needed_hours
                            * float(user_profile.power / 100),
                        )
                    )
                user_profile.refresh_from_db()
                if (
                    user_profile.overheat_energy_collected
                    >= user_profile.overheat_goal
                ):
                    duration = random.randint(
                        overheat_config.min_duration, overheat_config.max_duration
                    )
                    UserProfile.objects.filter(
                        user_id=user_profile.user_id
                    ).update(
                        overheated_until=timezone.now()
                        + timedelta(seconds=duration),
                        was_overheated=True,
                    )
        
        user_profile.refresh_from_db()
        
        return Response({
            "overheated": bool(user_profile.overheated_until and user_profile.overheated_until > now),
            "overheated_until": user_profile.overheated_until.isoformat() if user_profile.overheated_until else None,
            "overheat_energy_collected": user_profile.overheat_energy_collected,
            "overheat_goal": user_profile.overheat_goal,
            "was_overheated": user_profile.was_overheated,
        })


# class UpgradeStationView(APIView):
#     @swagger_auto_schema(
#         operation_description="Покращення станції користувача",
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             required=["user_id"],
#             properties={
#                 "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
#             },
#         ),
#     )
#     def post(self, request):
#         user_id = request.data["user_id"]
#         try:
#             user_profile = UserProfile.objects.get(user_id=user_id)
#             if user_profile.level < 3:
#                 next_level = user_profile.level + 1
#                 config = PowerStationConfig.objects.get(
#                     station_type=user_profile.station_type, level=next_level
#                 )

#                 if user_profile.energy >= config.price_kw:
#                     user_profile.level = next_level
#                     user_profile.storage_limit = config.storage_limit
#                     user_profile.generation_rate = config.generation_rate
#                     user_profile.energy -= config.price_kw
#                     user_profile.save()
#                     return Response(
#                         {"message": "Station upgraded successfully"}, status=200
#                     )
#                 else:
#                     return Response({"error": "Not enough kW for upgrade"}, status=400)
#             else:
#                 return Response({"error": "Maximum level reached"}, status=400)
#         except UserProfile.DoesNotExist:
#             return Response({"error": "User not found"}, status=404)


from .serializers import (
    GenPowerStationConfigSerializer,
    RepairPowerStationConfigSerializer,
    StoragePowerStationConfigSerializer,
)


class PowerStationConfigView(APIView):
    @swagger_auto_schema(
        tags=["station", "config"],
        operation_description="Отримати дані по конфігураціям станцій",
    )
    @require_auth
    def get(self, request):
        gen_configs = GenPowerStationConfigSerializer(
            GenPowerStationConfig.objects.all(), many=True
        )
        storage_configs = StoragePowerStationConfigSerializer(
            StoragePowerStationConfig.objects.all(), many=True
        )
        repair_configs = RepairPowerStationConfigSerializer(
            RepairPowerStationConfig.objects.all(), many=True
        )
        eng_configs = EngineerConfigSerializer(EngineerConfig.objects.all(), many=True)
        return Response(
            {
                "gen_configs": gen_configs.data,
                "storage_configs": storage_configs.data,
                "repair_configs": repair_configs.data,
                "eng_configs": eng_configs.data,
                "withdraw_config": WithdrawConfigSerializer(
                    WithdrawalConfig.objects.first()
                ).data,
                "rental_config": NFTRentalConfigSerializer(
                    NFTRentalConfig.objects.first()
                ).data,
                "gradation_config": GradationConfigSerializer(
                    GradationConfig.objects.all(), many=True
                ).data,
            },
            status=status.HTTP_200_OK,
        )


class RepairPowerStationConfigView(APIView):
    @swagger_auto_schema(
        tags=["station", "config"],
        operation_description="Отримати дані по конфігураціям станцій",
        responses={200: RepairPowerStationConfigSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        configs = RepairPowerStationConfig.objects.all()
        serializer = RepairPowerStationConfigSerializer(configs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GenPowerStationConfigView(APIView):
    @swagger_auto_schema(
        tags=["station", "config"],
        operation_description="Отримати дані по конфігураціям станцій",
        responses={200: GenPowerStationConfigSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        configs = GenPowerStationConfig.objects.all()
        serializer = GenPowerStationConfigSerializer(configs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StoragePowerStationConfigView(APIView):
    @swagger_auto_schema(
        tags=["station", "config"],
        operation_description="Отримати дані по конфігураціям станцій",
        responses={200: StoragePowerStationConfigSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        configs = StoragePowerStationConfig.objects.all()
        serializer = StoragePowerStationConfigSerializer(configs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EngineerConfigView(APIView):
    @swagger_auto_schema(
        tags=["station", "config"],
        operation_description="Отримати дані по Engineer",
        responses={200: EngineerConfigSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        configs = EngineerConfig.objects.all()
        serializer = EngineerConfigSerializer(configs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class RepairStationView(APIView):
    @swagger_auto_schema(
        tags=["station"],
        operation_description="Ремонт станції користувача",
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            action_logger.info(
                f"user {user_profile.user_id} | repair {user_profile.energy} kw, {user_profile.tbtc_wallet} tbtc"
            )
            base_cost_kw = RepairPowerStationConfig.objects.get(
                station_type=user_profile.station_type
            ).price_kw
            base_cost_tbtc = RepairPowerStationConfig.objects.get(
                station_type=user_profile.station_type
            ).price_tbtc
            repair_cost_kw = decimal.Decimal(
                100 - user_profile.power
            ) * decimal.Decimal(base_cost_kw)
            repair_cost_tbtc = decimal.Decimal(
                100 - user_profile.power
            ) * decimal.Decimal(base_cost_tbtc)

            # Проверяем активность Repair Kit
            is_repair_kit_active = (
                user_profile.repair_kit_expires
                and timezone.now() < user_profile.repair_kit_expires
            )

            if repair_cost_kw > 0 and user_profile.energy >= repair_cost_kw:
                GlobalSpendStats.objects.update(
                    energy_spent_repair=F("energy_spent_repair") + repair_cost_kw
                )
                update_data = {
                    "energy": F("energy") - repair_cost_kw,
                    "power": 100,
                }
                if is_repair_kit_active:
                    update_data["repair_kit_power_level"] = 100
                UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
                user_profile.refresh_from_db()
                return Response(
                    {
                        "message": "Station repaired successfully",
                        "cost_kw": repair_cost_kw,
                        "kw_wallet": user_profile.kw_wallet,
                        "energy": user_profile.energy,
                    },
                    status=status.HTTP_200_OK,
                )
            elif repair_cost_kw > 0 and user_profile.kw_wallet >= repair_cost_kw:
                GlobalSpendStats.objects.update(
                    energy_spent_repair=F("energy_spent_repair") + repair_cost_kw
                )
                update_data = {
                    "kw_wallet": F("kw_wallet") - repair_cost_kw,
                    "power": 100,
                }
                if is_repair_kit_active:
                    update_data["repair_kit_power_level"] = 100
                UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
                user_profile.refresh_from_db()
                return Response(
                    {
                        "message": "Station repaired successfully",
                        "cost_kw": repair_cost_kw,
                        "kw_wallet": user_profile.kw_wallet,
                        "energy": user_profile.energy,
                    },
                    status=status.HTTP_200_OK,
                )
            elif repair_cost_tbtc > 0 and user_profile.tbtc_wallet >= repair_cost_tbtc:
                GlobalSpendStats.objects.update(
                    tbtc_spent_repair=F("tbtc_spent_repair") + repair_cost_tbtc
                )
                update_data = {
                    "tbtc_wallet": F("tbtc_wallet") - repair_cost_tbtc,
                    "power": 100,
                }
                if is_repair_kit_active:
                    update_data["repair_kit_power_level"] = 100
                UserProfile.objects.filter(user_id=user_profile.user_id).update(**update_data)
                user_profile.refresh_from_db()
                return Response(
                    {
                        "message": "Station repaired successfully",
                        "cost_tbtc": repair_cost_tbtc,
                        "tbtc_wallet": user_profile.tbtc_wallet,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"error": "Not enough resources for repair"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


import pytoniq_core
from django.conf import settings
from pytoniq_core import Address, begin_cell
from tonutils.client import TonapiClient
from tonutils.jetton import JettonMaster, JettonWallet
from tonutils.wallet import WalletV5R1


async def send_tbtc(dest: str, amount: int, comment: str) -> None:
    JETTON_MASTER_ADDRESS = "EQBDdyCZeFFRoOmvEPZw3q_xuwGAb4qXgE2_q4WdmiBTnZLu"
    JETTON_DECIMALS = 4
    DESTINATION_ADDRESS = dest
    JETTON_AMOUNT = amount
    COMMENT = comment

    client = TonapiClient(
        api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
    )
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, settings.TBTC_MNEMONICS_SECRET.split())

    jetton_wallet_address = await JettonMaster.get_wallet_address(
        client=client,
        owner_address=wallet.address.to_str(),
        jetton_master_address=JETTON_MASTER_ADDRESS,
    )

    body = JettonWallet.build_transfer_body(
        recipient_address=Address(DESTINATION_ADDRESS),
        response_address=wallet.address,
        jetton_amount=int(JETTON_AMOUNT * (10**JETTON_DECIMALS)),
        forward_payload=(
            begin_cell()
            .store_uint(0, 32)  # Text comment opcode
            .store_snake_string(COMMENT)
            .end_cell()
        ),
        forward_amount=1,
    )

    tx_hash = await wallet.transfer(
        destination=jetton_wallet_address,
        amount=0.05,
        body=body,
    )

    return tx_hash


async def send_kw(dest: str, amount: int, comment: str) -> None:
    JETTON_MASTER_ADDRESS = "EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb"
    JETTON_DECIMALS = 9
    DESTINATION_ADDRESS = dest
    JETTON_AMOUNT = amount
    COMMENT = comment

    client = TonapiClient(
        api_key="AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
    )
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, settings.KW_MNEMONICS_SECRET.split())

    jetton_wallet_address = await JettonMaster.get_wallet_address(
        client=client,
        owner_address=wallet.address.to_str(),
        jetton_master_address=JETTON_MASTER_ADDRESS,
    )

    body = JettonWallet.build_transfer_body(
        recipient_address=Address(DESTINATION_ADDRESS),
        response_address=wallet.address,
        jetton_amount=int(JETTON_AMOUNT * (10**JETTON_DECIMALS)),
        forward_payload=(
            begin_cell()
            .store_uint(0, 32)  # Text comment opcode
            .store_snake_string(COMMENT)
            .end_cell()
        ),
        forward_amount=1,
    )

    tx_hash = await wallet.transfer(
        destination=jetton_wallet_address,
        amount=0.05,
        body=body,
    )

    return tx_hash


from django.db import transaction


class CreateWithdrawalRequestView(APIView):
    @swagger_auto_schema(
        tags=["withdraw"],
        operation_description="Створити запит на вивід kW або tBTC",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "user_id",
                "wallet_address",
                "token_amount",
                "token_contract_address",
            ],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "wallet_address": openapi.Schema(type=openapi.TYPE_STRING),
                "token_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "token_contract_address": openapi.Schema(type=openapi.TYPE_STRING),
                "is_mining": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                "is_staking": openapi.Schema(type=openapi.TYPE_BOOLEAN),
            },
        ),
        responses={
            200: openapi.Response(
                description="Запит на вивід створено успішно",
                examples={
                    "application/json": {
                        "message": "Withdrawal request created successfully",
                        "request_id": 1,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        return common_withdrawal(request)


def common_withdrawal(request):
    wallet_address = request.data.get("wallet_address")
    token_amount = request.data.get("token_amount")
    token_contract_address = request.data.get("token_contract_address")
    is_mining = request.data.get("is_mining", False)
    is_staking = request.data.get("is_staking", False)
    is_rent = request.data.get("is_rent", False)

    if not all([wallet_address, token_amount, token_contract_address]):
        return Response(
            {"error": "All fields are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_id = request.user_profile.user_id
    last_withdraw_time = cache.get(f"last_withdraw_{user_id}")

    if (
        last_withdraw_time
        and (timezone.now() - last_withdraw_time).total_seconds() < 5
    ):
        return Response(
            {"error": "Withdraw are too frequent. Please wait a moment."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    user_profile: UserProfile = request.user_profile
    cache.set(f"last_withdraw_{user_id}", timezone.now(), timeout=10)

    if token_contract_address not in [
        "EQDSYiFUtMVS9rhBDhbTfP-zbj_uqa69bHv6e5IberQH5n1N",
        "EQBOqBiArR45GUlifxdzZ40ZahdVhjtU7GjY-lVtqruHvQEc",
    ]:
        return Response(
            {"error": "Wrong token_contract_address"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        real_address = pytoniq_core.Address(wallet_address).to_str(
            is_user_friendly=False
        )
    except Exception:
        action_logger.info(
            f"wrong wallet address: {real_address}, need {request.user_profile.ton_wallet} for {request.user_profile.id}"
        )
    if real_address != request.user_profile.ton_wallet:
        action_logger.info(
            f"wrong wallet address: {real_address}, need {request.user_profile.ton_wallet} for {request.user_profile.id}"
        )
        return Response(
            {"error": "Wrong wallet address"}, status=status.HTTP_400_BAD_REQUEST
        )

    user_profile: UserProfile = request.user_profile
    energy = user_profile.energy
    tbtc_claimed_period = float(user_profile.tbtc_claimed_period)
    if is_mining:
        note = "withdraw"
    elif is_staking:
        note = "staking"
    elif is_rent:
        note = "rent"
    else:
        note = "claim"
    comment = ""
    is_auto = False

    withdraw_config = WithdrawalConfig.objects.first() or None
    min_kw = getattr(withdraw_config, "min_kw", 500)
    min_tbtc = getattr(withdraw_config, "min_tbtc", 50)
    min_claim = getattr(withdraw_config, "min_claim", 0)
    max_auto_kw = getattr(withdraw_config, "max_auto_kw", 10000)
    max_auto_tbtc = getattr(withdraw_config, "max_auto_tbtc", 500)
    max_auto_claim = getattr(withdraw_config, "max_auto_claim", 500)
    real_amount = 0
    min_staking_out = getattr(withdraw_config, "min_staking_out", 10)
    max_auto_staking_out = getattr(withdraw_config, "max_auto_staking_out", 0)
    commision_percent = 0

    min_rent = getattr(withdraw_config, "min_rent", 10)
    max_auto_rent = getattr(withdraw_config, "max_auto_rent", 1000)
    wallet_info = WalletInfo.objects.filter(user=user_profile, wallet=user_profile.ton_wallet).first()

    try:
        last_request = (
            WithdrawalRequest.objects.filter(
                user=user_profile,
                token_contract_address=token_contract_address,
                note=note,
            )
            .order_by("-claimed_at")
            .first()
        )
        if last_request and (timezone.now() - last_request.claimed_at).days < 1:
            return Response(
                {
                    "error": "You can only make one withdrawal request per day",
                    "last_date": last_request.claimed_at,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            token_contract_address
            == "EQDSYiFUtMVS9rhBDhbTfP-zbj_uqa69bHv6e5IberQH5n1N"
        ):
            token_type = "kw"
            if user_profile.energy < token_amount or token_amount < min_kw or (wallet_info and wallet_info.kw_amount < token_amount):
                return Response(
                    {"error": "Not enough kW in wallet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                UserProfile.objects.filter(user_id=user_profile.user_id).update(
                    energy=F("energy") - token_amount
                )
                WalletInfo.objects.filter(
                    user=user_profile, wallet=user_profile.ton_wallet
                ).update(kw_amount=F("kw_amount") - token_amount)
            commision_percent = user_profile.sbt_get_kw_commision()
            if token_amount < max_auto_kw:
                real_amount = token_amount * (1 - commision_percent)
                add_kw_commission(token_amount - real_amount)
                tx_hash = ""
                comment = f"Mint {user_profile.user_id}"
                # try:
                #     tx_hash = async_to_sync(send_kw)(
                #         wallet_address, real_amount, f"Mint {user_profile.user_id}"
                #     )
                # except Exception as e:
                #     tx_hash = "error"
                #     action_logger.exception("Error mint")
                action_logger.info(
                    f"AUTOCLAIM {wallet_address}, {real_amount}, Mint {user_profile.user_id}, {tx_hash}"
                )
                is_auto = True
        else:
            token_type = "tbtc"
            if is_mining:
                with transaction.atomic():
                    try:
                        requested_amount = float(token_amount)
                    except (TypeError, ValueError):
                        return Response(
                            {"error": "Invalid token_amount"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    total_mined_tokens_balance = (
                        user_profile.total_mined_tokens_balance()
                    )
                    if total_mined_tokens_balance <= 0:
                        return Response(
                            {"error": "Not enough tBTC in wallet 2"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    withdraw_gross = min(requested_amount, total_mined_tokens_balance)

                    if withdraw_gross < min_claim:
                        return Response(
                            {"error": "Not enough tBTC in wallet 2"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )

                    ratio = withdraw_gross / total_mined_tokens_balance if total_mined_tokens_balance else 0

                    mined_main_take = user_profile.mined_tokens_balance * ratio
                    mined_s21_take = user_profile.mined_tokens_balance_s21 * ratio
                    mined_sx_take = user_profile.mined_tokens_balance_sx * ratio

                    commision_percent = user_profile.sbt_get_claim_commision()
                    low_sum = withdraw_gross < 100
                    apply_comission = lambda t: t - 1 if low_sum else t * (1-commision_percent)

                    token_amount_s21 = (1-commision_percent) * mined_s21_take
                    token_amount_sx = (1-commision_percent) * mined_sx_take
                    token_amount = (
                        apply_comission(mined_main_take)
                        + token_amount_s21
                        + token_amount_sx
                    )
                    UserProfile.objects.filter(user_id=user_profile.user_id).update(
                        mined_tokens_balance=F("mined_tokens_balance") - mined_main_take,
                        mined_tokens_balance_s21=F("mined_tokens_balance_s21") - mined_s21_take,
                        mined_tokens_balance_sx=F("mined_tokens_balance_sx") - mined_sx_take,
                        tbtc_claimed_period=F("tbtc_claimed_period") + token_amount,
                    )
                    WalletInfo.objects.filter(
                        user=user_profile, wallet=user_profile.ton_wallet
                    ).update(
                        tbtc_amount=F("tbtc_amount") - mined_main_take,
                        tbtc_amount_s21=F("tbtc_amount_s21") - mined_s21_take,
                        tbtc_amount_sx=F("tbtc_amount_sx") - mined_sx_take
                    )

                    # today = timezone.now().date()
                    # next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=2)
                    # if today.day > 3
                    # S21 AND ULTRA ASICS STAKING - Вимкн: 100% йде на моментальний вивід
                    # staking_30 = SpecialAsicStaking.objects.filter(
                    #     days=30,
                    #     user=user_profile,
                    #     end_date__gt=timezone.now(),
                    # ).first()
                    # if staking_30:
                    #     SpecialAsicStaking.objects.filter(id=staking_30.id).update(
                    #         token_amount=F("token_amount")
                    #         + token_amount_s21 * 0.25
                    #         + token_amount_sx * 0.25,
                    #     )
                    # else:
                    #     SpecialAsicStaking.objects.create(
                    #         user=user_profile,
                    #         token_amount=token_amount_s21 * 0.25
                    #         + token_amount_sx * 0.25,
                    #         start_date=timezone.now(),
                    #         end_date=timezone.now() + timedelta(days=30),
                    #         days=30,
                    #         apr=25,
                    #     )

                    # staking_90 = SpecialAsicStaking.objects.filter(
                    #     days=90,
                    #     user=user_profile,
                    #     end_date__gt=timezone.now(),
                    # ).first()
                    # if staking_90:
                    #     SpecialAsicStaking.objects.filter(id=staking_90.id).update(
                    #         token_amount=F("token_amount")
                    #         + token_amount_s21 * 0.25
                    #         + token_amount_sx * 0.25,
                    #     )
                    # else:
                    #     SpecialAsicStaking.objects.create(
                    #         user=user_profile,
                    #         token_amount=token_amount_s21 * 0.25
                    #         + token_amount_sx * 0.25,
                    #         start_date=timezone.now(),
                    #         end_date=timezone.now() + timedelta(days=90),
                    #         days=90,
                    #         apr=35,
                    #     )

                    # staking_180 = SpecialAsicStaking.objects.filter(
                    #     days=180,
                    #     user=user_profile,
                    #     end_date__gt=timezone.now(),
                    # ).first()
                    # if staking_180:
                    #     SpecialAsicStaking.objects.filter(id=staking_180.id).update(
                    #         token_amount=F("token_amount")
                    #         + token_amount_s21 * 0.25
                    #         + token_amount_sx * 0.25,
                    #     )
                    # else:
                    #     SpecialAsicStaking.objects.create(
                    #         user=user_profile,
                    #         token_amount=token_amount_s21 * 0.25
                    #         + token_amount_sx * 0.25,
                    #         start_date=timezone.now(),
                    #         end_date=timezone.now() + timedelta(days=180),
                    #         days=180,
                    #         apr=50,
                    #     )

                MiningStats.objects.update(
                    total_tbtc_claimed=F("total_tbtc_claimed") + token_amount
                )
                if token_amount < max_auto_claim:
                    commission_amount = max(0, withdraw_gross - token_amount)
                    real_amount = token_amount
                    # if token_amount < 100:
                    #     real_amount = token_amount - 1
                    # else:
                    #     real_amount = token_amount * 0.99
                    add_tbtc_commission(commission_amount)
                    tx_hash = ""
                    comment = f"Claim {user_profile.user_id}"
                    # try:
                    #     tx_hash = async_to_sync(send_tbtc)(
                    #         wallet_address,
                    #         real_amount,
                    #         f"Claim {user_profile.user_id}",
                    #     )
                    # except Exception as e:
                    #     tx_hash = "error"
                    #     action_logger.exception("Error claim")
                    action_logger.info(
                        f"AUTOCLAIM {wallet_address}, {real_amount}, Claim {user_profile.user_id}, {tx_hash}"
                    )
                    is_auto = True
            else:
                token_type = "staking"
                if is_staking:
                    now = timezone.now()
                    stakings = UserStaking.objects.filter(
                        user=user_profile,
                        last_collected__lt=F("end_date"),
                        confirmed=True,
                    )
                    info = []
                    token_amount = decimal.Decimal(0)
                    for s in stakings:
                        curr = now
                        if s.end_date < now:
                            curr = s.end_date
                        days_passed = (
                            decimal.Decimal(
                                (curr - s.last_collected).total_seconds()
                            )
                            / 24
                            / 60
                            / 60
                        )
                        daily_profit = (
                            decimal.Decimal(s.token_amount)
                            * decimal.Decimal(s.apr)
                            / 100
                            / 365
                        )
                        collected = daily_profit * days_passed
                        token_amount += collected
                        info.append([collected, s.id])

                    with transaction.atomic():
                        if token_amount <= min_staking_out:
                            return Response(
                                {"error": "Not enough staking"},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        for num, i in info:
                            UserStaking.objects.filter(id=i).update(
                                last_collected=now,
                                collected=F("collected") + num,
                            )
                    try:
                        if user_profile.referrer:
                            UserProfile.objects.filter(
                                user_id=user_profile.referrer.user_id
                            ).update(
                                bonus_invest_level_1=F("bonus_invest_level_1")
                                + token_amount * decimal.Decimal(0.05)
                            )

                            UserProfile.objects.filter(
                                user_id=user_profile.user_id
                            ).update(
                                bring_bonus_invest_level_1=F(
                                    "bring_bonus_invest_level_1"
                                )
                                + token_amount * decimal.Decimal(0.05)
                            )

                            if user_profile.referrer_level_2:
                                UserProfile.objects.filter(
                                    user_id=user_profile.referrer_level_2.user_id
                                ).update(
                                    bonus_invest_level_2=F("bonus_invest_level_2")
                                    + token_amount * decimal.Decimal(0.02)
                                )

                                UserProfile.objects.filter(
                                    user_id=user_profile.referrer.user_id
                                ).update(
                                    bring_bonus_invest_level_2=F(
                                        "bring_bonus_invest_level_2"
                                    )
                                    + token_amount * decimal.Decimal(0.02)
                                )

                    except Exception as e:
                        pass
                    if token_amount < max_auto_staking_out:
                        tx_hash = ""
                        comment = f"tBTC staking earnings {user_profile.user_id}"
                        real_amount = token_amount
                        # try:
                        #     tx_hash = async_to_sync(send_tbtc)(
                        #         wallet_address,
                        #         real_amount,
                        #         f"Claim {user_profile.user_id}",
                        #     )
                        # except Exception as e:
                        #     tx_hash = "error"
                        #     action_logger.exception("Error claim")
                        action_logger.info(
                            f"AUTOCLAIM {wallet_address}, {real_amount}, Claim {user_profile.user_id}, {tx_hash}"
                        )
                        is_auto = True
                else:
                    token_type = "rent"
                    if is_rent:
                        token_amount = user_profile.rent_mined_tokens_balance
                        if token_amount < min_rent:
                            return Response(
                                {"error": "Not enough rent in wallet"},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        with transaction.atomic():
                            UserProfile.objects.filter(
                                user_id=user_profile.user_id
                            ).update(rent_mined_tokens_balance=0)
                        commision_percent = user_profile.sbt_get_claim_commision()
                        if token_amount < max_auto_rent:
                            tx_hash = ""
                            comment = f"Rent {user_profile.user_id}"
                            # try:
                            #     tx_hash = async_to_sync(send_kw)(
                            #         wallet_address, real_amount, f"Mint {user_profile.user_id}"
                            #     )
                            # except Exception as e:
                            #     tx_hash = "error"
                            #     action_logger.exception("Error mint")
                            action_logger.info(
                                f"AUTOCLAIM {wallet_address}, {real_amount}, Rent {user_profile.user_id}, {tx_hash}"
                            )
                            is_auto = True
                    else:
                        return Response(
                            {"error": "Not active"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                        if (
                            user_profile.tbtc_wallet < token_amount
                            or token_amount < min_tbtc
                        ):
                            return Response(
                                {"error": "Not enough tBTC in wallet"},
                                status=status.HTTP_400_BAD_REQUEST,
                            )
                        UserProfile.objects.filter(
                            user_id=user_profile.user_id
                        ).update(
                            tbtc_wallet=F("tbtc_wallet") - token_amount,
                            tbtc_claimed_period=0,
                        )
                # if token_amount < max_auto_tbtc:
                #     if token_amount < 100:
                #         real_amount = token_amount - 1
                #     else:
                #         real_amount = token_amount * 0.99
                # add_tbtc_commission(token_amount - real_amount)
                # try:
                #     tx_hash = async_to_sync(send_tbtc)(
                #         wallet_address,
                #         real_amount,
                #         f"Withdraw {user_profile.user_id}",
                #     )
                # except Exception as e:
                #     tx_hash = "error"
                #     action_logger.exception("Error withdraw")
                # action_logger.info(
                #     f"AUTOCLAIM {wallet_address}, {real_amount}, Withdraw {user_profile.user_id}, {tx_hash}"
                # )
                # is_auto = True

        user_profile.refresh_from_db()
        if is_auto:
            AutoWithdrawalRequest.objects.create(
                user=user_profile,
                username=user_profile.username,
                token_amount_full=token_amount,
                token_amount=real_amount,
                token_type=token_type,
                claimed_at=timezone.now(),
                status="wait_auto",
                tx_id=tx_hash,
                wallet_address=wallet_address,
                comment=comment,
            )

        withdrawal_request = WithdrawalRequest.objects.create(
            user=user_profile,
            wallet_address=wallet_address,
            token_amount=token_amount,
            token_contract_address=token_contract_address,
            claimed_at=timezone.now(),
            is_auto=is_auto,
            energy=energy,
            station_type=user_profile.station_type,
            generation_level=user_profile.generation_level,
            storage_level=user_profile.storage_level,
            generation_rate=user_profile.generation_rate,
            tbtc_left=user_profile.mined_tokens_balance,
            tbtc_claimed_period=tbtc_claimed_period,
            note=note,
            commision_percent=commision_percent,
        )
        return Response(
            {
                "message": "Withdrawal request created successfully",
                "request_id": withdrawal_request.id,
            },
            status=status.HTTP_200_OK,
        )
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        action_logger.exception(
            f"Error creating withdrawal request for {user_id} | {real_amount} {token_type} | {wallet_address}"
        )
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(APIView):
    @swagger_auto_schema(
        tags=["profile"],
        operation_description="Отримати інформацію про профіль користувача",
        responses={
            200: openapi.Response(
                description="Інформація про профіль користувача",
                schema=UserProfileSerializer(),
            ),
            404: "Користувача не знайдено",
        },
    )
    @require_auth
    def get(self, request):
        try:
            serializer = UserProfileSerializer(request.user_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK


class ReferralInfoPagination(PageNumberPagination):
    page_size = 100  # Default number of referrals per page
    page_size_query_param = (
        "page_size"  # Allow client to specify the number of referrals per page
    )
    max_page_size = 200  # Set a maximum limit for page size


import django_filters
from django.db.models import F, Sum


class UserProfileFilter(django_filters.FilterSet):
    class Meta:
        model = UserProfile
        fields = []
        order_by = [
            "bonus_kw_level_1",
            "bonus_tbtc_level_1",
            "nft_count",
        ]


from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.generics import ListAPIView


class ReferralInfoView(ListAPIView):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = [
        "bonus_kw_level_1",
        "bonus_tbtc_level_1",
        "bring_bonus_kw_level_1",
        "bring_bonus_tbtc_level_1",
        "nft_count",
    ]
    pagination_class = ReferralInfoPagination

    @swagger_auto_schema(
        tags=["referral"],
        operation_description="Отримати інформацію про рефералів користувача та скільки вони принесли бонусів",
        responses={
            200: openapi.Response(
                description="Інформація про рефералів користувача",
            ),
            404: "Користувача не знайдено",
        },
    )
    @require_auth
    def get(self, request):
        user_profile: UserProfile = request.user_profile

        # Fetch all referrals for the user
        referrals = user_profile.referrals.all()

        # Apply filters and ordering
        filtered_referrals = self.filter_queryset(referrals)

        # Apply pagination
        paginated_referrals: list[UserProfile] = self.paginate_queryset(
            filtered_referrals
        )

        # Prepare referral data
        referral_data = [
            {
                "user_id": referral.user_id,
                "username": referral.username or "",
                "name": referral.first_name or "",
                "bonus_kw_level_1": round(referral.bring_bonus_kw_level_1, 2),
                "bonus_kw_level_2": round(referral.bring_bonus_kw_level_2, 2),
                "bonus_tbtc_level_1": round(referral.bring_bonus_tbtc_level_1, 2),
                "bonus_tbtc_level_2": round(referral.bring_bonus_tbtc_level_2, 2),
                "bonus_investor_level_1": round(referral.bring_bonus_invest_level_1, 2),
                "bonus_investor_level_2": round(referral.bring_bonus_invest_level_2, 2),
                "nft_count": referral.nft_count,
            }
            for referral in paginated_referrals
        ]

        first_level_count = UserProfile.objects.filter(referrer=user_profile).count()
        second_level_count = UserProfile.objects.filter(
            referrer_level_2=user_profile
        ).count()

        return Response(
            {
                "referrals": referral_data,
                "total_bonus_kw": user_profile.bonus_kw_level_1
                + user_profile.bonus_kw_level_2,
                "total_bonus_tbtc": user_profile.bonus_tbtc_level_1
                + user_profile.bonus_tbtc_level_2,
                "total_staking_bonus": user_profile.bonus_invest_level_1
                + user_profile.bonus_invest_level_2,
                "first_level_count": first_level_count,
                "second_level_count": second_level_count,
            },
            status=status.HTTP_200_OK,
        )


def start_mining_common(request):
    user_profile: UserProfile = request.user_profile
    action_logger.info(
        f"starting mining user {user_profile.user_id} | {user_profile.kw_wallet} kw"
    )
    if user_profile.is_mining:
        return Response(
            {"error": "Mining is already running"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    has_at_least_one_rented_nft = NFTRentalAgreement.objects.filter(
        renter=user_profile, end_date__gte=timezone.now()
    ).exists()
    all_nfts_in_work = (
        len(user_profile.nft_string.split(";"))
        == NFTRentalAgreement.objects.filter(owner=user_profile).count()
    )
    if (not has_at_least_one_rented_nft) and (
        all_nfts_in_work or user_profile.nft_string == ""
    ):
        return Response(
            {"error": "No NFT"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if user_profile.rent_farm_consumption_plus * 24 > user_profile.kw_wallet:
        user_profile.remove_point()
        return Response(
            {"error": "Not enough kW in wallet"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user_profile.upd_stopper()

    booster = Booster.objects.filter(slug="magnit").first()
    magnit_percent = float(getattr(booster, "n1", 20))

    user_profile.recalc_rent()

    farm_consumption = (
        user_profile.total_farm_consumption
        - user_profile.rent_farm_consumption_minus
        + user_profile.rent_farm_consumption_plus
    )

    if user_profile.is_powerbank_active:
        farm_consumption -= user_profile.powerbank_max_consume

    energy_saved_magnet = 0
    if user_profile.premium_sub_expires and user_profile.premium_sub_expires > timezone.now():
        magnit_percent = 24
    if user_profile.magnit_expires and user_profile.magnit_expires > timezone.now():
        energy_saved_magnet = farm_consumption * (magnit_percent / 100)
        farm_consumption = farm_consumption * (1 - magnit_percent / 100)

    if farm_consumption <= 0:
        farm_consumption = 1

    if farm_consumption > user_profile.kw_wallet:
        if farm_consumption / 2 > user_profile.kw_wallet:
            return Response(
                {"error": "Not enough kW in wallet"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                kw_wallet=F("kw_wallet") - farm_consumption / 2,
                battery_balance=farm_consumption / 2,
                mining_period=1800,
                is_mining=True,
                started_mining_at=timezone.now(),
                true_started_mining_at=timezone.now(),
                last_tbtc_added=timezone.now(),
                farm_runtime=F("kw_wallet") / float(farm_consumption),
                # mining_was_stopped=False,
            )
            add_mining_commission(farm_consumption / 2)
            MiningStats.objects.update(
                energy_spent_mining=F("energy_spent_mining") + farm_consumption / 2
            )
    else:
        UserProfile.objects.filter(user_id=user_profile.user_id).update(
            kw_wallet=F("kw_wallet") - farm_consumption,
            battery_balance=farm_consumption,
            mining_period=3600,
            is_mining=True,
            started_mining_at=timezone.now(),
            true_started_mining_at=timezone.now(),
            last_tbtc_added=timezone.now(),
            farm_runtime=F("kw_wallet") / float(farm_consumption),
            # mining_was_stopped=False,
        )
        add_mining_commission(farm_consumption)
        MiningStats.objects.update(
            energy_spent_mining=F("energy_spent_mining") + farm_consumption
        )
    if user_profile.is_powerbank_active:
        UserProfile.objects.filter(user_id=user_profile.user_id).update(
            is_powerbank_active=False,
            powerbank_activated=timezone.now(),
        )
        MiningStats.objects.update(
            energy_saved_powerbank=F("energy_saved_powerbank")
            + user_profile.powerbank_max_consume
        )
    MiningStats.objects.update(
        energy_saved_magnet=F("energy_saved_magnet") + energy_saved_magnet
    )

    user_profile.refresh_from_db()
    action_logger.info(
        f"started mining user {user_profile.user_id} | {user_profile.kw_wallet} kw | {farm_consumption} consumption | mining period {user_profile.mining_period}"
    )
    return None


class StartMiningView(APIView):
    @swagger_auto_schema(
        tags=["mining"],
        operation_description="Запуск майнінг ферми",
        responses={
            200: openapi.Response(
                description="Майнінг ферму запущено",
                examples={
                    "application/json": {
                        "message": "Mining started",
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            returned = start_mining_common(request)
            request.user_profile.refresh_from_db()
            if returned is not None:
                return returned
            return Response(
                {
                    "message": "Mining started",
                    "kw_wallet": request.user_profile.kw_wallet,
                    "user": UserProfileSerializer(request.user_profile).data,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class StopMiningView(APIView):
    @swagger_auto_schema(
        tags=["mining"],
        operation_description="Зупинка майнінг ферми",
        responses={
            200: openapi.Response(
                description="Майнінг ферму зупинено",
                examples={
                    "application/json": {
                        "message": "Mining stopped",
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile = request.user_profile
            if not user_profile.is_mining:
                return Response(
                    {"error": "Mining is not running"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            action_logger.info(f"manual mining stop {user_profile.user_id}")
            user_profile.stop_mining("manual stop")
            return Response({"message": "Mining stopped"}, status=status.HTTP_200_OK)
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class EnergyRunStartView(APIView):
    """Записывает старт сбора энергии (раннер). Следующий старт разрешён через 60 минут."""

    @require_auth
    def post(self, request):
        try:
            user_profile = request.user_profile
            now = timezone.now()
            cooldown_minutes = 60
            next_allowed = None
            if user_profile.energy_run_last_started_at:
                next_allowed = user_profile.energy_run_last_started_at + timedelta(
                    minutes=cooldown_minutes
                )
                if now < next_allowed:
                    return Response(
                        {
                            "error": "energy_run_cooldown",
                            "next_available_at": next_allowed.isoformat(),
                            "next_available_in_seconds": max(
                                0, int((next_allowed - now).total_seconds())
                            ),
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            # Сохраняем текущее значение storage и обнуляем его
            from decimal import Decimal
            current_storage = user_profile.storage
            # Логирование убрано для оптимизации - логируем только ошибки
            # action_logger.info(
            #     f"Energy run start: user_id={user_profile.user_id}, "
            #     f"current_storage={current_storage}, energy_run_last_started_at={now}"
            # )
            
            # Сохраняем данные в БД
            updated_count = UserProfile.objects.filter(user_id=user_profile.user_id).update(
                energy_run_last_started_at=now,
                energy_run_start_storage=Decimal(str(current_storage)),
                storage=Decimal('0')
            )
            # Логирование убрано для оптимизации - логируем только ошибки
            # action_logger.info(
            #     f"Energy run start DB update: user_id={user_profile.user_id}, "
            #     f"updated_count={updated_count}"
            # )
            
            # ОПТИМИЗАЦИЯ: Убираем лишний запрос к БД - данные уже обновлены через update()
            # Получаем обновленный объект только если нужны данные для ответа
            user_profile = UserProfile.objects.get(user_id=user_profile.user_id)
            # Логирование убрано для оптимизации - логируем только ошибки
            # action_logger.info(
            #     f"Energy run start after DB get: user_id={user_profile.user_id}, "
            #     f"energy_run_last_started_at={user_profile.energy_run_last_started_at}, "
            #     f"storage={user_profile.storage}, "
            #     f"energy_run_start_storage={user_profile.energy_run_start_storage}"
            # )
            
            serializer_data = UserProfileSerializer(user_profile).data
            action_logger.info(
                f"Energy run start response: user_id={user_profile.user_id}, "
                f"energy_run_last_started_at={user_profile.energy_run_last_started_at}, "
                f"storage={user_profile.storage}, "
                f"serializer_energy_run_last_started_at={serializer_data.get('energy_run_last_started_at')}"
            )
            return Response(
                {
                    "message": "Energy run started",
                    "user": serializer_data,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            action_logger.error(
                f"Energy run start error: UserProfile.DoesNotExist for user_id={request.user_profile.user_id if hasattr(request, 'user_profile') else 'unknown'}"
            )
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            action_logger.error(
                f"Energy run start error: {str(e)}, traceback: {traceback.format_exc()}"
            )
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GameRunCompleteView(APIView):
    """Завершение забега и начисление энергии"""
    
    @swagger_auto_schema(
        tags=["game"],
        operation_description="Завершение 3D забега и начисление энергии",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["distance", "energy_collected", "run_duration", "is_win"],
            properties={
                "distance": openapi.Schema(type=openapi.TYPE_NUMBER, description="Пройденное расстояние"),
                "energy_collected": openapi.Schema(type=openapi.TYPE_NUMBER, description="Собранная энергия"),
                "run_duration": openapi.Schema(type=openapi.TYPE_NUMBER, description="Длительность забега в секундах"),
                "obstacles_hit": openapi.Schema(type=openapi.TYPE_INTEGER, description="Количество препятствий"),
                "power_used": openapi.Schema(type=openapi.TYPE_NUMBER, description="Использованная мощность"),
                "is_win": openapi.Schema(type=openapi.TYPE_BOOLEAN, description="Победа (True) или проигрыш (False)"),
                "collected_points": openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    description="Массив собранных поинтов энергии для проверки (защита от подмены данных)",
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            "value": openapi.Schema(type=openapi.TYPE_NUMBER, description="Значение поинта в kW"),
                            "timestamp_ms": openapi.Schema(type=openapi.TYPE_INTEGER, description="Время сбора поинта в миллисекундах от начала забега"),
                        }
                    )
                ),
            },
        ),
        responses={
            200: openapi.Response(
                description="Забег успешно завершен",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Run completed successfully",
                        "energy_gained": 45.3,
                        "total_energy": 150.5,
                        "storage": 0,
                        "power": 95.0,
                    }
                },
            ),
            400: "Ошибка валидации или забег не был начат",
        },
    )
    @require_auth
    def post(self, request):
        try:
            # Перезагружаем user_profile из базы данных, чтобы получить актуальные данные
            # (request.user_profile может быть кэшированным)
            user_profile = UserProfile.objects.get(user_id=request.user_profile.user_id)
            now = timezone.now()
            
            # Логирование входа в метод (только для отладки, можно убрать в продакшене)
            # action_logger.info(
            #     f"GameRunCompleteView POST received: user_id={user_profile.user_id}, "
            #     f"request.data={request.data}"
            # )
            
            # Получаем данные из запроса
            distance = request.data.get("distance", 0)
            energy_collected = request.data.get("energy_collected", 0)
            run_duration = request.data.get("run_duration", 0)
            obstacles_hit = request.data.get("obstacles_hit", 0)
            power_used = request.data.get("power_used", 0)
            is_win = request.data.get("is_win", False)
            collected_points = request.data.get("collected_points", [])  # Массив собранных поинтов для проверки
            
            # Валидация 1: Проверка что забег был начат
            # Логирование убрано для оптимизации - логируем только ошибки
            if not user_profile.energy_run_last_started_at:
                action_logger.warning(
                    f"GameRunCompleteView validation 1 FAILED: Run not started for user {user_profile.user_id}"
                )
                return Response(
                    {"error": "Run not started. Please start a run first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Валидация 2: Проверка что забег был начат не более 2 часов назад
            time_since_start = (now - user_profile.energy_run_last_started_at).total_seconds()
            # Логирование убрано для оптимизации - логируем только ошибки
            if time_since_start > 7200:  # 2 часа
                action_logger.warning(
                    f"GameRunCompleteView validation 2 FAILED: Run expired for user {user_profile.user_id}, "
                    f"time_since_start={time_since_start}"
                )
                return Response(
                    {"error": "Run expired. Please start a new run."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Валидация 3: Проверка что energy_run_start_storage существует
            # Логирование убрано для оптимизации - логируем только ошибки
            if user_profile.energy_run_start_storage is None:
                action_logger.warning(
                    f"GameRunCompleteView validation 3 FAILED: Run data not found for user {user_profile.user_id}"
                )
                return Response(
                    {"error": "Run data not found. Please start a new run."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Валидация 4: Проверка собранной энергии
            energy_collected = float(energy_collected)
            # Логирование убрано для оптимизации - логируем только ошибки
            if energy_collected < 0:
                action_logger.warning(
                    f"GameRunCompleteView validation 4 FAILED: Invalid energy_collected {energy_collected} "
                    f"for user {user_profile.user_id}"
                )
                return Response(
                    {"error": "Invalid energy_collected value"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            max_energy = float(user_profile.energy_run_start_storage)
            # Логирование убрано для оптимизации - логируем только ошибки
            if energy_collected > max_energy:
                action_logger.warning(
                    f"GameRunCompleteView validation 4b FAILED: Energy collected {energy_collected} "
                    f"exceeds max {max_energy} for user {user_profile.user_id}"
                )
                return Response(
                    {
                        "error": "Energy collected exceeds maximum allowed",
                        "max_allowed": max_energy,
                        "provided": energy_collected,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Валидация 4c: Проверка соответствия energy_collected и суммы собранных поинтов (защита от подмены)
            if collected_points and isinstance(collected_points, list):
                from decimal import Decimal
                # ОПТИМИЗАЦИЯ: Ограничиваем обработку до 200 поинтов (разумный максимум)
                points_to_check = collected_points[:200] if len(collected_points) > 200 else collected_points
                
                # Проверка 4c1: Валидация структуры поинтов
                valid_points = []
                for i, point in enumerate(points_to_check):
                    # Поддерживаем как новый формат (только value), так и старый (value + timestamp_ms)
                    if isinstance(point, dict):
                        point_value = float(point.get("value", 0))
                    elif isinstance(point, (int, float)):
                        # Поддержка упрощенного формата - просто число
                        point_value = float(point)
                    else:
                        action_logger.warning(
                            f"GameRunCompleteView validation 4c1 FAILED: Invalid point format at index {i} "
                            f"for user {user_profile.user_id}"
                        )
                        return Response(
                            {"error": f"Invalid point format at index {i}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    
                    if point_value <= 0 or point_value > max_energy:
                        # Логируем только критичные ошибки валидации
                        action_logger.warning(
                            f"GameRunCompleteView validation 4c1 FAILED: Invalid point value {point_value} "
                            f"at index {i} (max={max_energy}) for user {user_profile.user_id}"
                        )
                        return Response(
                            {"error": f"Invalid point value {point_value} at index {i}"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                    valid_points.append(point_value)
                
                # Проверка 4c2: Вычисляем сумму собранных поинтов
                points_sum = sum(valid_points)
                # Округляем до 2 знаков для сравнения (как на клиенте)
                points_sum_rounded = round(points_sum, 2)
                energy_collected_rounded = round(float(energy_collected), 2)
                
                # Допускаем небольшую погрешность из-за округления (0.01 kW)
                tolerance = 0.01
                difference = abs(points_sum_rounded - energy_collected_rounded)
                
                # Логирование убрано для оптимизации - логируем только ошибки
                if difference > tolerance:
                    action_logger.warning(
                        f"GameRunCompleteView validation 4c2 FAILED: Energy collected {energy_collected_rounded} "
                        f"does not match sum of collected points {points_sum_rounded} "
                        f"(difference={difference}) for user {user_profile.user_id}"
                    )
                    return Response(
                        {
                            "error": "Energy collected does not match collected points",
                            "energy_collected": energy_collected_rounded,
                            "points_sum": points_sum_rounded,
                            "difference": difference,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                
                # Проверка 4c3: Проверка что сумма поинтов не превышает максимум
                if points_sum_rounded > max_energy + tolerance:
                    action_logger.warning(
                        f"GameRunCompleteView validation 4c3 FAILED: Points sum {points_sum_rounded} "
                        f"exceeds max {max_energy} for user {user_profile.user_id}"
                    )
                    return Response(
                        {
                            "error": "Sum of collected points exceeds maximum allowed",
                            "points_sum": points_sum_rounded,
                            "max_allowed": max_energy,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                # Если массив поинтов не передан, логируем предупреждение только периодически (для старых клиентов)
                # Но не блокируем запрос, чтобы не сломать старые версии клиента
                # ОПТИМИЗАЦИЯ: Логируем только каждое 10-е предупреждение чтобы не засорять логи
                import random
                if random.randint(1, 10) == 1:  # 10% вероятность логирования
                    action_logger.warning(
                        f"GameRunCompleteView validation 4c WARNING: collected_points not provided or invalid "
                        f"for user {user_profile.user_id}, skipping validation (consider updating client)"
                    )
            
            # Валидация 5: Проверка времени забега (5 секунд - 2 часа)
            run_duration = float(run_duration)
            # Логирование убрано для оптимизации - логируем только ошибки
            if run_duration < 5 or run_duration > 7200:
                action_logger.warning(
                    f"GameRunCompleteView validation 5 FAILED: Invalid run_duration {run_duration} "
                    f"for user {user_profile.user_id}"
                )
                return Response(
                    {"error": "Invalid run_duration. Must be between 5 and 7200 seconds."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Валидация 6: Проверка дистанции
            distance = float(distance)
            # Логирование убрано для оптимизации - логируем только ошибки
            if distance <= 0:
                action_logger.warning(
                    f"GameRunCompleteView validation 6 FAILED: Invalid distance {distance} "
                    f"for user {user_profile.user_id}"
                )
                return Response(
                    {"error": "Invalid distance value"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Расчет финального количества энергии
            if is_win:
                # При победе начисляем всю собранную энергию
                final_energy = energy_collected
            else:
                # При проигрыше применяем процент сохранения от уровня инженера
                # Используем get_real_engs() который правильно учитывает все уровни (включая gold и electrics)
                engineer_level = user_profile.get_real_engs()
                try:
                    eng_config = EngineerConfig.objects.get(level=engineer_level)
                    saved_percent = eng_config.saved_percent_on_lose or 0
                except EngineerConfig.DoesNotExist:
                    saved_percent = 0
                
                # Бонус +2% если есть активные синие электрики
                # Проверяем напрямую electrics_expires вместо несуществующего метода get_active_boosts()
                if user_profile.electrics_expires and user_profile.electrics_expires > now:
                    saved_percent += 2
                
                # Ограничиваем процент максимумом 100%
                saved_percent = min(saved_percent, 100)
                
                final_energy = energy_collected * (saved_percent / 100)
                
                # Логирование убрано для оптимизации - логируем только финальный результат
                # action_logger.info(
                #     f"GameRunCompleteView loss calculation: user_id={user_profile.user_id}, "
                #     f"engineer_level={engineer_level}, saved_percent={saved_percent}, "
                #     f"energy_collected={energy_collected}, final_energy={final_energy}"
                # )
            
            # Преобразуем final_energy в Decimal для корректной работы с F()
            from decimal import Decimal
            final_energy_decimal = Decimal(str(final_energy))
            
            # Логирование только финального результата (минимизировано для оптимизации)
            # Логируем только важные события и ошибки
            if final_energy_decimal <= 0:
                action_logger.warning(
                    f"Energy run complete: final_energy is 0 or negative for user {user_profile.user_id}, "
                    f"energy_collected={energy_collected}, is_win={is_win}"
                )
            
            # НЕ начисляем энергию здесь - только сохраняем данные забега
            # Начисление будет происходить при нажатии кнопки "Забрать" через GameRunClaimView
            # Сохраняем данные забега для последующего начисления:
            # - energy_run_start_storage остается (для валидации)
            # - energy_run_last_started_at остается (для проверки что забег был начат)
            
            # ОПТИМИЗАЦИЯ: Убираем лишний запрос к БД - данные не изменились
            # user_profile уже загружен в начале метода и не изменялся
            # user_profile = UserProfile.objects.get(user_id=user_profile.user_id)
            
            return Response(
                {
                    "success": True,
                    "message": "Run completed successfully. Click 'Claim' to receive energy.",
                    "energy_collected": float(energy_collected),
                    "energy_gained": float(final_energy),  # Сколько получит при нажатии "Забрать"
                    "is_win": is_win,
                    "total_energy": float(user_profile.energy),  # Текущий баланс (без начисления)
                    "storage": float(user_profile.storage),
                    "power": float(user_profile.power),
                    "bonuses": None,
                    "penalties": None,
                },
                status=status.HTTP_200_OK,
            )
            
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            action_logger.error(
                f"GameRunCompleteView error: {str(e)}, traceback: {traceback.format_exc()}"
            )
            traceback.print_exc()
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class GameRunClaimView(APIView):
    """Начисление энергии при нажатии кнопки 'Забрать' после завершения забега"""
    
    @swagger_auto_schema(
        tags=["game"],
        operation_description="Начисление энергии за завершенный забег при нажатии кнопки 'Забрать'",
        responses={
            200: openapi.Response(
                description="Энергия успешно начислена",
                examples={
                    "application/json": {
                        "success": True,
                        "message": "Energy claimed successfully",
                        "energy_gained": 45.3,
                        "total_energy": 150.5,
                    }
                },
            ),
            400: "Ошибка валидации или забег не был завершен",
        },
    )
    @require_auth
    def post(self, request):
        try:
            # Перезагружаем user_profile из базы данных
            user_profile = UserProfile.objects.get(user_id=request.user_profile.user_id)
            now = timezone.now()
            
            action_logger.info(
                f"GameRunClaimView POST received: user_id={user_profile.user_id}"
            )
            
            # Валидация: Проверка что забег был завершен (есть energy_run_start_storage и energy_run_last_started_at)
            if not user_profile.energy_run_last_started_at:
                action_logger.warning(
                    f"GameRunClaimView validation FAILED: Run not started for user {user_profile.user_id}"
                )
                return Response(
                    {"error": "Run not started. Please start a run first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            if user_profile.energy_run_start_storage is None:
                action_logger.warning(
                    f"GameRunClaimView validation FAILED: Run data not found for user {user_profile.user_id}"
                )
                return Response(
                    {"error": "Run data not found. Please complete a run first."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Проверка что забег был завершен не более 2 часов назад
            time_since_start = (now - user_profile.energy_run_last_started_at).total_seconds()
            if time_since_start > 7200:  # 2 часа
                action_logger.warning(
                    f"GameRunClaimView validation FAILED: Run expired for user {user_profile.user_id}, "
                    f"time_since_start={time_since_start}"
                )
                return Response(
                    {"error": "Run expired. Please start a new run."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Получаем данные завершенного забега из запроса
            # Эти данные должны были быть сохранены при завершении забега
            energy_collected = float(request.data.get("energy_collected", 0))
            is_win = request.data.get("is_win", False)
            
            # Логирование убрано для оптимизации - логируем только финальный результат
            # action_logger.info(
            #     f"GameRunClaimView: user_id={user_profile.user_id}, "
            #     f"energy_collected={energy_collected}, is_win={is_win}, "
            #     f"energy_run_start_storage={user_profile.energy_run_start_storage}"
            # )
            
            # Валидация собранной энергии
            if energy_collected < 0:
                return Response(
                    {"error": "Invalid energy_collected value"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            max_energy = float(user_profile.energy_run_start_storage)
            if energy_collected > max_energy:
                return Response(
                    {
                        "error": "Energy collected exceeds maximum allowed",
                        "max_allowed": max_energy,
                        "provided": energy_collected,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            
            # Расчет финального количества энергии (та же логика что в GameRunCompleteView)
            if is_win:
                final_energy = energy_collected
            else:
                # При проигрыше применяем процент сохранения от уровня инженера
                engineer_level = user_profile.get_real_engs()
                try:
                    eng_config = EngineerConfig.objects.get(level=engineer_level)
                    saved_percent = eng_config.saved_percent_on_lose or 0
                except EngineerConfig.DoesNotExist:
                    saved_percent = 0
                
                # Бонус +2% если есть активные синие электрики
                if user_profile.electrics_expires and user_profile.electrics_expires > now:
                    saved_percent += 2
                
                saved_percent = min(saved_percent, 100)
                final_energy = energy_collected * (saved_percent / 100)
            
            # Преобразуем final_energy в Decimal
            from decimal import Decimal
            final_energy_decimal = Decimal(str(final_energy))
            
            # Логирование убрано для оптимизации - логируем только финальный результат начисления
            # action_logger.info(
            #     f"GameRunClaimView: user_id={user_profile.user_id}, "
            #     f"energy_collected={energy_collected}, is_win={is_win}, "
            #     f"final_energy={final_energy}, final_energy_decimal={final_energy_decimal}, "
            #     f"engineer_level={user_profile.get_real_engs() if not is_win else 'N/A'}"
            # )
            
            # Начисление энергии на баланс
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                energy=F("energy") + final_energy_decimal
            )
            
            # Обновление WalletInfo.kw_amount
            if user_profile.ton_wallet:
                updated_count = WalletInfo.objects.filter(
                    user=user_profile, 
                    wallet=user_profile.ton_wallet
                ).update(kw_amount=F("kw_amount") + final_energy_decimal)
                # Логирование убрано для оптимизации - логируем только ошибки
                # action_logger.info(
                #     f"GameRunClaimView: WalletInfo updated for user {user_profile.user_id}, "
                #     f"wallet={user_profile.ton_wallet}, updated_count={updated_count}, "
                #     f"kw_amount_added={final_energy_decimal}"
                # )
            # else:
            #     # Логирование убрано для оптимизации - логируем только ошибки
            #     # action_logger.warning(
            #     #     f"GameRunClaimView: No ton_wallet for user {user_profile.user_id}, "
            #     #     f"skipping WalletInfo update"
            #     # )
            
            # Обновление статистики
            GlobalSpendStats.objects.update(
                total_energy_accumulated=F("total_energy_accumulated") + final_energy_decimal
            )
            
            # Добавление в график
            add_chart_kw(float(final_energy))
            
            # Очистка данных забега после успешного начисления
            # НЕ обнуляем energy_run_last_started_at - он нужен для cooldown таймера
            # Обнуляем только energy_run_start_storage, так как забег завершен и энергия начислена
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                energy_run_start_storage=None
                # energy_run_last_started_at остается для cooldown таймера (60 минут)
            )
            
            # Получаем обновленный объект пользователя
            user_profile = UserProfile.objects.get(user_id=user_profile.user_id)
            
            return Response(
                {
                    "success": True,
                    "message": "Energy claimed successfully",
                    "energy_gained": float(final_energy),
                    "total_energy": float(user_profile.energy),
                    "storage": float(user_profile.storage),
                    "power": float(user_profile.power),
                },
                status=status.HTTP_200_OK,
            )
            
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            import traceback
            action_logger.error(
                f"GameRunClaimView error: {str(e)}, traceback: {traceback.format_exc()}"
            )
            traceback.print_exc()
            return Response(
                {"error": f"Internal server error: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class AddKwToWalletView(APIView):
    @swagger_auto_schema(
        operation_description="Додає кіловати до гаманця користувача",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["kw_amount"],
            properties={
                "kw_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
            },
        ),
        responses={
            200: openapi.Response(
                description="Кіловати успішно додано до гаманця",
                examples={
                    "application/json": {
                        "message": "Kilowatts added to wallet",
                        "kw_wallet": 100.0,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        kw_amount = request.data.get("kw_amount")
        # if kw_amount is None or kw_amount <= 0:
        #     return Response(
        #         {"error": "Invalid kilowatt amount"}, status=status.HTTP_400_BAD_REQUEST
        #     )

        try:
            user_profile = request.user_profile
            # action_logger.info(
            #     f"user {user_profile.user_id} | add wallet"
            # )
            # user_profile.kw_wallet += kw_amount
            # user_profile.save()
            return Response(
                {
                    "message": "Kilowatts added to wallet",
                    "kw_wallet": user_profile.kw_wallet,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class AddTbtcToWalletView(APIView):
    @swagger_auto_schema(
        operation_description="Додає tBTC до гаманця користувача",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["tbtc_amount"],
            properties={
                "tbtc_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
            },
        ),
        responses={
            200: openapi.Response(
                description="tBTC успішно додано до гаманця",
                examples={
                    "application/json": {
                        "message": "tBTC added to wallet",
                        "tbtc_wallet": 50.0,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        tbtc_amount = request.data.get("tbtc_amount")
        # if tbtc_amount is None or tbtc_amount <= 0:
        #     return Response(
        #         {"error": "Invalid tBTC amount"}, status=status.HTTP_400_BAD_REQUEST
        #     )

        try:
            user_profile = request.user_profile
            # user_profile.tbtc_wallet += tbtc_amount
            # user_profile.save()
            return Response(
                {
                    "message": "tBTC added to wallet",
                    "tbtc_wallet": user_profile.tbtc_wallet,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


from tonsdk.utils import Address
from pytonconnect.parsers import WalletInfo as WalletInfoTon, Account, TonProof

class AddTonWalletView(APIView):
    @swagger_auto_schema(
        tags=["profile"],
        operation_description="Додає TON гаманець до профілю користувача",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["ton_wallet"],
            properties={
                "ton_wallet": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={
            200: openapi.Response(
                description="TON гаманець успішно додано до профілю",
                examples={
                    "application/json": {
                        "message": "TON wallet added to profile",
                        "ton_wallet": "ton_wallet_address",
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile
        ton_wallet = request.data.get("ton_wallet")
        kw_address = request.data.get("kw_address")
        tbtc_address = request.data.get("tbtc_address")
        
        proof = {"proof":request.data.get("proof")}
        account = request.data.get("account")
        account["network"] = ""
        
        wallet = WalletInfoTon()
        wallet.account = Account.from_dict(account)
        wallet.ton_proof = TonProof.from_dict(proof)
        try:
            is_valid = wallet.check_proof()
            if not is_valid:
                return Response(
                    {"error": "Invalid wallet data"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            # sentry_sdk.capture_exception(e)
            return Response(
                {"error": "Invalid wallet data"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # if not ton_wallet or not kw_address or not tbtc_address:
        # print(request.data)
        if not ton_wallet:
            return Response(
                {"error": "wallet address is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if UserProfile.objects.filter(ton_wallet=ton_wallet).exists():
                return Response(
                    {"error": "TON wallet is already associated with another user"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            

            wallet_info = WalletInfo.objects.filter(user=user_profile, wallet=ton_wallet).first()
            if wallet_info is None:
                # не знайдено інфи по волету
                if WalletInfo.objects.filter(user=user_profile).first() is None:
                    # якщо це перший волет, беремо значення з профілю і не блокуємо
                    WalletInfo.objects.create(
                    user=user_profile,
                    wallet=ton_wallet,
                    kw_amount=user_profile.energy,
                    tbtc_amount=user_profile.mined_tokens_balance,
                    tbtc_amount_s21=user_profile.mined_tokens_balance_s21,
                    tbtc_amount_sx=user_profile.mined_tokens_balance_sx,
                    block_until=None,
                )
                else:
                    # якщо це не перший волет, блокуємо його на 1 день
                    WalletInfo.objects.create(
                        user=user_profile,
                        wallet=ton_wallet,
                        block_until=timezone.now() + timedelta(days=1),
                    )
            else:
                # якщо це перепідключення минулого волета (злетів, etc.), не блокуємо
                if user_profile.prev_ton_wallet and ton_wallet != user_profile.prev_ton_wallet:
                    WalletInfo.objects.filter(
                        user=user_profile,
                        wallet=ton_wallet,
                    ).update(
                        block_until=timezone.now() + timedelta(days=1),
                    )

            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                ton_wallet=ton_wallet,
                prev_ton_wallet=ton_wallet,
                kw_address=kw_address,
                tbtc_address=tbtc_address,
            )
            
            user_profile.stop_mining("add ton wallet")
            action_logger.info(
                f"user {user_profile.user_id} | added wallet {ton_wallet}"
            )
            return Response(
                {
                    "message": "TON wallet added to profile",
                    "ton_wallet": user_profile.ton_wallet,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class DeleteTonWalletView(APIView):
    @swagger_auto_schema(
        tags=["profile"],
        operation_description="Видалити TON гаманець з профілю користувача",
        responses={
            200: openapi.Response(
                description="TON гаманець успішно видалено з профілю",
                examples={
                    "application/json": {
                        "message": "TON wallet removed from profile",
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            wallet = str(user_profile.ton_wallet)
            user_profile.ton_wallet = None
            user_profile.kw_address = None
            user_profile.tbtc_address = None
            user_profile.save()
            user_profile.stop_mining("delete ton wallet")

            user_profile.battery_balance = 0
            user_profile.nft_count = 0
            user_profile.mining_farm_speed = 0
            user_profile.total_mining_speed = 0
            user_profile.total_farm_consumption = 0
            user_profile.farm_runtime = 0
            user_profile.nft_string = ""
            user_profile.mining_period = 0
            user_profile.save()
            action_logger.info(f"user {user_profile.user_id} | remove wallet {wallet}")
            return Response(
                {"message": "TON wallet removed from profile"},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


# def generate_payload(ttl: int) -> str:
#     payload = bytearray(random(8))

#     ts = int(datetime.now().timestamp()) + ttl
#     payload.extend(ts.to_bytes(8, "big"))

#     return payload.hex()


# from pytonconnect import TonConnect
# from pytonconnect.parsers import WalletInfo


# def check_payload(payload: str, wallet_info: WalletInfo):
#     if len(payload) < 32:
#         print("Payload length error")
#         return False
#     if not wallet_info.check_proof(payload):
#         print("Check proof failed")
#         return False
#     ts = int(payload[16:32], 16)
#     if datetime.now().timestamp() > ts:
#         print("Request timeout error")
#         return False
#     return True


# async def main():
#     proof_payload = generate_payload(600)

#     connector = TonConnect(
#         manifest_url="https://raw.githubusercontent.com/XaBbl4/pytonconnect/main/pytonconnect-manifest.json"
#     )

#     def status_changed(wallet_info):
#         print("wallet_info:", wallet_info)
#         if wallet_info is not None:
#             print("check_proof:", check_payload(proof_payload, wallet_info))

#         unsubscribe()

#     def status_error(e):
#         print("connect_error:", e)

#     unsubscribe = connector.on_status_change(status_changed, status_error)

#     wallets_list = connector.get_wallets()
#     print("wallets_list:", wallets_list)


class UpgradeStorageView(APIView):
    @swagger_auto_schema(
        tags=["station"],
        operation_description="Апгрейд сховища користувача",
        responses={
            200: openapi.Response(
                description="Сховище апгрейдовано успішно",
                examples={
                    "application/json": {
                        "message": "Storage upgraded successfully",
                    }
                },
            ),
            400: "Неправильні дані або недостатньо ресурсів",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            if user_profile.is_building():
                return Response(
                    {"error": "Building is in progress"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                user_profile = UserProfile.objects.select_for_update().get(
                    user_id=user_profile.user_id
                )
                if user_profile.upgrade_storage():
                    return Response(
                        {"message": "Storage upgraded successfully"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Not enough resources or maximum level reached"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class UpgradeGenerationView(APIView):
    @swagger_auto_schema(
        tags=["station"],
        operation_description="Апгрейд генерації користувача",
        responses={
            200: openapi.Response(
                description="Генерацію апгрейдовано успішно",
                examples={
                    "application/json": {
                        "message": "Generation upgraded successfully",
                    }
                },
            ),
            400: "Неправильні дані або недостатньо ресурсів",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile = request.user_profile
            if user_profile.is_building():
                return Response(
                    {"error": "Building is in progress"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                user_profile = UserProfile.objects.select_for_update().get(
                    user_id=user_profile.user_id
                )
                if user_profile.upgrade_generation():
                    return Response(
                        {"message": "Generation upgraded successfully"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Not enough resources or maximum level reached"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class UpgradeStationView(APIView):
    @swagger_auto_schema(
        tags=["station"],
        operation_description="Апгрейд станції користувача",
        responses={
            200: openapi.Response(
                description="Станцію апгрейдовано успішно",
                examples={
                    "application/json": {
                        "message": "Station upgraded successfully",
                    }
                },
            ),
            400: "Неправильні дані або недостатньо ресурсів",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            if user_profile.is_building():
                return Response(
                    {"error": "Building is in progress"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            with transaction.atomic():
                user_profile = UserProfile.objects.select_for_update().get(
                    user_id=user_profile.user_id
                )
                if user_profile.upgrade_station():
                    return Response(
                        {"message": "Station upgraded successfully"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Not enough resources or maximum level reached"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        # except Exception as e:
        #     return Response(
        #         {"error": traceback.format_exc()}, status=status.HTTP_400_BAD_REQUEST
        #     )


class UpgradeEngineerView(APIView):
    @swagger_auto_schema(
        tags=["station"],
        operation_description="Апгрейд інженера користувача",
        responses={
            200: openapi.Response(
                description="Інженера покращено успішно",
                examples={
                    "application/json": {
                        "message": "Engineer upgraded successfully",
                    }
                },
            ),
            400: "Неправильні дані або недостатньо ресурсів",
        },
    )
    @require_auth
    def post(self, request):
        # loger222.info(f"{request.user_profile.user_id}")
        try:
            user_profile: UserProfile = request.user_profile
            with transaction.atomic():
                user_profile = UserProfile.objects.select_for_update().get(
                    user_id=user_profile.user_id
                )
                # if user_profile.engineer_level + 1 >= 50:
                #     return Response(
                #         {"error": "Stars payment"},
                #         status=status.HTTP_400_BAD_REQUEST,
                #     )
                if user_profile.upgrade_engineer():
                    return Response(
                        {"message": "Engineer upgraded successfully"},
                        status=status.HTTP_200_OK,
                    )
                else:
                    return Response(
                        {"error": "Not enough resources or maximum level reached"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class BufferTransactionView(APIView):
    @swagger_auto_schema(
        tags=["withdraw"],
        operation_description="Отримати результат транзакції за хешем",
        responses={
            200: openapi.Response(
                description="Результат транзакції",
                examples={
                    "application/json": {
                        "tx_hash": "transaction_hash",
                        "address": "address",
                        "success": True,
                    }
                },
            ),
            404: "Транзакцію не знайдено",
        },
    )
    def get(self, request, tx_hash):
        try:
            transaction = BufferTransaction.objects.get(tx_hash=tx_hash)
            return Response(
                {
                    "tx_hash": transaction.tx_hash,
                    "address": transaction.address,
                    "success": transaction.success,
                },
                status=status.HTTP_200_OK,
            )
        except BufferTransaction.DoesNotExist:
            return Response(
                {"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND
            )


class LastWithdrawalDateView(APIView):
    @swagger_auto_schema(
        tags=["withdraw"],
        operation_description="Отримати дату останнього виводу користувача",
        responses={
            200: openapi.Response(
                description="Дата останнього виводу",
                examples={
                    "application/json": {
                        "last_withdrawal_date": "2023-10-01T12:34:56Z",
                    }
                },
            ),
            404: "Користувача не знайдено",
        },
    )
    @require_auth
    def get(self, request):
        try:
            user_profile = request.user_profile
            last_request = (
                WithdrawalRequest.objects.filter(user=user_profile)
                .order_by("-claimed_at")
                .first()
            )
            if last_request:
                last_withdrawal_date = last_request.claimed_at
            else:
                last_withdrawal_date = None

            return Response(
                {"last_withdrawal_date": last_withdrawal_date},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class GetKwReferralBonusesView(APIView):
    @swagger_auto_schema(
        tags=["referral"],
        operation_description="Отримати бонусні бали від рефералів до kw_wallet",
        responses={
            200: openapi.Response(
                description="Бонусні бали успішно отримано",
                examples={
                    "application/json": {
                        "message": "Bonuses added to kw_wallet",
                        "kw_wallet": 100.0,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile = request.user_profile
            kw_bonus = user_profile.bonus_kw_level_1 + user_profile.bonus_kw_level_2

            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                kw_wallet=F("kw_wallet") + kw_bonus,
                bonus_kw_level_1=0,
                bonus_kw_level_2=0,
                last_kw_bonus_claimed_at=timezone.now(),
            )

            # UserProfile.objects.filter(referrer=user_profile).update(
            #     bring_bonus_kw_level_1=0, bring_bonus_kw_level_2=0
            # )

            user_profile.refresh_from_db()
            return Response(
                {
                    "message": "Bonuses added to kw_wallet",
                    "kw_wallet": user_profile.kw_wallet,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class GetTbtcReferralBonusesView(APIView):
    @swagger_auto_schema(
        tags=["referral"],
        operation_description="Отримати бонусні бали від рефералів до tbtc_wallet",
        responses={
            200: openapi.Response(
                description="Бонусні бали успішно отримано",
                examples={
                    "application/json": {
                        "message": "Bonuses added to tbtc_wallet",
                        "tbtc_wallet": 50.0,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        # return Response({"error": "Not active"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_profile = request.user_profile
            tbtc_bonus = (
                user_profile.bonus_tbtc_level_1 + user_profile.bonus_tbtc_level_2
            )

            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                tbtc_wallet=F("tbtc_wallet") + tbtc_bonus,
                bonus_tbtc_level_1=0,
                bonus_tbtc_level_2=0,
                last_tbtc_bonus_claimed_at=timezone.now(),
            )

            # UserProfile.objects.filter(referrer=user_profile).update(
            #     bring_bonus_tbtc_level_1=0, bring_bonus_tbtc_level_2=0
            # )

            user_profile.refresh_from_db()
            return Response(
                {
                    "message": "Bonuses added to tbtc_wallet",
                    "tbtc_wallet": user_profile.tbtc_wallet,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class GetStakingReferralBonusesView(APIView):
    @swagger_auto_schema(
        tags=["staking"],
        operation_description="Отримати staking бали від рефералів до tbtc_wallet",
        responses={
            200: openapi.Response(
                description="Бонусні бали успішно отримано",
                examples={
                    "application/json": {
                        "message": "Bonuses added to tbtc_wallet",
                        "tbtc_wallet": 50.0,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        # return Response({"error": "Not active"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_profile: UserProfile = request.user_profile
            tbtc_bonus = (
                user_profile.bonus_invest_level_1 + user_profile.bonus_invest_level_2
            )

            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                tbtc_wallet=F("tbtc_wallet") + tbtc_bonus,
                bonus_invest_level_1=0,
                bonus_invest_level_2=0,
                last_staking_bonus_claimed_at=timezone.now(),
            )

            # UserProfile.objects.filter(referrer=user_profile).update(
            #     bring_bonus_tbtc_level_1=0, bring_bonus_tbtc_level_2=0
            # )

            user_profile.refresh_from_db()
            return Response(
                {
                    "message": "Bonuses added to tbtc_wallet",
                    "tbtc_wallet": user_profile.tbtc_wallet,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


header_param = openapi.Parameter(
    "Authorization",
    openapi.IN_HEADER,
    description="local header param",
    type=openapi.IN_HEADER,
)
header_param2 = openapi.Parameter(
    "user_id",
    openapi.IN_QUERY,
    # description="local header param",
    type=openapi.IN_QUERY,
)


class UserTapInfoView(APIView):
    @swagger_auto_schema(
        # operation_description="Отримати інформацію про користувача, якщо у нього більше 10 тапів",
        tags=["integration"],
        responses={
            200: openapi.Response(
                description="Інформація про користувача",
                schema=UserProfileSerializer(),
            ),
            404: "Користувача не знайдено або недостатньо тапів",
            401: "Unauthorized",
        },
        manual_parameters=[header_param, header_param2],
    )
    def get(self, request):
        auth_header = request.headers.get("Authorization")
        if (
            not auth_header
            or auth_header
            != "Bearer OybjGzPQ1SBamQUKLlzKVbajeJTAw75Q0Ig3lUCdrLAMz3zu3eVXrKELX5ikaXvG"
        ):
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_profile = UserProfile.objects.get(user_id=int(user_id))
            # if user_profile.tap_count > 10:
            serializer = UserProfileSerializer(user_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
            # else:
            #     return Response(
            #         {"error": "Not enough taps"}, status=status.HTTP_404_NOT_FOUND
            #     )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class UserTapInfoView2(APIView):
    @swagger_auto_schema(
        # operation_description="Отримати інформацію про користувача, якщо у нього більше 10 тапів",
        tags=["integration"],
        responses={
            200: openapi.Response(
                description="Інформація про користувача",
                schema=UserProfileSerializer(),
            ),
            404: "Користувача не знайдено або недостатньо тапів",
            401: "Unauthorized",
        },
    )
    def get(self, request):
        auth_header = request.headers.get("Authorization")
        if (
            not auth_header
            or auth_header
            != "Bearer MKFVLBkgJswE5x5RIJkgFAlLwJQSDWiqK2CcGCBPB4th8xTBJw34DEe8RXu5c911"
        ):
            return Response(
                {"error": "Unauthorized"}, status=status.HTTP_401_UNAUTHORIZED
            )

        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "User ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user_profile = UserProfile.objects.get(user_id=int(user_id))
            # if user_profile.tap_count > 10:
            serializer = UserProfileSerializer(user_profile)
            return Response(serializer.data, status=status.HTTP_200_OK)
            # else:
            #     return Response(
            #         {"error": "Not enough taps"}, status=status.HTTP_404_NOT_FOUND
            #     )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class EnableStationView(APIView):
    @swagger_auto_schema(
        tags=["mining"],
        operation_description="Enable the station to start generating energy",
        responses={
            200: openapi.Response(
                description="Station enabled successfully",
                examples={
                    "application/json": {
                        "message": "Station enabled successfully",
                    }
                },
            ),
            400: "Invalid data or user not found",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile = request.user_profile
            if user_profile.overheated_until > timezone.now():
                return Response(
                    {"error": "Station is overheated"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                overheated_until=None, tap_count_since_overheat=0
            )
            return Response(
                {"message": "Station enabled successfully"},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


from django.conf import settings
from telebot import TeleBot, types

bot = TeleBot(settings.BOT_TOKEN, parse_mode="HTML")
from telebot.types import LabeledPrice


class EngineerStarsView(APIView):
    @swagger_auto_schema(
        tags=["station"],
        operation_description="Отримати посилання для покупки інженера",
        responses={
            200: openapi.Response(
                description="Посилання для покупки інженера",
                examples={
                    "application/json": {
                        "link": "https://example.com/invoice_link",
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            next_level = user_profile.engineer_level + 1
            # if next_level < 50:
            #     return Response(
            #         {"error": "Wrong level"},
            #         status=status.HTTP_400_BAD_REQUEST,
            #     )

            config = EngineerConfig.objects.get(level=next_level)
            
            price = config.hire_cost_stars
            if not price:
                return Response(
                    {"error": "Price not set for this level"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            final_price = int(user_profile.sbt_get_stars_discount() * price)
            link = bot.create_invoice_link(
                title="Покупка инженера",
                description=f"Покупка инженера {next_level} уровня",
                currency="XTR",
                provider_token="",
                prices=[LabeledPrice(label="XTR", amount=final_price)],
                payload=f"engineer:{next_level}",
            )
            return Response(
                {"link": link},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class StakingPeriodConfigView(APIView):
    @swagger_auto_schema(
        tags=["staking"],
        operation_description="Отримати всі настройки стейкінгу",
        responses={200: StakingPeriodConfigSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        slots = StakingPeriodConfig.objects.all()
        serializer = StakingPeriodConfigSerializer(slots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class HashrateInfoView(APIView):
    @swagger_auto_schema(
        tags=["mining"],
        responses={200: HashrateInfoSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        slots = HashrateInfo.objects.all()
        serializer = HashrateInfoSerializer(slots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateUserStakingView(APIView):
    @swagger_auto_schema(
        tags=["staking"],
        operation_description="Створити новий стейкінг для користувача",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["token_amount", "staking_period_days"],
            properties={
                "token_amount": openapi.Schema(type=openapi.TYPE_NUMBER),
                "staking_period_days": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(
                description="Стейкінг створено успішно",
                examples={
                    "application/json": {
                        "message": "Staking created successfully",
                        "staking_id": 1,
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile
        staking_period_days = request.data.get("staking_period_days")

        if not all([staking_period_days]):
            return Response(
                {"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            staking_config = StakingPeriodConfig.objects.get(days=staking_period_days)
        except StakingPeriodConfig.DoesNotExist:
            return Response(
                {"error": "Invalid staking period"}, status=status.HTTP_400_BAD_REQUEST
            )

        user_staking = UserStaking.objects.create(
            user=user_profile,
            days=staking_period_days,
            apr=staking_config.apr,
            confirmed=False,
        )

        return Response(
            {
                "message": "Staking created successfully",
                "staking_id": user_staking.id,
            },
            status=status.HTTP_200_OK,
        )


class RewardsInfoPagination(PageNumberPagination):
    page_size = 100  # Default number of referrals per page
    page_size_query_param = (
        "page_size"  # Allow client to specify the number of referrals per page
    )
    max_page_size = 200  # Set a maximum limit for page size


class UserStakingsView(ListAPIView):
    queryset = UserStaking.objects.all()
    serializer_class = UserStakingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["start_date", "end_date", "token_amount"]
    filterset_fields = ["status"]
    pagination_class = ReferralInfoPagination

    @swagger_auto_schema(
        tags=["staking"],
        operation_description="Отримати історію наград користувача",
        responses={200: UserStakingSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        user_profile = request.user_profile

        stakings = UserStaking.objects.filter(user=user_profile, confirmed=True)
        # .exclude(status="wait_deposit")

        stakings = self.filter_queryset(stakings)
        stakings = self.paginate_queryset(stakings)

        serializer = UserStakingSerializer(stakings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EarnDepositView(APIView):
    @swagger_auto_schema(
        tags=["staking"],
        operation_description="Отримати депозит користувача",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["stake_id"],
            properties={
                "stake_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(
                description="Інформація про депозит",
                examples={
                    "application/json": {
                        "deposit": 100.0,
                    }
                },
            ),
            404: "Користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile = request.user_profile
            stake_id = request.data.get("stake_id")
            stake = UserStaking.objects.filter(id=stake_id, user=user_profile).first()
            if not stake:
                return Response(
                    {"error": "Stake not found"}, status=status.HTTP_404_NOT_FOUND
                )
            if timezone.now() < stake.end_date:
                return Response(
                    {"error": "Stake is not finished yet"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if stake.status != "active":
                return Response(
                    {"error": "Cant get deposit"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            UserStaking.objects.filter(id=stake_id).update(status="wait_deposit")
            return Response(
                {"deposit": UserStakingSerializer(stake).data},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


def check_calc_answer(number1, op, number2, answer):
    if op == "+":
        if number1 + number2 == answer:
            return True
    elif op == "-":
        if number1 - number2 == answer:
            return True
    elif op == "*":
        if number1 * number2 == answer:
            return True
    elif op == "/":
        if number1 / number2 == answer:
            return
    return False


class ReconnectMiningView(APIView):
    @swagger_auto_schema(
        tags=["mining"],
        operation_description="Перезапуск майнінг ферми",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[],
            properties={
                "number1": openapi.Schema(type=openapi.TYPE_NUMBER),
                "op": openapi.Schema(type=openapi.TYPE_STRING),
                "number2": openapi.Schema(type=openapi.TYPE_NUMBER),
                "answer": openapi.Schema(type=openapi.TYPE_NUMBER),
            },
        ),
        responses={
            200: openapi.Response(
                description="Майнінг ферму запущено",
                examples={
                    "application/json": {
                        "message": "Mining started",
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            number1 = int(request.data.get("number1"))
            op = request.data.get("op")
            number2 = int(request.data.get("number2"))
            answer = int(request.data.get("answer"))

            if not all([number1, op, number2, answer]):
                return Response(
                    {"error": "All fields are required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_profile: UserProfile = request.user_profile
            action_logger.info(f"restarting mining user {user_profile.user_id}")
            if not user_profile.mining_was_stopped:
                return Response(
                    {"error": "Mining is already running"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                user_profile.stop_mining_activate_last
                and timezone.now() - user_profile.stop_mining_activate_last
                < timedelta(minutes=10)
            ):
                return Response(
                    {"error": "Wrong attempt recently"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not check_calc_answer(number1, op, number2, answer):
                UserProfile.objects.filter(user_id=user_profile.user_id).update(
                    stop_mining_activate_last=timezone.now(),
                )
                return Response(
                    {"error": "Wrong answer"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_profile.upd_stopper()

            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                mining_was_stopped=False, mining_last_stopped=None
            )

            user_profile.refresh_from_db()
            action_logger.info(f"restarted mining user {user_profile.user_id}")
            return Response(
                {
                    "message": "Mining started",
                    "user": UserProfileSerializer(user_profile).data,
                },
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class MintStationView(APIView):
    @swagger_auto_schema(
        tags=["mint"],
        operation_description="Mint a new level station",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["burn_nft1", "burn_nft2"],
            properties={
                "burn_nft1": openapi.Schema(type=openapi.TYPE_STRING),
                "burn_nft2": openapi.Schema(type=openapi.TYPE_STRING),
            },
        ),
        responses={200: "Mint request created", 400: "Invalid request"},
    )
    @require_auth
    def post(self, request):
        # loger222.info("MINT")
        burn_nft1 = request.data.get("burn_nft1")
        burn_nft2 = request.data.get("burn_nft2")

        user_profile: UserProfile = request.user_profile

        # Check if user has two NFT level 5
        # nft_level = len(
        #     user_profile.mint_string.split(",")
        # )  # Example check, adjust as needed
        # nft_level = 3
        # if nft_level < 2:
        #     return Response(
        #         {"status": "Not enough NFT level 5"}, status=status.HTTP_400_BAD_REQUEST
        #     )

        has_existing_nft = StationNFTOwner.objects.filter(user=user_profile).exists()

        # loger222.info(f"{has_existing_nft}, {user_profile.get_station_level()}")
        if not has_existing_nft and user_profile.get_station_level() >= 4:
            config_storage = StoragePowerStationConfig.objects.get(
                station_type=user_profile.station_type, level=1
            )
            required_kw, required_tbtc = 0, config_storage.price_tbtc / 2
            # if user_profile.id==678886913:
            # loger222.info(f"{user_profile.tbtc_wallet}, {required_tbtc}")
            if user_profile.tbtc_wallet < required_tbtc:
                return Response(
                    {"status": "Insufficient resources"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                tbtc_wallet=F("tbtc_wallet") - required_tbtc,
                building_until=timezone.now()
                + config_storage.get_duration()
                * user_profile.sbt_get_building_reduction(),
                current_mint="wait",
            )

            mint_request = MintRequest.objects.create(
                user=user_profile,
                wallet=user_profile.ton_wallet,
                nft_required=user_profile.station_type,
                kw_spent=required_kw,
                tbtc_spent=required_tbtc,
                nft_sent_1=burn_nft1,
                nft_sent_2=burn_nft2,
            )
        else:
            if user_profile.ton_wallet is None or user_profile.ton_wallet == "":
                return Response(
                    {"status": "Wallet not found"}, status=status.HTTP_400_BAD_REQUEST
                )

            # if user_profile.get_station_level() + 1 != 4:
            #     if (
            #         burn_nft1 is None
            #         or burn_nft2 is None
            #         or burn_nft1 == ""
            #         or burn_nft2 == ""
            #     ):
            #         return Response(
            #             {"status": "NFT empty"}, status=status.HTTP_400_BAD_REQUEST
            #         )

            #     if burn_nft1 == burn_nft2:
            #         return Response(
            #             {"status": "NFTs must be different"},
            #             status=status.HTTP_400_BAD_REQUEST,
            #         )

            #     if (
            #         burn_nft1 not in user_profile.mint_string
            #         or burn_nft2 not in user_profile.mint_string
            #     ):
            #         return Response(
            #             {"status": "NFT not found"}, status=status.HTTP_400_BAD_REQUEST
            #         )

            if not user_profile.upgrade_station():
                return Response(
                    {"message": "Insufficient resources"},
                    status=status.HTTP_200_OK,
                )

            StationNFTOwner.objects.filter(user=user_profile).delete()
            UserProfile.objects.filter(user_id=user_profile.user_id).update(
                current_mint="wait"
            )

            config_storage = StoragePowerStationConfig.objects.get(
                station_type=user_profile.station_type, level=1
            )
            required_kw, required_tbtc = (
                config_storage.price_kw,
                config_storage.price_tbtc,
            )
            # Create mint request
            mint_request = MintRequest.objects.create(
                user=user_profile,
                wallet=user_profile.ton_wallet,
                nft_required=user_profile.station_type,
                kw_spent=required_kw,
                tbtc_spent=required_tbtc,
                nft_sent_1=burn_nft1,
                nft_sent_2=burn_nft2,
            )

        StationNFTOwner.objects.create(
            user=user_profile,
            wallet=user_profile.ton_wallet,
        )

        # Check NFT ownership after minting process
        # if not check_nft_ownership(user_profile, mint_request.nft_required):
        #     return Response(
        #         {"status": "NFT not found, reverted to Boiler House"},
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )

        return Response({"status": "Mint request created"}, status=status.HTTP_200_OK)


class RollbackStationView(APIView):
    @swagger_auto_schema(
        tags=["mint"],
        operation_description="Rollback station to Boiler House",
        responses={200: "Station rolled back successfully", 400: "Invalid request"},
    )
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile

        if user_profile.station_type != "Boiler house":
            user_profile.reset_station()

            return Response(
                {"status": "Station rolled back successfully"},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"status": "Station is already at Boiler House"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AssignNFTStationView(APIView):
    @swagger_auto_schema(
        operation_description="Assign an NFT station to a user",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["user_id", "station_id"],
            properties={
                "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
                "station_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={200: "NFT station assigned successfully", 400: "Invalid request"},
    )
    @require_auth
    def post(self, request):
        user_id = request.data.get("user_id")
        station_id = request.data.get("station_id")

        try:
            user = UserProfile.objects.get(user_id=user_id)
            station = NFTStation.objects.get(id=station_id)
            user.nft_count += 1
            user.save()
            UserActionLog.objects.create(
                user=user,
                action="Assigned NFT station",
                details=f"Assigned {station.station_type} level {station.level} to user {user_id}",
            )
            return Response(
                {"status": "NFT station assigned successfully"},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
        except NFTStation.DoesNotExist:
            return Response(
                {"error": "NFT station not found"}, status=status.HTTP_404_NOT_FOUND
            )


class UserActionLogView(APIView):
    @swagger_auto_schema(
        operation_description="Get user action logs",
        responses={200: UserActionLogSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        logs = UserActionLog.objects.all()
        serializer = UserActionLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class StationRollbackLogView(APIView):
    @swagger_auto_schema(
        operation_description="Get station rollback logs",
        responses={200: StationRollbackLogSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        logs = StationRollbackLog.objects.all()
        serializer = StationRollbackLogSerializer(logs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SpeedBuildStarsView(APIView):
    @swagger_auto_schema(
        tags=["mint", "station"],
        operation_description="Отримати посилання для прискорення будівництва",
        responses={
            200: openapi.Response(
                description="Посилання для прискорення будівництва",
                examples={
                    "application/json": {
                        "link": "https://example.com/invoice_link",
                    }
                },
            ),
            400: "Неправильні дані або користувача не знайдено",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile

            price = user_profile.get_build_price()
            if price is None:
                return Response(
                    {"error": "Building not in progress"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            final_price = int(price * user_profile.sbt_get_stars_discount())

            link = bot.create_invoice_link(
                title="Ускорение строительства",
                description=f"Ускорение строительства",
                currency="XTR",
                provider_token="",
                prices=[LabeledPrice(label="XTR", amount=final_price)],
                payload=f"speed_build",
            )
            return Response(
                {"link": link},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )


class NFTRentalView(APIView):
    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Configure and process NFT rental",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["nft", "rental_days", "owner_percentage"],
            properties={
                "nft": openapi.Schema(type=openapi.TYPE_STRING),
                "rental_days": openapi.Schema(type=openapi.TYPE_INTEGER),
                "owner_percentage": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(description="NFT rental configured successfully"),
            400: "Invalid data or insufficient resources",
        },
    )
    @require_auth
    def post(self, request):
        # return Response(
        #     {"message": "Rent is turned off"},
        #     status=status.HTTP_410_GONE,
        # )
        user_profile: UserProfile = request.user_profile
        nft = request.data.get("nft")
        rental_days = request.data.get("rental_days")
        owner_percentage = request.data.get("owner_percentage")

        if NFTRentalAgreement.objects.filter(nft=nft).exists():
            return Response(
                {"error": "NFT is already in rental list"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            user_profile.rent_blocked_until
            and user_profile.rent_blocked_until > timezone.now()
        ):
            return Response(
                {"error": "You are temporarily blocked from renting NFTs"},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Validate rental configuration
        try:
            rental_config = NFTRentalConfig.objects.first()
            if not rental_config:
                return Response(
                    {"error": "Rental configuration not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not (rental_config.min_days <= rental_days <= rental_config.max_days):
                return Response(
                    {"error": "Invalid rental period"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not (
                rental_config.min_percentage
                <= owner_percentage
                <= rental_config.max_percentage
            ):
                return Response(
                    {"error": "Invalid percentage"}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            return Response(
                {"error": "Invalid configuration"}, status=status.HTTP_400_BAD_REQUEST
            )

        if nft not in user_profile.nft_string.split(";"):
            return Response(
                {"error": "NFT not found in mining"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create rental agreement
        # end_date = timezone.now() + timedelta(days=rental_days)
        nft_db = NFTDatabase.objects.filter(nft=nft).first()
        NFTRentalAgreement.objects.create(
            nft=nft,
            hashrate=getattr(nft_db, "hashrate", None),
            name=getattr(nft_db, "name", None),
            owner=user_profile,
            rentals_days=rental_days,
            owner_percentage=owner_percentage,
            # start_date=timezone.now(),
            # end_date=end_date,
        )

        user_profile.recalc_rent()

        if user_profile.is_mining:
            user_profile.stop_mining("NFT rental")

            # START MINING
            returned = start_mining_common(request)
            if returned is not None:
                return returned
            # ========================

        return Response(
            {"message": "NFT rental configured successfully"}, status=status.HTTP_200_OK
        )


class UserNotificationsView(ListAPIView):
    """
    Retrieve a list of notifications for the authenticated user.
    """

    serializer_class = NotificationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["notif_type"]  # Add filtering by notif_type

    @swagger_auto_schema(
        tags=["notifications"],
        operation_description="Get a list of notifications for the authenticated user",
        responses={200: NotificationSerializer(many=True)},
    )
    @require_auth
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        user_profile = self.request.user_profile
        return Notification.objects.filter(user=user_profile).order_by("-created_at")


class MarkNotificationAsReadView(APIView):
    """
    Mark a specific notification as read.
    """

    @swagger_auto_schema(
        tags=["notifications"],
        operation_description="Mark a notification as read",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["notification_id"],
            properties={
                "notification_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(description="Notification marked as read"),
            404: "Notification not found",
        },
    )
    @require_auth
    def post(self, request):
        notification_id = request.data.get("notification_id")
        if not notification_id:
            return Response(
                {"error": "Notification ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            notification = Notification.objects.get(
                id=notification_id, user=request.user_profile
            )
            notification.is_read = True
            notification.save()
            return Response(
                {"message": "Notification marked as read"},
                status=status.HTTP_200_OK,
            )
        except Notification.DoesNotExist:
            return Response(
                {"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND
            )


class NFTRentalsPagination(PageNumberPagination):
    page_size = 10  # Default number of items per page
    page_size_query_param = "page_size"  # Allow client to specify page size
    max_page_size = 100  # Maximum limit for page size


from django.db.models import ExpressionWrapper, F, IntegerField, Value


class AvailableNFTRentalsView(ListAPIView):
    """
    Retrieve a list of available NFTs for rent with sorting options.
    """

    queryset = NFTRentalAgreement.objects.filter(
        renter__isnull=True
    )  # Filter unrented NFTs
    serializer_class = NFTRentalAgreementSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = [
        "hashrate",
        "rentals_days",
        "owner_percentage",
        "adjusted_owner_percentage",
    ]
    pagination_class = NFTRentalsPagination

    def get_queryset(self):
        return NFTRentalAgreement.objects.filter(renter__isnull=True).annotate(
            adjusted_owner_percentage=ExpressionWrapper(
                Value(100) - F("owner_percentage"), output_field=IntegerField()
            )
        )

    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Get a list of available NFTs for rent",
        responses={200: NFTRentalAgreementSerializer(many=True)},
    )
    @require_auth
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserRentedNFTsView(ListAPIView):
    """
    Retrieve a list of NFTs rented by the authenticated user.
    """

    serializer_class = NFTRentalAgreementSerializer

    def get_queryset(self):
        user_profile = self.request.user_profile
        return NFTRentalAgreement.objects.filter(renter=user_profile)

    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Get a list of NFTs rented by the authenticated user",
        responses={200: NFTRentalAgreementSerializer(many=True)},
    )
    @require_auth
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ReturnNFTRentalView(APIView):
    """
    Allow the owner to reclaim their rented NFT after the rental period has ended.
    """

    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Return a rented NFT to its owner after the rental period has ended",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["rental_id"],
            properties={
                "rental_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(description="NFT rental returned successfully"),
            404: "Rental agreement not found",
            403: "Permission denied or rental period not ended",
        },
    )
    @require_auth
    def post(self, request):
        rental_id = request.data.get("rental_id")
        if not rental_id:
            return Response(
                {"error": "Rental ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rental = NFTRentalAgreement.objects.get(id=rental_id)
        except NFTRentalAgreement.DoesNotExist:
            raise NotFound("Rental agreement not found")

        # if rental.renter != request.user_profile:
        #     raise PermissionDenied("You do not have permission to return this NFT")

        if rental.end_date and rental.end_date > timezone.now():
            raise PermissionDenied("Rental period has not ended yet")

        # Delete the rental agreement

        if rental.owner.is_mining:
            rental.owner.stop_mining("NFT rental")

            # START MINING
            returned = start_mining_common(request)

        rental.delete()

        rental.owner.recalc_rent()
        rental.renter.recalc_rent()

        return Response(
            {"message": "NFT rental returned successfully"},
            status=status.HTTP_200_OK,
        )


class CancelNFTRentalView(APIView):
    """
    Cancel the rental of an NFT by the owner.
    """

    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Cancel the rental of an NFT",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["rental_id"],
            properties={
                "rental_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(description="NFT rental canceled successfully"),
            404: "Rental agreement not found",
            403: "Permission denied",
        },
    )
    @require_auth
    def post(self, request):
        rental_id = request.data.get("rental_id")
        if not rental_id:
            return Response(
                {"error": "Rental ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rental = NFTRentalAgreement.objects.get(id=rental_id)
        except NFTRentalAgreement.DoesNotExist:
            raise NotFound("Rental agreement not found")

        if rental.owner != request.user_profile:
            raise PermissionDenied("You do not have permission to cancel this rental")

        if rental.renter is not None:
            return Response(
                {"error": "Cannot cancel rental because it is already rented"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Delete the rental agreement
        rental.delete()
        rental.owner.recalc_rent()

        return Response(
            {"message": "NFT rental canceled successfully"},
            status=status.HTTP_200_OK,
        )


from django.db.models import F
from django.utils.timezone import now
from rest_framework.exceptions import ValidationError


class AccelerateRentBlockView(APIView):
    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Accelerate rent_blocked_until using STARS",
        # request_body=openapi.Schema(
        #     type=openapi.TYPE_OBJECT,
        #     required=["user_id"],
        #     properties={
        #         "user_id": openapi.Schema(type=openapi.TYPE_INTEGER),
        #     },
        # ),
        responses={
            200: openapi.Response(
                description="Rent block accelerated successfully",
                examples={
                    "application/json": {
                        "message": "Rent block accelerated successfully",
                        "new_rent_blocked_until": "2023-10-01T12:34:56Z",
                    }
                },
            ),
            400: "Invalid data or insufficient STARS",
        },
    )
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile

        if (
            not user_profile.rent_blocked_until
            or user_profile.rent_blocked_until <= now()
        ):
            raise ValidationError("Rent block is not active or already expired.")

        config = WithdrawalConfig.objects.first()
        if not config:
            raise ValidationError("Configuration not found.")

        remaining_minutes = max(
            0, (user_profile.rent_blocked_until - now()).total_seconds() / 60
        )
        price = (remaining_minutes // config.gradation_minutes) * config.gradation_value

        final_price = int(price * user_profile.sbt_get_stars_discount())
        link = bot.create_invoice_link(
            title="Ускорение разблокировки аренды",
            description=f"Ускорение разблокировки аренды",
            currency="XTR",
            provider_token="",
            prices=[LabeledPrice(label="XTR", amount=final_price)],
            payload=f"speed_rent_unblock",
        )
        return Response(
            {"link": link},
            status=status.HTTP_200_OK,
        )


class RentNFTView(APIView):
    """
    Allow a user to rent an available NFT.
    """

    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Rent an available NFT",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["rental_id"],
            properties={
                "rental_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(description="NFT rented successfully"),
            404: "Rental agreement not found",
            403: "Permission denied or NFT already rented",
        },
    )
    @require_auth
    def post(self, request):
        # return Response(
        #     {"message": "Rent is turned off"},
        #     status=status.HTTP_410_GONE,
        # )
        rental_id = request.data.get("rental_id")
        if not rental_id:
            return Response(
                {"error": "Rental ID is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            rental = NFTRentalAgreement.objects.get(id=rental_id, renter__isnull=True)
        except NFTRentalAgreement.DoesNotExist:
            raise NotFound("Rental agreement not found or NFT already rented")

        user_profile = request.user_profile

        # Check if the user is blocked from renting
        if (
            user_profile.rent_blocked_until
            and user_profile.rent_blocked_until > timezone.now()
        ):
            return Response(
                {"error": "You are temporarily blocked from renting NFTs"},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            user_profile.kw_wallet
            <= NFTDatabase.objects.get(nft=rental.nft).consumption_kw * 24
        ):
            return Response(
                {"error": "Insufficient resources to rent this NFT"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Assign the renter and set the start and end dates
        rental.renter = user_profile
        rental.start_date = timezone.now()
        rental.end_date = timezone.now() + timedelta(days=rental.rentals_days)
        rental.mining_speed_tbtc = NFTDatabase.objects.get(
            nft=rental.nft
        ).mining_speed_tbtc
        rental.save()

        rental.owner.recalc_rent()
        rental.renter.recalc_rent()

        return Response(
            {"message": "NFT rented successfully"},
            status=status.HTTP_200_OK,
        )


class UserLentNFTsView(ListAPIView):
    """
    Retrieve a list of NFTs lent by the authenticated user.
    """

    serializer_class = NFTRentalAgreementSerializer

    def get_queryset(self):
        user_profile = self.request.user_profile
        return NFTRentalAgreement.objects.filter(owner=user_profile)

    @swagger_auto_schema(
        tags=["rent"],
        operation_description="Get a list of NFTs lent by the authenticated user",
        responses={200: NFTRentalAgreementSerializer(many=True)},
    )
    @require_auth
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


from django.db.models import Avg, DateField
from django.db.models.functions import TruncMonth


class AllChartsView(APIView):
    @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Получить данные для всех графиков",
        manual_parameters=[
            openapi.Parameter(
                "filter_type",
                openapi.IN_QUERY,
                description="Тип фильтра: week, month, all_time",
                type=openapi.TYPE_STRING,
                enum=["week", "month", "all_time"],
            )
        ],
        responses={
            200: openapi.Response(
                description="Данные всех графиков",
                examples={
                    "application/json": {
                        "station_power": [
                            {"date": "2023-05-01", "value": 100.0},
                            {"date": "2023-05-02", "value": 110.0},
                        ],
                        "another_chart": [
                            {"date": "2023-05-01", "value": 50.0},
                            {"date": "2023-05-02", "value": 60.0},
                        ],
                    }
                },
            ),
            400: "Неверный тип фильтра",
        },
    )
    def get(self, request):
        # return None
        all_charts_data = cache.get("CHARTS:all_charts_data")

        if all_charts_data:
            return Response(all_charts_data, status=status.HTTP_200_OK)


        filter_type = request.query_params.get("filter_type", "week")
        if filter_type not in ["week", "month", "all_time"]:
            return Response(
                {"error": "Invalid filter_type. Choose from: week, month, all_time."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()
        if filter_type == "week":
            start_date = today - timedelta(days=6)
        elif filter_type == "month":
            start_date = today - timedelta(days=30)
        else:
            start_date = None

        chart_types = [
            "station_power",
            "network_hashrate",
            "active_stations",
            "active_asics",
            "kw_price",
            "tbtc_price",
            "kw_mined",
            "tbtc_mined",
            "kw_per_tbtc",
            "energy_burned",
            "tbtc_remaining",
            "tbtc_staked",
        ]  # Add all chart types here
        sum_types = {
            "kw_mined",
            "tbtc_mined",
            "energy_burned",
        }
        all_charts_data = {}

        for chart_type in chart_types:
            queryset = ChartData.objects.filter(
                chart_type=chart_type,
            )
            if filter_type == "week":
                queryset = queryset.filter(
                    date__gte=today - timedelta(days=6)
                ).order_by("date")
            elif filter_type == "month":
                queryset = queryset.filter(
                    date__gte=today - timedelta(days=30)
                ).order_by("date")

            if chart_type in sum_types:
                total = queryset.aggregate(total=Sum("value"))["total"] or 0
                all_charts_data[chart_type] = [{"date": str(today), "value": total}]
            else:
                if filter_type == "all_time" or filter_type == "month":
                    all_entries = queryset.order_by("date")
                    total_points = all_entries.count()
                    if total_points == 0:
                        all_charts_data[chart_type] = []
                        continue
                    if total_points <= 10:
                        chart_data = [
                            {"date": entry.date, "value": entry.value}
                            for entry in all_entries
                        ]
                    else:
                        step = (total_points - 1) / 9
                        idxs = [round(i * step) for i in range(10)]
                        chart_data = [
                            {"date": all_entries[i].date, "value": all_entries[i].value}
                            for i in idxs
                            if i < total_points
                        ]
                    all_charts_data[chart_type] = chart_data
                else:
                    chart_data = [
                        {"date": entry.date, "value": entry.value} for entry in queryset
                    ]
                    all_charts_data[chart_type] = chart_data

        # for chart_type in chart_types:
        #     queryset = ChartData.objects.filter(
        #         chart_type=chart_type,
        #     )
        #     if start_date:
        #         queryset = queryset.filter(date__gte=start_date)

        #     if chart_type in sum_types:
        #         chart_data = [
        #             {"date": today, "value": queryset.aggregate(value=Sum("value"))["value"] or 0}
        #         ]

        #         all_charts_data[chart_type] = chart_data
        #     else:
        #         if filter_type == "all_time":
        #             queryset = (
        #                 queryset.annotate(month=TruncMonth("date"))
        #                 .values("month")
        #                 .annotate(avg_value=Avg("value"))
        #                 .order_by("month")
        #             )
        #             chart_data = [
        #                 {"date": entry["month"], "value": entry["avg_value"]}
        #                 for entry in queryset
        #             ]
        #         else:
        #             chart_data = [
        #                 {"date": entry.date, "value": entry.value} for entry in queryset
        #             ]

        #         all_charts_data[chart_type] = chart_data

        cache.set("CHARTS:all_charts_data", all_charts_data, timeout=300)
        return Response(all_charts_data, status=status.HTTP_200_OK)


import requests
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class GeckoProxyView(APIView):
    def get(self, request, path=None):
        url = f"https://api.geckoterminal.com/api/{path}"

        try:
            headers = {
                "Accept": "application/json",
            }
            response = requests.get(url, headers=headers, params=request.query_params)
            r = response.json()
            cache.set("GECKO:" + path, r, timeout=300)  # Short cache to avoid spamming
            return Response(r, status=response.status_code)

        except Exception as e:
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


def get_total_active_generation():
    now = timezone.now()
    total_generation = (
        UserProfile.objects.filter(
            Q(storage__lt=F("storage_limit"))  # Станція ще не заповнена
            | (
                Q(jarvis_expires__gt=now)
                & Q(jarvis_expires__isnull=False)
                & (Q(building_until__lt=now) | Q(building_until__isnull=True))
            )
        ).aggregate(total=Sum(F("generation_rate") * F("power") / 100))
    )["total"] or 0
    return total_generation


def get_total_active_asic_hashrate():
    mining_user_ids = UserProfile.objects.filter(is_mining=True).values_list(
        "id", flat=True
    )
    total_hashrate = (
        NFTRentalAgreement.objects.filter(renter_id__in=mining_user_ids).aggregate(
            total=Sum("hashrate")
        )["total"]
        or 0
    )
    total_hashrate_minus = (
        NFTRentalAgreement.objects.filter(owner_id__in=mining_user_ids).aggregate(
            total=Sum("hashrate")
        )["total"]
        or 0
    )
    return (
        total_hashrate / 1000
        - total_hashrate_minus / 1000
        + (
            UserProfile.objects.filter(is_mining=True).aggregate(
                total=Sum("mining_farm_speed")
            )["total"]
            or 0
        )
    )


def get_total_investor_wallet_balance():
    last = ChartData.objects.filter(chart_type="tbtc_staked").order_by("-date").first()
    return last.value if last else 0


class DashboardInfoView(APIView):
    @swagger_auto_schema(
        tags=["dashboard"],
        operation_description="Отримати основну інформацію для дашборду",
    )
    def get(self, request):
        cache_key = "dashboard_info"
        data = cache.get(cache_key)
        if not data:
            total_active_generation = get_total_active_generation()
            total_active_asic_hashrate = get_total_active_asic_hashrate()
            total_investor_wallet_balance = get_total_investor_wallet_balance()
            data = {
                "total_active_generation": total_active_generation,
                "total_active_asic_hashrate": total_active_asic_hashrate,
                "total_investor_wallet_balance": total_investor_wallet_balance,
            }
            cache.set(cache_key, data, timeout=60)
        return Response(data, status=status.HTTP_200_OK)


# SpecificAsicsView
from core.models import SpecialAsicStaking

from .serializers import SpecialAsicStakingSerializer
from django.core.cache import cache


class SpecificAsicsView(ListAPIView):
    queryset = SpecialAsicStaking.objects.all()
    serializer_class = SpecialAsicStakingSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status"]
    ordering_fields = ["start_date", "end_date", "token_amount", "apr"]

    @swagger_auto_schema(
        tags=["staking"],
        operation_description="Get all special ASIC stakings for the authenticated user",
        responses={200: "List of special ASIC stakings"},
    )
    @require_auth
    def get(self, request):
        user_profile = request.user_profile

        stakings = SpecialAsicStaking.objects.filter(user=user_profile)

        stakings = self.filter_queryset(stakings)

        serializer = SpecialAsicStakingSerializer(stakings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserBurnedTBTCView(ListAPIView):
    queryset = UserBurnedTBTC.objects.all()
    serializer_class = UserBurnedTBTCSerializer
    filter_backends = [OrderingFilter]
    ordering_fields = ["amount"]

    @swagger_auto_schema(
        tags=["staking"],
        responses={200: "List of user burned TBTC"},
    )
    @require_auth
    def get(self, request):
        user_profile = request.user_profile

        stakings = UserBurnedTBTC.objects.filter(user=user_profile)

        stakings = self.filter_queryset(stakings)

        serializer = UserBurnedTBTCSerializer(stakings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)




class TimedUserNFTView(ListAPIView):
    queryset = TimedUserNFT.objects.all()
    serializer_class = TimedUserNFTSerializer
    # filter_backends = [OrderingFilter]
    # ordering_fields = ["amount"]

    @swagger_auto_schema(
        tags=["control"],
        responses={200: "List of user timed nfts"},
    )
    @require_auth
    def get(self, request):
        user_profile = request.user_profile

        objects = TimedUserNFT.objects.filter(user=user_profile, block_until__gt=timezone.now())

        objects = self.filter_queryset(objects)

        serializer = TimedUserNFTSerializer(objects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TimedNFTStarsView(APIView):
    @swagger_auto_schema(
        tags=["control"],
        operation_description="Get invoice link for speeding up TimedUserNFT unlock",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["timed_nft_id"],
            properties={
                "timed_nft_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(
                description="Invoice link for speeding up unlock",
                examples={
                    "application/json": {
                        "link": "https://example.com/invoice_link",
                    }
                },
            ),
            400: "Invalid data or TimedUserNFT not found",
        },
    )
    @require_auth
    def post(self, request):
        timed_nft_id = request.data.get("timed_nft_id")
        if not timed_nft_id:
            return Response(
                {"error": "timed_nft_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            user_profile: UserProfile = request.user_profile
            timed_nft = TimedUserNFT.objects.filter(id=timed_nft_id, user=user_profile).first()
            if not timed_nft:
                return Response(
                    {"error": "TimedUserNFT not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not timed_nft.block_until or timed_nft.block_until <= timezone.now():
                return Response(
                    {"error": "NFT is not blocked or already unlocked"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config = GradationConfig.objects.filter(name=timed_nft.name).first()
            if not config:
                config = GradationConfig(name="", gradation_minutes=1, gradation_value=5)
                # return Response(
                #     {"error": "Config not found"},
                #     status=status.HTTP_400_BAD_REQUEST,
                # )

                
            remaining_minutes = max(
                0, (timed_nft.block_until - timezone.now()).total_seconds() / 60
            )
            price = math.ceil(remaining_minutes / config.gradation_minutes) * config.gradation_value
            final_price = int(price * user_profile.sbt_get_stars_discount())
            # final_price = price
            link = bot.create_invoice_link(
                title="Ускорение разблокировки NFT",
                description=f"Ускорение разблокировки NFT",
                currency="XTR",
                provider_token="",
                prices=[LabeledPrice(label="XTR", amount=final_price)],
                payload=f"speed_timed_nft_unblock:{timed_nft_id}",
            )
            return Response(
                {"link": link},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )



class CurrentWalletInfoView(APIView):
    @swagger_auto_schema(
        tags=["control"],
        operation_description="Get current wallet information for the authenticated user",
        responses={
            200: openapi.Response(
                description="Current wallet information",
            ),
            404: "Wallet not found",
        },
    )
    @require_auth
    def get(self, request):
        user_profile: UserProfile = request.user_profile
        wallet = WalletInfo.objects.filter(user=user_profile, wallet=user_profile.ton_wallet).first()
        if not wallet:
            return Response(
                {"error": "Wallet not found"}, status=status.HTTP_404_NOT_FOUND
            )
        data = WalletInfoSerializer(wallet).data
        return Response(data, status=status.HTTP_200_OK)


class CurrentWalletInfoStarsView(APIView):
    @swagger_auto_schema(
        tags=["control"],
        operation_description="Get invoice link for speeding up TimedUserNFT unlock",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["timed_nft_id"],
            properties={
                "timed_nft_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: openapi.Response(
                description="Invoice link for speeding up unlock",
                examples={
                    "application/json": {
                        "link": "https://example.com/invoice_link",
                    }
                },
            ),
            400: "Invalid data or TimedUserNFT not found",
        },
    )
    @require_auth
    def post(self, request):
        try:
            user_profile: UserProfile = request.user_profile
            wallet_info = WalletInfo.objects.filter(user=user_profile, wallet=user_profile.ton_wallet).first()
            if not wallet_info:
                return Response(
                    {"error": "Wallet not found"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if not wallet_info.block_until or wallet_info.block_until <= timezone.now():
                return Response(
                    {"error": "NFT is not blocked or already unlocked"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            config = GradationConfig.objects.filter(name="Wallet").first()
            if not config:
                config = GradationConfig(name="", gradation_minutes=1, gradation_value=5)
                return Response(
                    {"error": "Config not found"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

                
            remaining_minutes = max(
                0, (wallet_info.block_until - timezone.now()).total_seconds() / 60
            )
            price = math.ceil(remaining_minutes / config.gradation_minutes) * config.gradation_value
            # final_price = int(price * user_profile.sbt_get_stars_discount())
            final_price = price
            link = bot.create_invoice_link(
                title="Ускорение разблокировки кошелька",
                description=f"Ускорение разблокировки кошелька",
                currency="XTR",
                provider_token="",
                prices=[LabeledPrice(label="XTR", amount=final_price)],
                payload=f"speed_wallet_unblock:{wallet_info.id}",
            )
            return Response(
                {"link": link},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )
            
            

class SwitchOrbitalView(APIView):
    @swagger_auto_schema(
        responses={
            200: "OK",
            400: "Bad Request",
        },
    )
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile
        
        if not user_profile.has_orbital_station:
            return Response({"error": "User does not have an orbital station"}, status=400)
        if not user_profile.orbital_first_owner:
            return Response({"error": "User is not the first owner of the orbital station"}, status=400)

        if float(request.data.get("token_amount")) == 0:
            resp = Response({"message": "Switched"}, status=200)
        else:
            resp = common_withdrawal(request)
            
        if resp.status_code == 200:
            if user_profile.orbital_is_blue:
                UserProfile.objects.filter(id=user_profile.id).update(
                    orbital_is_blue=False
                )
                user_profile.refresh_from_db()
                user_profile.check_storage_generation()
            else:
                UserProfile.objects.filter(id=user_profile.id).update(
                    orbital_is_blue=True
                )
                user_profile.refresh_from_db()
                user_profile.check_storage_generation()
            return resp
        else:
            return resp

class SwitchOrbitalStationView(APIView):
    @swagger_auto_schema(
        responses={
            200: "OK",
            400: "Bad Request",
        },
    )
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile
        
        if not user_profile.has_orbital_station:
            return Response({"error": "User does not have an orbital station"}, status=400)
        if not user_profile.orbital_first_owner:
            return Response({"error": "User is not the first owner of the orbital station"}, status=400)

        is_basic_now = user_profile.orbital_force_basic

        if is_basic_now:
            # відключаєм базову, включаєм НФТ
            with transaction.atomic():
                UserProfile.objects.filter(user_id=user_profile.user_id).update(
                orbital_force_basic=False,
                hydro_prev_energy=F("energy"),
                power=F("hydro_prev_power"),
                hydro_prev_power=F("power"),
                hydro_prev_station_type=F("station_type"),
                hydro_prev_storage_level=F("storage_level"),
                hydro_prev_generation_level=F("generation_level"),
                hydro_prev_engineer_level=F("engineer_level"),
                station_type="Dyson Sphere",
                storage_level=3,
                generation_level=3,
                engineer_level=45,
                energy=0,
                storage=0,
                storage_limit=2320,
            generation_rate=290 if user_profile.orbital_first_owner else 580,
            kw_per_tap=EngineerConfig.objects.get(
                level=45
            ).tap_power
            )
        else:
            # відключаєм НФТ, включаєм базову
            # Обновляем объект для получения актуальных значений
            user_profile.refresh_from_db()
            
            with transaction.atomic():
                # Логируем баланс энергии на момент отката orbital станции
                StationRollbackLog.objects.create(
                    user=user_profile,
                    from_station=user_profile.station_type,
                    generation_level=user_profile.generation_level,
                    storage_level=user_profile.storage_level,
                    engineer_level=user_profile.engineer_level,
                    energy=user_profile.energy,
                    nft_address=user_profile.current_station_nft if user_profile.current_station_nft else "",
                )
                
                UserProfile.objects.filter(user_id=user_profile.user_id).update(
                    orbital_force_basic=True,
                    energy=F("hydro_prev_energy")+(F("energy") if (user_profile.orbital_first_owner and not user_profile.orbital_is_blue) else 0),
                    power=F("hydro_prev_power"),
                    hydro_prev_power=F("power"),
                    station_type=F("hydro_prev_station_type"),
                    storage_level=F("hydro_prev_storage_level"),
                    generation_level=F("hydro_prev_generation_level"),
                    engineer_level=F("hydro_prev_engineer_level"),
                    storage=0,
                    storage_limit=StoragePowerStationConfig.objects.filter(
                        station_type=user_profile.hydro_prev_station_type,
                        level=user_profile.hydro_prev_storage_level,
                    )
                    .first()
                    .storage_limit,
                generation_rate=GenPowerStationConfig.objects.filter(
                    station_type=user_profile.hydro_prev_station_type,
                    level=user_profile.hydro_prev_generation_level,
                )
                .first()
                .generation_rate,
                kw_per_tap=EngineerConfig.objects.get(
                    level=user_profile.hydro_prev_engineer_level
                ).tap_power
                )
        return Response({"success": True}, status=200)

class CraftNFTView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                "nft1": openapi.Schema(type=openapi.TYPE_STRING, description="ID of the first NFT"),
                "nft2": openapi.Schema(type=openapi.TYPE_STRING, description="ID of the second NFT"),
            },
            required=["nft1", "nft2"]
        ),
        responses={
            200: openapi.Response(
                description="Successful NFT crafting",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "success": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "crafted_nft": openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Bad Request",
        },
    )
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile
        nft1_addr = request.data.get("nft1")
        nft2_addr = request.data.get("nft2")

        nft1 = NFTDatabase.objects.get(nft=nft1_addr)
        nft2 = NFTDatabase.objects.get(nft=nft2_addr)
        
        price = 15000
        if user_profile.tbtc_wallet < price:
            return Response({"error": "Insufficient funds"}, status=400)

        UserProfile.objects.filter(id=user_profile.id).update(
            tbtc_wallet=F("tbtc_wallet") - price
        )

        crafted_nft = random.choices([
            "SX Ultra",
            "S21",
            "S19",
            "S17",
        ], weights=[30, 50, 15, 5])

        return Response({"success": True, "crafted_nft": crafted_nft}, status=200)
    
    
class TestEndpointView(APIView):
    @swagger_auto_schema(
        tags=["test"],
        operation_description="Test endpoint to verify API functionality",
        responses={
            200: openapi.Response(
                description="Test endpoint returned successfully",
                examples={
                    "application/json": {
                        "message": "Test endpoint returned successfully"
                    }
                },
            ),
        },
    )
    def get(self, request):
        return Response(
            {"message": "Test endpoint returned successfully"},
            status=status.HTTP_200_OK,
        )