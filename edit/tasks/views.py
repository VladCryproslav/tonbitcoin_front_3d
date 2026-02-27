from datetime import timedelta
from django.shortcuts import render
from rest_framework import generics

from core.serializers import UserProfileSerializer
from .models import (
    Task,
    UserTask,
    TaskCategory,
    WheelSlot,
    UserReward,
    Booster,
    WheelSlot2,
)
from .serializers import (
    TaskSerializer,
    UserTaskSerializer,
    TaskCategorySerializer,
    UserRewardSerializer,
    BoosterSerializer,
    WheelSlotSerializer,
)
from core.views import require_auth
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from rest_framework.views import APIView
from .services import activate_booster, check_task_completion
from core.models import UserProfile, WithdrawalConfig, add_wheel_stat
from django.utils import timezone
from django.db.models import F
from drf_yasg import openapi
import random


class CheckTaskCompletionView(APIView):
    @swagger_auto_schema(
        operation_description="Перевірити виконання завдання користувачем",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                "user_task_id",
            ],
            properties={
                "user_task_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={200: "Task completed", 400: "Task not completed"},
    )
    @require_auth
    def post(self, request):
        user_task_id = request.data.get("user_task_id")
        if user_task_id is None:
            return Response(
                {"status": "Task id is required"}, status=status.HTTP_400_BAD_REQUEST
            )
        user_task_id = int(user_task_id)

        user_profile = request.user_profile
        user_task = (
            UserTask.objects.select_related("task")
            .filter(id=user_task_id, profile=user_profile)
            .first()
        )

        if user_task is None:
            return Response(
                {"status": "Task not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        if user_task.claimed:
            return Response(
                {"status": "Task already claimed"}, status=status.HTTP_400_BAD_REQUEST
            )

        if not user_task.started:
            UserTask.objects.filter(id=user_task_id).update(started=True)
            return Response(
                {"status": "Task started"}, status=status.HTTP_400_BAD_REQUEST
            )

        if check_task_completion(user_profile, user_task.task, user_task):
            UserTask.objects.filter(id=user_task_id).update(
                claimed=True, claimed_at=timezone.now(), completed=True
            )
            if user_task.task.reward_type == "kW":
                UserProfile.objects.filter(id=user_profile.id).update(
                    kw_wallet=F("kw_wallet") + user_task.task.reward_amount
                )
            elif user_task.task.reward_type == "tBTC":
                UserProfile.objects.filter(id=user_profile.id).update(
                    tbtc_wallet=F("tbtc_wallet") + user_task.task.reward_amount
                )
            return Response({"status": "Task claimed"}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"status": "Task not completed"}, status=status.HTTP_400_BAD_REQUEST
            )


from rest_framework.generics import ListAPIView

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter


class UserTasksView(ListAPIView):

    queryset = UserTask.objects.all()
    serializer_class = UserTaskSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["task__categories"]

    @swagger_auto_schema(
        operation_description="Отримати дані по завданням користувача",
        responses={200: UserTaskSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        user_profile = request.user_profile

        new_tasks = Task.objects.exclude(
            id__in=UserTask.objects.filter(profile=user_profile).values_list(
                "task__id", flat=True
            )
        )

        if new_tasks.exists():
            user_tasks = [
                UserTask(profile=user_profile, task=task) for task in new_tasks
            ]

            UserTask.objects.bulk_create(user_tasks)

        category_ids = request.query_params.getlist("task__categories")
        if category_ids:
            user_tasks = (
                UserTask.objects.filter(
                    profile=user_profile, task__categories__id__in=category_ids
                )
                .order_by("task__order_number")
                .distinct()
            )
        else:
            user_tasks = UserTask.objects.filter(profile=user_profile).order_by(
                "task__order_number"
            )
        serializer = UserTaskSerializer(user_tasks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TaskCategoriesView(APIView):
    @swagger_auto_schema(
        operation_description="Отримати всі категорії завдань",
        responses={200: TaskCategorySerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        categories = TaskCategory.objects.all()
        serializer = TaskCategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


def get_prize(currency: str, user_profile: UserProfile):
    if user_profile.wheel_slot2:
        wheel_slots = WheelSlot2.objects.all()
    else:
        wheel_slots = WheelSlot.objects.all()
    if user_profile.engineer_level >= 49:
        wheel_slots = wheel_slots.exclude(
            asset_name="electrics"
        )
    # Исключаем призы инженеров, если активна орбитальная (Special), гидро или Singularity
    is_blocked = (
        (user_profile.has_orbital_station and not user_profile.orbital_force_basic) or
        user_profile.has_hydro_station or
        getattr(user_profile, "has_singularity_station", False)
    )
    if is_blocked:
        wheel_slots = wheel_slots.exclude(
            asset_name="electrics"
        )
    if not wheel_slots.exists():
        return False, False

    wheel_slots = list(wheel_slots)

    if currency == "kW":
        probabilities = [slot.probability_kW for slot in wheel_slots]
    elif currency == "tBTC":
        probabilities = [slot.probability_tBTC for slot in wheel_slots]
    elif currency == "Stars":
        probabilities = [slot.probability_stars for slot in wheel_slots]
    else:
        return False, False

    # cumulative_probability = 0
    # selected_slot = None

    # print(probabilities, [f"{i.asset_name} {i.asset_quantity}" for i in wheel_slots])
    selected_slot = random.choices(wheel_slots, weights=probabilities)[0]
    # print(f"{random_choice}/{total_probability}, {probabilities}")
    # for slot, probability in zip(wheel_slots, probabilities):
    #     print(f"{cumulative_probability}, {probability}")
    #     cumulative_probability += probability
    #     if random_choice <= cumulative_probability:
    #         print(f"win {cumulative_probability}, {probability}, {slot}")
    #         selected_slot = slot
    #         break
    
    selected_slot = WheelSlot.objects.get(order_number=selected_slot.order_number)

    # Створюємо винагороду на основі типу слота
    if selected_slot:
        # Визначаємо тип обробки
        if selected_slot.asset_name in ["kW", "tBTC"]:
            processing_type = "automatic"
        elif selected_slot.asset_name in ["autostart", "azot", "powerbank", "electrics", "jarvis", "magnit", "asic_manager"]:
            processing_type = "automatic"  # Бустери теж автоматично
        else:
            processing_type = "manual"  # ASIC, Stars, Chip

        reward = UserReward.objects.create(
            profile=user_profile,
            slot=selected_slot,
            asset_type=selected_slot.asset_name,
            n_parameter=selected_slot.n_parameter,
            asset_quantity=getattr(selected_slot, 'asset_quantity', None),
            status="unclaimed",
            processing_type=processing_type,
            paid_with=currency,
            random_val=0,
            wallet=user_profile.ton_wallet,
        )

        add_wheel_stat(reward)
        return (
            reward,
            selected_slot,
        )
    else:
        return False, False


from shared import setup_logger

action_logger = setup_logger()


class SpinWheelView(APIView):
    @swagger_auto_schema(
        operation_description="Вращать колесо фортуны",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["currency"],
            properties={
                "currency": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=["kW", "tBTC"],
                ),
            },
        ),
        responses={200: "Prize awarded", 400: "Insufficient balance"},
    )
    @require_auth
    def post(self, request):
        currency = request.data.get("currency")
        user_profile: UserProfile = request.user_profile
        try:
            if currency not in ["kW", "tBTC"]:
                return Response(
                    {"status": "Unknown currency"}, status=status.HTTP_400_BAD_REQUEST
                )
            withdraw_config = WithdrawalConfig.objects.first() or None
            kw_price = getattr(withdraw_config, "wheel_kw_cost", 1500)
            tbtc_price = getattr(withdraw_config, "wheel_tbtc_cost", 100)

            if currency == "kW" and user_profile.kw_wallet < kw_price:
                return Response(
                    {"status": "Insufficient kW balance"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            elif currency == "tBTC" and user_profile.tbtc_wallet < tbtc_price:
                return Response(
                    {"status": "Insufficient tBTC balance"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if currency == "kW":
                UserProfile.objects.filter(id=user_profile.id).update(
                    kw_wallet=F("kw_wallet") - kw_price
                )
            elif currency == "tBTC":
                UserProfile.objects.filter(id=user_profile.id).update(
                    tbtc_wallet=F("tbtc_wallet") - tbtc_price
                )

            prize, slot = get_prize(currency, user_profile)
            if prize:
                return Response(
                    {
                        "status": "Prize awarded",
                        "prize": UserRewardSerializer(prize).data,
                        "slot_id": slot.pk,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                action_logger.info(
                    f"{user_profile.user_id} WRONG PRIZE, currency: {currency}"
                )
                return Response(
                    {"status": "No prize awarded"}, status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            action_logger.exception(
                f"ERROR PRIZE {user_profile.user_id} currency: {currency}"
            )


from rest_framework.pagination import PageNumberPagination


class RewardsInfoPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = (
        "page_size"
    )
    max_page_size = 200


class UserRewardsView(ListAPIView):
    queryset = UserReward.objects.all()
    serializer_class = UserRewardSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["status", "asset_type"]
    ordering_fields = ["created_at"]

    pagination_class = RewardsInfoPagination

    @swagger_auto_schema(
        operation_description="Отримати історію наград користувача",
        responses={200: UserRewardSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        user_profile = request.user_profile
        user_rewards = UserReward.objects.filter(profile=user_profile).order_by(
            "-status", "-created_at"
        )
        filtered = self.filter_queryset(user_rewards)
        page = self.paginate_queryset(filtered)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(filtered, many=True)
        return Response(serializer.data)


from django.conf import settings
from telebot import types, TeleBot

bot = TeleBot(settings.BOT_TOKEN, parse_mode="HTML")
from telebot.types import LabeledPrice


class WheelStarsView(APIView):
    @require_auth
    def post(self, request):
        user_profile: UserProfile = request.user_profile
        withdraw_config = WithdrawalConfig.objects.first() or None
        stars_price = int(getattr(withdraw_config, "wheel_stars_cost", 100))
        final_price = int(stars_price * user_profile.sbt_get_stars_discount())
        try:
            link = bot.create_invoice_link(
                title="Рулетка за Stars",
                description=f"Рулетка за {final_price} Stars",
                currency="XTR",
                provider_token="",
                prices=[LabeledPrice(label="XTR", amount=final_price)],
                payload=f"wheel_stars",
            )
            return Response(
                {"link": link},
                status=status.HTTP_200_OK,
            )
        except UserProfile.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

from .services import apply_booster_reward

class ClaimUserRewardView(APIView):
    @swagger_auto_schema(
        operation_description="Отримати нагороду користувача за ID",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["reward_id"],
            properties={
                "reward_id": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={200: "Reward claimed", 400: "Reward not found or already claimed"},
    )
    @require_auth
    def post(self, request):
        reward_id = request.data.get("reward_id")
        if reward_id is None:
            return Response(
                {"status": "Reward ID is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        user_profile = request.user_profile
        user_reward = UserReward.objects.filter(
            id=reward_id, profile=user_profile
        ).first()

        if user_reward is None:
            return Response(
                {"status": "Reward not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        if user_reward.status == "claimed":
            return Response(
                {"status": "Reward already claimed"}, status=status.HTTP_400_BAD_REQUEST
            )

        if user_reward.status == "processing":
            return Response(
                {"status": "Reward in processing"}, status=status.HTTP_400_BAD_REQUEST
            )

        if user_reward.asset_type == "kW":
            UserProfile.objects.filter(id=user_profile.id).update(
                kw_wallet=F("kw_wallet") + user_reward.asset_quantity
            )
            UserReward.objects.filter(id=reward_id).update(status="claimed")
        elif user_reward.asset_type == "tBTC":
            UserProfile.objects.filter(id=user_profile.id).update(
                tbtc_wallet=F("tbtc_wallet") + user_reward.asset_quantity
            )
            UserReward.objects.filter(id=reward_id).update(status="claimed")
        elif user_reward.asset_type in ["autostart", "azot", "powerbank", "electrics", "jarvis", "magnit", "asic_manager"]:
            # Блокируем забор приза инженеров, если активна орбитальная (Special), гидро или Singularity
            if user_reward.asset_type == "electrics":
                is_blocked = (
                    (user_profile.has_orbital_station and not user_profile.orbital_force_basic) or
                    user_profile.has_hydro_station or
                    getattr(user_profile, "has_singularity_station", False)
                )
                if is_blocked:
                    return Response(
                        {"status": "Engineers reward cannot be claimed with active orbital (Special), hydro or singularity station"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            # Обробка бустерів
            success, message = apply_booster_reward(user_profile, user_reward)
            
            if success:
                UserReward.objects.filter(id=reward_id).update(status="claimed")
                return Response({"status": "Reward claimed"}, status=status.HTTP_200_OK)
            else:
                return Response({"status": message}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # ASIC, Stars, Chip та інші - ручна обробка
            UserReward.objects.filter(id=reward_id).update(status="processing")

        return Response({"status": "Reward claimed"}, status=status.HTTP_200_OK)


class BoosterListView(ListAPIView):
    queryset = Booster.objects.all()
    serializer_class = BoosterSerializer

    @swagger_auto_schema(
        operation_description="Отримати список всіх бустерів",
        responses={200: BoosterSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        boosters = Booster.objects.all()
        serializer = BoosterSerializer(boosters, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ActivateBoosterFTBCView(APIView):
    @swagger_auto_schema(
        operation_description="Активувати бустер за slug",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["slug"],
            properties={
                "slug": openapi.Schema(type=openapi.TYPE_STRING),
                "day_count": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: "Booster activated",
            400: "Booster not found or already active",
        },
    )
    @require_auth
    def post(self, request):
        slug = request.data.get("slug")
        day_count = request.data.get("day_count")
        if not slug:
            return Response(
                {"status": "Slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        booster = Booster.objects.filter(slug=slug).first()

        if not booster:
            return Response(
                {"status": "Booster not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        user_profile: UserProfile = request.user_profile

        price = activate_booster(user_profile, booster, day_count, fbtc=True)
        if day_count:
            desc = f"на {day_count} дней"
        else:
            desc = ""
        if price is None:
            return Response(
                {"status": "Cannot activate booster"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        final_price = price
        if price > 0:
            if user_profile.tbtc_wallet < final_price:
                return Response(
                    {"status": "Insufficient fBTC balance"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            UserProfile.objects.filter(id=user_profile.id).update(
                tbtc_wallet=F("tbtc_wallet") - final_price
            )
            
            if booster.slug == "azot":
                UserProfile.objects.filter(id=user_profile.id).update(
                    azot_counts=F("azot_counts") + 1,
                    overheated_until=None,
                    tap_count_since_overheat=0,
                    was_overheated=False,  # Сбрасываем флаг перегрева при активации азота
                )
                user_profile.refresh_from_db()
            elif booster.slug == "jarvis":
                days = int(day_count) if day_count else 1
                now = timezone.now()
                jarvis_expires = user_profile.jarvis_expires
                is_active = jarvis_expires and jarvis_expires > now

                if not is_active:
                    jarvis_expires = now

                jarvis_expires += timedelta(days=days)

                if jarvis_expires > now + timedelta(days=31):
                    return Response(
                        {"status": "Booster cannot be activated for more than 31 days"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    jarvis_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    jarvis_expires=jarvis_expires
                )
            elif booster.slug == "cryo":
                days = int(day_count) if day_count else 1
                now = timezone.now()
                cryo_expires = user_profile.cryo_expires
                is_active = cryo_expires and cryo_expires > now

                if not is_active:
                    cryo_expires = now

                cryo_expires += timedelta(days=days)

                if cryo_expires > now + timedelta(days=31):
                    return Response(
                        {"status": "Booster cannot be activated for more than 31 days"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    cryo_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    cryo_expires=cryo_expires
                )
            elif booster.slug == "autostart":
                days = int(day_count) if day_count else 1
                UserProfile.objects.filter(id=user_profile.id).update(
                    autostart_count=F("autostart_count") + days
                )
            elif booster.slug == "magnit":
                days = int(day_count) if day_count else 1
                now = timezone.now()
                magnit_expires = user_profile.magnit_expires
                is_active = magnit_expires and magnit_expires > now

                if not is_active:
                    magnit_expires = now

                magnit_expires += timedelta(days=days)

                if magnit_expires > now + timedelta(days=31):
                    return Response(
                        {"status": "Booster cannot be activated for more than 31 days"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    magnit_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    magnit_expires=magnit_expires,
                    magnit_buy_hashrate=F("mining_farm_speed"),
                )
            elif booster.slug == "asic_manager":
                days = int(day_count) if day_count else 1
                now = timezone.now()
                manager_expires = user_profile.manager_expires
                is_active = manager_expires and manager_expires > now

                if not is_active:
                    manager_expires = now

                manager_expires += timedelta(days=days)

                if manager_expires > now + timedelta(days=31):
                    return Response(
                        {"status": "Booster cannot be activated for more than 31 days"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    manager_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    manager_expires=manager_expires,
                    manager_buy_hashrate=F("mining_farm_speed"),
                )
            elif booster.slug == "electrics":
                days = int(day_count) if day_count else 1
                now = timezone.now()
                electrics_expires = user_profile.electrics_expires
                is_active = electrics_expires and electrics_expires > now

                if not is_active:
                    electrics_expires = now

                electrics_expires += timedelta(days=days)

                if electrics_expires > now + timedelta(days=31):
                    return Response(
                        {"status": "Booster cannot be activated for more than 31 days"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    electrics_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    electrics_expires=electrics_expires
                )
            elif booster.slug == "premium_sub":
                days = int(day_count) if day_count else 1
                now = timezone.now()
                premium_sub_expires = user_profile.premium_sub_expires
                is_active = premium_sub_expires and premium_sub_expires > now

                if not is_active:
                    premium_sub_expires = now

                premium_sub_expires += timedelta(days=days)

                if premium_sub_expires > now + timedelta(days=31):
                    return Response(
                        {"status": "Booster cannot be activated for more than 31 days"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    premium_sub_expires = now + timedelta(days=31)

                UserProfile.objects.filter(id=user_profile.id).update(
                    premium_sub_expires=premium_sub_expires
                )
            elif booster.slug == "repair_kit":
                days = int(day_count) if day_count else 1
                now = timezone.now()
                repair_kit_expires = user_profile.repair_kit_expires
                is_active = repair_kit_expires and repair_kit_expires > now

                if not is_active:
                    repair_kit_expires = now

                repair_kit_expires += timedelta(days=days)

                if repair_kit_expires > now + timedelta(days=31):
                    return Response(
                        {"status": "Booster cannot be activated for more than 31 days"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                    repair_kit_expires = now + timedelta(days=31)

                # Сохраняем текущий уровень power при активации
                UserProfile.objects.filter(id=user_profile.id).update(
                    repair_kit_expires=repair_kit_expires,
                    repair_kit_power_level=user_profile.power,  # Новое поле для хранения уровня
                )
        # if price > 0:
        #     link = bot.create_invoice_link(
        #         title=f"Покупка бустера {booster.title}",
        #         description=f"Покупка бустера {booster.title} {desc}",
        #         currency="XTR",
        #         provider_token="",
        #         prices=[LabeledPrice(label="XTR", amount=final_price)],
        #         payload=f"booster:{slug}:{day_count}",
        #     )
        #     return Response(
        #         {"link": link},
        #         status=status.HTTP_200_OK,
        #     )

        user_profile.refresh_from_db()
        return Response(
            {
                "status": "Booster activated",
                "user": UserProfileSerializer(user_profile).data,
            },
            status=status.HTTP_200_OK,
        )


class ActivateBoosterView(APIView):
    @swagger_auto_schema(
        operation_description="Активувати бустер за slug",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=["slug"],
            properties={
                "slug": openapi.Schema(type=openapi.TYPE_STRING),
                "day_count": openapi.Schema(type=openapi.TYPE_INTEGER),
            },
        ),
        responses={
            200: "Booster activated",
            400: "Booster not found or already active",
        },
    )
    @require_auth
    def post(self, request):
        slug = request.data.get("slug")
        day_count = request.data.get("day_count")
        if not slug:
            return Response(
                {"status": "Slug is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        booster = Booster.objects.filter(slug=slug).first()

        if not booster:
            return Response(
                {"status": "Booster not found"}, status=status.HTTP_400_BAD_REQUEST
            )

        user_profile: UserProfile = request.user_profile

        price = activate_booster(user_profile, booster, day_count)
        if day_count:
            desc = f"на {day_count} дней"
        else:
            desc = ""
        if price is None:
            return Response(
                {"status": "Cannot activate booster"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if slug=="premium_sub":
            final_price = int(price)
        else:
            final_price = int(price * user_profile.sbt_get_stars_discount())
        if price > 0:
            link = bot.create_invoice_link(
                title=f"Покупка бустера {booster.title}",
                description=f"Покупка бустера {booster.title} {desc}",
                currency="XTR",
                provider_token="",
                prices=[LabeledPrice(label="XTR", amount=final_price)],
                payload=f"booster:{slug}:{day_count}",
            )
            return Response(
                {"link": link},
                status=status.HTTP_200_OK,
            )

        user_profile.refresh_from_db()
        return Response(
            {
                "status": "Booster activated",
                "user": UserProfileSerializer(user_profile).data,
            },
            status=status.HTTP_200_OK,
        )


class WheelSlotsView(APIView):
    @swagger_auto_schema(
        operation_description="Отримати всі слоти рулетки",
        responses={200: WheelSlotSerializer(many=True)},
    )
    @require_auth
    def get(self, request):
        slots = WheelSlot.objects.order_by("order_number").all()
        serializer = WheelSlotSerializer(slots, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
