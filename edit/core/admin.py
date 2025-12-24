from datetime import datetime

import django
import pytoniq_core
from django import forms
from django.contrib import admin, messages
from django.db.models import F
from django.shortcuts import redirect, render
from django.urls import path
from django.utils import timezone

from core import models
from tasks.models import UserRewardReport

from .models import NFTDatabase, NFTRentalAgreement, OrbitalOwner, StationUpgradeEvent  # Import the NFTRentalAgreement model
from .models import Notification  # Import the Notification model
from .models import (
    AsicsCoefs,
    AutoWithdrawalRequest,
    BoosterRefund,
    EngineerConfig,
    GenPowerStationConfig,
    GlobalSpendStats,
    GlobalStats,
    HashrateInfo,
    KwCommissions,
    MiningCommissions,
    MintRequest,
    NFTRentalConfig,
    NFTStation,
    OverheatConfig,
    RentalCommissions,
    RepairPowerStationConfig,
    RoadmapItem,
    StakingPeriodConfig,
    StationNFTOwner,
    StationRollbackLog,
    StoragePowerStationConfig,
    TbtcCommissions,
    UserActionLog,
    UserProfile,
    UserProfileWheelProxy,
    UserStaking,
    WheelStats,
    WithdrawalRequest,
)


class AdjustPointsForm(forms.Form):
    points = forms.IntegerField(label="Кількість поінтів", required=True)


# Register your models here.
@admin.register(RoadmapItem)
class RoadmapItemAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "order")
    list_editable = ("status", "order")
    ordering = ("order",)
    search_fields = ("title",)


@admin.register(GenPowerStationConfig)
class GenPowerStationConfigAdmin(admin.ModelAdmin):
    list_display = (
        "station_type",
        "level",
        "price_kw",
        "price_tbtc",
        "generation_rate",
    )
    list_filter = ("station_type", "level")
    search_fields = ("station_type",)


@admin.register(StoragePowerStationConfig)
class StoragePowerStationConfigAdmin(admin.ModelAdmin):
    list_display = (
        "station_type",
        "level",
        "price_kw",
        "price_tbtc",
        "storage_limit",
    )
    list_filter = ("station_type", "level")
    search_fields = ("station_type",)


@admin.register(RepairPowerStationConfig)
class RepairPowerStationConfigAdmin(admin.ModelAdmin):
    list_display = (
        "station_type",
        "price_kw",
        "price_tbtc",
    )
    list_filter = ("station_type",)
    search_fields = ("station_type",)


# from advanced_filters.admin import AdminAdvancedFiltersMixin
import csv

from django.http import HttpResponse
from rangefilter.filters import DateRangeFilter, DateTimeRangeFilter, NumericRangeFilter

MAX_LENGTH = 20
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "short_first_name",
        "username",
        "formatted_energy",
        "kw_wallet",
        "tbtc_wallet",
        "mined_tokens_balance",
        "station_type",
        "formatted_storage",
        "formatted_storage_limit",
        "formatted_generation_rate",
        "formatted_power",
        "register_date",
    )
    readonly_fields = (
        "last_kw_bonus_claimed_at",
        "last_tbtc_bonus_claimed_at",
        "last_staking_bonus_claimed_at",
        "register_date",
    )

    def formatted_energy(self, obj):
        return f"{obj.energy:.3f}"

    formatted_energy.short_description = "energy"
    formatted_energy.admin_order_field = "energy"

    def formatted_storage(self, obj):
        return f"{obj.storage:.3f}"

    formatted_storage.short_description = "storage"
    formatted_storage.admin_order_field = "storage"

    def formatted_storage_limit(self, obj):
        return f"{obj.storage_limit:.3f}"

    formatted_storage_limit.short_description = "Storage limit"
    formatted_storage_limit.admin_order_field = "storage_limit"

    def formatted_generation_rate(self, obj):
        return f"{obj.generation_rate:.3f}"

    formatted_generation_rate.short_description = "Generation rate"
    formatted_generation_rate.admin_order_field = "generation_rate"

    def formatted_power(self, obj):
        return f"{obj.power:.3f}"

    formatted_power.short_description = "power"
    formatted_power.admin_order_field = "power"
    
    def short_first_name(self, obj):
        name = obj.first_name or ""
        return (name[:MAX_LENGTH] + "...") if len(name) > MAX_LENGTH else name
    short_first_name.short_description = "First name"
    short_first_name.admin_order_field = "first_name"

    list_filter = [
        "station_type",
        ("energy", NumericRangeFilter),
        ("kw_wallet", NumericRangeFilter),
        ("tbtc_wallet", NumericRangeFilter),
        ("user_id", NumericRangeFilter),
        ("storage_level", NumericRangeFilter),
        ("generation_level", NumericRangeFilter),
        ("register_date", DateTimeRangeFilter),
        ("referrer__user_id", NumericRangeFilter),
    ]

    actions = ["export_as_csv"]

    def export_as_csv(self, request, queryset):
        meta = self.model._meta
        field_names = [field.name for field in meta.fields]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={}.csv".format(meta)
        writer = csv.writer(response)

        writer.writerow(field_names + ["staking_amount"])
        for obj in queryset:
            stakings = UserStaking.objects.filter(
                user=obj,
                last_collected__lt=F("end_date"),
                confirmed=True,
            )
            now = timezone.now()
            token_amount = 0
            for s in stakings:
                curr = now
                if s.end_date < now:
                    curr = s.end_date
                days_passed = (curr - s.last_collected).total_seconds() / 24 / 60 / 60
                daily_profit = float(s.token_amount) * float(s.apr) / 100 / 365
                collected = daily_profit * days_passed
                token_amount += collected
            row = writer.writerow(
                [getattr(obj, field) for field in field_names] + [token_amount]
            )

        return response

    export_as_csv.short_description = "Export Selected"

    search_fields = ("user_id", "station_type", "ton_wallet", "username", "first_name")

    autocomplete_fields = ["referrer", "referrer_level_2"]

    # change_list_template = "admin/adjust_points.html"

    # def get_urls(self):
    #     urls = super().get_urls()
    #     custom_urls = [
    #         path(
    #             "adjust-points/<int:user_id>/",
    #             self.admin_site.admin_view(self.adjust_points),
    #             name="adjust_points",
    #         ),
    #     ]
    #     return custom_urls + urls

    # def adjust_points(self, request, user_id):
    #     if request.method == "POST":
    #         form = AdjustPointsForm(request.POST)
    #         if form.is_valid():
    #             points = form.cleaned_data["points"]
    #             UserProfile.objects.filter(user_id=user_id).update(
    #                 energy=F("energy") + points
    #             )
    #             self.message_user(request, f"Поінти успішно оновлено на {points}")
    #             return redirect("..")
    #     else:
    #         form = AdjustPointsForm()

    #     context = {
    #         "form": form,
    #         "title": "Регулювання поінтів",
    #         "user_id": user_id,
    #     }
    #     return render(request, "admin/adjust_points.html", context)


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    autocomplete_fields = ["user"]

    list_display = (
        "user",
        "wallet_address",
        "token_amount",
        "token_contract_address",
        "claimed_at",
        "processed",
        "energy",
        "tbtc_left",
        "tbtc_claimed_period",
        "station_type",
        "generation_level",
        "storage_level",
        "generation_rate",
        "is_auto",
        "note",
        "commision_percent",
    )
    list_filter = (
        "processed",
        "claimed_at",
        "token_contract_address",
        "is_auto",
        "note",
    )
    search_fields = ("user__user_id", "wallet_address", "token_contract_address")


@admin.register(EngineerConfig)
class EngineerConfigAdmin(admin.ModelAdmin):
    list_display = ("level", "tap_power", "hire_cost", "hire_cost_stars")
    ordering = ("level",)
    search_fields = ("level",)


@admin.register(AsicsCoefs)
class AsicsCoefsAdmin(admin.ModelAdmin):
    list_display = ("address", "coef")
    search_fields = ("address",)


@admin.register(OverheatConfig)
class OverheatConfigAdmin(admin.ModelAdmin):
    list_display = [field.name for field in OverheatConfig._meta.get_fields()]
    # list_editable = (
    #     "min_duration",
    #     "max_duration",
    #     "activation_count",
    #     "activation_period_minutes",
    #     "taps_before_health_reduction",
    #     "health_reduction_percentage",
    # )


from .models import WithdrawalConfig


@admin.register(WithdrawalConfig)
class WithdrawalConfigAdmin(admin.ModelAdmin):
    list_display = [field.name for field in WithdrawalConfig._meta.get_fields()]


@admin.register(AutoWithdrawalRequest)
class AutoWithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = [
        field.name
        for field in AutoWithdrawalRequest._meta.get_fields()
        if field.name != "id"
    ]
    list_filter = ["status", "token_type", "token_type", "claimed_at"]
    search_fields = ["username", "user__user_id", "tx_id"]
    autocomplete_fields = ["user"]


@admin.register(KwCommissions)
class KwCommissionsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in KwCommissions._meta.get_fields()]

    list_filter = [
        ("date", DateRangeFilter),
    ]


@admin.register(TbtcCommissions)
class TbtcCommissionsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in TbtcCommissions._meta.get_fields()]

    list_filter = [
        ("date", DateRangeFilter),
    ]


@admin.register(MiningCommissions)
class MiningCommissionsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in MiningCommissions._meta.get_fields()]

    list_filter = [
        ("date", DateRangeFilter),
    ]


@admin.register(RentalCommissions)
class RentalCommissionsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in RentalCommissions._meta.get_fields()]

    list_filter = [
        ("date", DateRangeFilter),
    ]


from django.db.models import Count, Sum, Q


@admin.register(UserProfileWheelProxy)
class UserProfileStatsAdmin(admin.ModelAdmin):
    list_display = (
        "user_id",
        "username",
        "wallet",
        "station_type",
        "total_spins",
        "total_kw_get",
        "kw_spins",
        "total_tbtc_get",
        "tbtc_spins",
        "total_stars_get",
        "stars_spins",
        "total_nft_get",
        "register_date",
    )

    search_fields = ("user_id", "station_type", "ton_wallet", "username")
    autocomplete_fields = ["referrer", "referrer_level_2"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(
            total_spins_db=Count("userreward"),
            total_kw_get_db=Sum("userreward__asset_quantity", filter=Q(userreward__asset_type="kW")),
            kw_spins_db=Count("userreward", filter=Q(userreward__paid_with="kW")),
            total_tbtc_get_db=Sum("userreward__asset_quantity", filter=Q(userreward__asset_type="tBTC")),
            tbtc_spins_db=Count("userreward", filter=Q(userreward__paid_with="tBTC")),
            total_stars_get_db=Sum("userreward__asset_quantity", filter=Q(userreward__asset_type="Stars")),
            stars_spins_db=Count("userreward", filter=Q(userreward__paid_with="Stars")),
            total_nft_get_db=Count("userreward", filter=Q(userreward__asset_type="ASIC")),
        )

    def wallet(self, obj):
        if not obj.ton_wallet:
            return ""
        return pytoniq_core.Address(obj.ton_wallet).to_str(is_user_friendly=True)

    def total_spins(self, obj):
        return obj.total_spins_db
    total_spins.admin_order_field = "total_spins_db"

    def total_kw_get(self, obj):
        return obj.total_kw_get_db
    total_kw_get.admin_order_field = "total_kw_get_db"

    def kw_spins(self, obj):
        return obj.kw_spins_db
    kw_spins.admin_order_field = "kw_spins_db"

    def total_tbtc_get(self, obj):
        return obj.total_tbtc_get_db
    total_tbtc_get.admin_order_field = "total_tbtc_get_db"

    def tbtc_spins(self, obj):
        return obj.tbtc_spins_db
    tbtc_spins.admin_order_field = "tbtc_spins_db"

    def total_stars_get(self, obj):
        return obj.total_stars_get_db
    total_stars_get.admin_order_field = "total_stars_get_db"

    def stars_spins(self, obj):
        return obj.stars_spins_db
    stars_spins.admin_order_field = "stars_spins_db"

    def total_nft_get(self, obj):
        return obj.total_nft_get_db
    total_nft_get.admin_order_field = "total_nft_get_db"


@admin.register(WheelStats)
class WheelStatsAdmin(admin.ModelAdmin):
    list_display = [field.name for field in WheelStats._meta.get_fields()]

    list_filter = [
        ("date", DateRangeFilter),
    ]


@admin.register(StakingPeriodConfig)
class StakingPeriodConfigAdmin(admin.ModelAdmin):
    list_display = ("days", "apr")
    search_fields = ("days",)


@admin.register(UserStaking)
class UserStakingAdmin(admin.ModelAdmin):
    list_display = (
        "user__user_id",
        "user__username",
        "tx_id",
        "wallet_address",
        "token_amount",
        "apr",
        "days",
        "reward",
        "collected",
        "start_date",
        "end_date",
        "status",
    )
    list_filter = ("apr", "days", "status")
    search_fields = ("user__user_id", "user__username", "tx_id")
    autocomplete_fields = ["user"]


@admin.register(HashrateInfo)
class HashrateInfoAdmin(admin.ModelAdmin):
    list_display = ("hashrate",)


@admin.register(BoosterRefund)
class BoosterRefundAdmin(admin.ModelAdmin):
    list_display = (
        "user__user_id",
        "user__username",
        "booster__slug",
        "days_left",
        "total_amount",
        "old_price",
        "new_price",
        "created_at",
        "processed",
    )
    list_filter = ("booster__slug", "processed")
    search_fields = ("user__user_id", "user__username", "booster__slug")


@admin.register(StationNFTOwner)
class MintRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "wallet",
        "nft",
    )
    search_fields = ("user__user_id", "user__username", "wallet", "nft")
    autocomplete_fields = ["user"]


@admin.register(MintRequest)
class MintRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "wallet2",
        "nft_required",
        "nft_sent_1",
        "nft_sent_2",
        "kw_spent",
        "tbtc_spent",
        "status",
        "created_at",
    )
    autocomplete_fields = ["user"]
    list_filter = ("status", "created_at")
    search_fields = ("user__user_id", "wallet")

    def wallet2(self, obj):
        if not obj.wallet:
            return ""
        return pytoniq_core.Address(obj.wallet).to_str(
            is_user_friendly=True, is_bounceable=False
        )


class NFTStationAdmin(admin.ModelAdmin):
    list_display = (
        "station_type",
        "level",
        "construction_time",
        "active_image",
        "construction_image",
    )
    search_fields = ("station_type", "level")
    list_filter = ("station_type", "level")
    readonly_fields = ("construction_time",)

    # def assign_nft_station(self, request, queryset):
    #     for station in queryset:
    #         user_id = request.POST.get("user_id")
    #         user = UserProfile.objects.get(user_id=user_id)
    #         user.nft_count += 1
    #         user.save()
    #         UserActionLog.objects.create(
    #             user=user,
    #             action="Assigned NFT station",
    #             details=f"Assigned {station.station_type} level {station.level} to user {user_id}",
    #         )
    #     self.message_user(request, "NFT station assigned successfully")

    # actions = [assign_nft_station]


admin.site.register(NFTStation, NFTStationAdmin)


class UserActionLogAdmin(admin.ModelAdmin):
    autocomplete_fields = ["user"]
    # list_display = (
    #     "user_id",
    #     "username",
    #     "wallet",
    #     "action",
    #     "details",
    #     "status",
    #     "date",
    # )
    # search_fields = ("user__user_id", "user__username", "user__ton_wallet")
    # list_filter = ("action", "status", "date")


admin.site.register(UserActionLog, UserActionLogAdmin)


def restore_station_action(modeladmin, request, queryset):
    """
    Восстановить станцию пользователя из StationRollbackLog.
    
    Действия:
    1. Восстанавливает тип станции и уровни
    2. Возвращает энергию на баланс
    3. Удаляет building_until (чтобы не было стройки)
    4. Создает запись в StationNFTOwner
    5. Обновляет статус в StationRollbackLog
    """
    from django.db import transaction
    from django.utils import timezone
    from django.db.models import F
    from core.models import StoragePowerStationConfig, GenPowerStationConfig, EngineerConfig
    
    restored_count = 0
    errors = []
    
    for rollback_log in queryset:
        # Проверка: уже восстановлено?
        if rollback_log.is_restored:
            errors.append(
                f"User {rollback_log.user.user_id}: станция уже восстановлена"
            )
            continue
        
        # Проверка: есть ли NFT адрес?
        if not rollback_log.nft_address:
            errors.append(
                f"User {rollback_log.user.user_id}: отсутствует NFT адрес. "
                f"Добавьте NFT адрес в поле 'nft_address' перед восстановлением."
            )
            continue
        
        # Проверка: есть ли данные для восстановления?
        if not rollback_log.from_station:
            errors.append(
                f"User {rollback_log.user.user_id}: отсутствует тип станции"
            )
            continue
        
        try:
            with transaction.atomic():
                user = rollback_log.user
                
                # 1. Получить конфигурации станции по уровням
                storage_config = StoragePowerStationConfig.objects.filter(
                    station_type=rollback_log.from_station,
                    level=rollback_log.storage_level or 1
                ).first()
                
                gen_config = GenPowerStationConfig.objects.filter(
                    station_type=rollback_log.from_station,
                    level=rollback_log.generation_level or 1
                ).first()
                
                engineer_config = EngineerConfig.objects.filter(
                    level=rollback_log.engineer_level or 1
                ).first()
                
                if not storage_config or not gen_config or not engineer_config:
                    errors.append(
                        f"User {rollback_log.user.user_id}: не найдены конфигурации для "
                        f"станции {rollback_log.from_station}, уровни "
                        f"storage={rollback_log.storage_level}, "
                        f"gen={rollback_log.generation_level}, "
                        f"engineer={rollback_log.engineer_level}"
                    )
                    continue
                
                # 2. Восстановить станцию в UserProfile
                # Получаем текущее значение current_mint для безопасного добавления адреса
                user_profile = UserProfile.objects.get(user_id=user.user_id)
                current_mint_value = user_profile.current_mint or ""
                
                # Добавляем адрес NFT в current_mint, если его там еще нет
                nft_address = rollback_log.nft_address
                if current_mint_value and current_mint_value != "wait":
                    # Если уже есть адреса, проверяем, нет ли там этого адреса
                    # Разделяем по запятой или переносу строки
                    existing_addresses = [addr.strip() for addr in current_mint_value.replace('\n', ',').split(',') if addr.strip()]
                    if nft_address not in existing_addresses:
                        # Добавляем новый адрес через запятую
                        current_mint_value = current_mint_value + "," + nft_address
                else:
                    # Если пустое или "wait", просто устанавливаем адрес NFT
                    current_mint_value = nft_address
                
                UserProfile.objects.filter(user_id=user.user_id).update(
                    station_type=rollback_log.from_station,
                    storage_level=rollback_log.storage_level or 1,
                    generation_level=rollback_log.generation_level or 1,
                    engineer_level=rollback_log.engineer_level or 1,
                    storage_limit=storage_config.storage_limit,
                    storage=storage_config.storage_limit,  # Устанавливаем storage равным storage_limit
                    generation_rate=gen_config.generation_rate,
                    kw_per_tap=engineer_config.tap_power,
                    current_station_nft=rollback_log.nft_address,
                    current_mint=current_mint_value,  # Добавляем адрес NFT в current_mint
                    # Возвращаем энергию на баланс
                    energy=F('energy') + (rollback_log.energy or 0),
                    # Удаляем building_until, чтобы не было стройки
                    building_until=None,
                )
                
                # 3. Создать запись в StationNFTOwner
                StationNFTOwner.objects.update_or_create(
                    user=user,
                    defaults={
                        'wallet': user.ton_wallet or '',
                        'nft': rollback_log.nft_address,
                    }
                )
                
                # 4. Обновить статус в StationRollbackLog
                rollback_log.is_restored = True
                rollback_log.restored_at = timezone.now()
                rollback_log.save(update_fields=['is_restored', 'restored_at'])
                
                restored_count += 1
                
        except Exception as e:
            errors.append(
                f"User {rollback_log.user.user_id}: ошибка при восстановлении - {str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    # Вывести результаты
    if restored_count > 0:
        modeladmin.message_user(
            request,
            f"✅ Успешно восстановлено станций: {restored_count}",
            messages.SUCCESS
        )
    
    if errors:
        error_msg = f"❌ Ошибки ({len(errors)}):\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            error_msg += f"\n... и еще {len(errors) - 10} ошибок"
        modeladmin.message_user(
            request,
            error_msg,
            messages.ERROR
        )

restore_station_action.short_description = "🔄 Восстановить станцию (Restore Station)"


def fill_current_mint_for_restored_action(modeladmin, request, queryset):
    """
    Заполнить current_mint для уже восстановленных станций.
    Безопасно добавляет адрес NFT в current_mint без дубликатов.
    """
    from django.db import transaction
    from core.models import UserProfile
    
    filled_count = 0
    skipped_count = 0
    errors = []
    
    for rollback_log in queryset:
        # Проверка: станция должна быть восстановлена
        if not rollback_log.is_restored:
            skipped_count += 1
            continue
        
        # Проверка: должен быть NFT адрес
        if not rollback_log.nft_address:
            errors.append(
                f"User {rollback_log.user.user_id}: отсутствует NFT адрес"
            )
            continue
        
        try:
            with transaction.atomic():
                user = rollback_log.user
                user_profile = UserProfile.objects.get(user_id=user.user_id)
                
                # Получаем текущее значение current_mint
                current_mint_value = user_profile.current_mint or ""
                nft_address = rollback_log.nft_address
                
                # Проверяем, нужно ли добавлять адрес
                needs_update = False
                
                if not current_mint_value or current_mint_value == "wait":
                    # Если пустое или "wait", устанавливаем адрес NFT
                    current_mint_value = nft_address
                    needs_update = True
                else:
                    # Если уже есть адреса, проверяем, нет ли там этого адреса
                    existing_addresses = [addr.strip() for addr in current_mint_value.replace('\n', ',').split(',') if addr.strip()]
                    if nft_address not in existing_addresses:
                        # Добавляем новый адрес через запятую
                        current_mint_value = current_mint_value + "," + nft_address
                        needs_update = True
                
                # Обновляем только если нужно
                if needs_update:
                    UserProfile.objects.filter(user_id=user.user_id).update(
                        current_mint=current_mint_value
                    )
                    filled_count += 1
                else:
                    skipped_count += 1
                    
        except Exception as e:
            errors.append(
                f"User {rollback_log.user.user_id}: ошибка - {str(e)}"
            )
            import traceback
            traceback.print_exc()
    
    # Вывести результаты
    result_messages = []
    if filled_count > 0:
        result_messages.append(f"✅ Заполнено current_mint для {filled_count} пользователей")
    if skipped_count > 0:
        result_messages.append(f"⏭️  Пропущено (уже заполнено или не восстановлено): {skipped_count}")
    
    if result_messages:
        modeladmin.message_user(
            request,
            "\n".join(result_messages),
            messages.SUCCESS if filled_count > 0 else messages.WARNING
        )
    
    if errors:
        error_msg = f"❌ Ошибки ({len(errors)}):\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            error_msg += f"\n... и еще {len(errors) - 10} ошибок"
        modeladmin.message_user(
            request,
            error_msg,
            messages.ERROR
        )

fill_current_mint_for_restored_action.short_description = "📝 Заполнить current_mint для восстановленных (Fill current_mint for restored)"


def fill_nft_addresses_action(modeladmin, request, queryset):
    """
    Автоматически заполнить NFT адреса для выбранных записей StationRollbackLog.
    Получает NFT адреса из TON API по типу станции.
    ОПТИМИЗИРОВАНО: использует прямой запрос NFT пользователя вместо загрузки всей коллекции.
    """
    from core.models import LinkedUserNFT
    import time
    
    # Коллекция станций
    STATION_COLLECTION = "EQB-pBhnWEYPbIu25uM1Yp5MqGFjQ-8Jes5CT2Dr-OVd705u"
    API_KEY = "AHNKO56KDTDIYGIAAAAKPVWGBLOQ2J4Z6W4ZYIP35GPCI6BSG647XSPXK6YEJHY4MTVHRFA"
    
    # Маппинг типов станций из БД в названия в NFT метаданных
    STATION_TYPE_MAPPING = {
        "Nuclear power plant": "Nuclear Power Plant",
        "Thermonuclear power plant": "Thermonuclear Power Plant",
        "Dyson Sphere": "Dyson Sphere",
        "Neutron star": "Neutron Star",
        "Boiler house": "Boiler House",
    }
    
    def get_user_nft_by_station_type_sync(wallet_address, station_type):
        """
        Получить NFT адрес конкретной станции пользователя из TON API (синхронная версия).
        Использует прямой HTTP запрос NFT пользователя, с fallback на метод через коллекцию.
        """
        try:
            expected_name = STATION_TYPE_MAPPING.get(station_type, station_type)
            
            import requests
            from pytoniq_core import Address
            from asgiref.sync import async_to_sync
            from pytonapi import AsyncTonapi
            
            # Конвертируем адрес коллекции в hex формат (как во фронтенде: "0:...")
            try:
                collection_addr = Address(STATION_COLLECTION)
                collection_hex = f"0:{collection_addr.hash_part.hex()}"
            except Exception as e:
                print(f"Error converting collection address: {e}")
                collection_hex = STATION_COLLECTION
            
            # Конвертируем wallet адрес - используем user-friendly формат (как во фронтенде)
            try:
                wallet_addr = Address(wallet_address)
                # Используем user-friendly формат (как во фронтенде)
                wallet_formatted = wallet_addr.to_str(is_user_friendly=True, is_bounceable=True)
            except Exception:
                wallet_formatted = wallet_address
            
            # Метод 1: Прямой запрос через HTTP (быстрее)
            try:
                url = f"https://tonapi.io/v2/accounts/{wallet_formatted}/nfts"
                params = {"collection": collection_hex}
                headers = {"Authorization": f"Bearer {API_KEY}"}
                
                response = requests.get(url, params=params, headers=headers, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    nft_items = data.get("nft_items", [])
                    
                    # Найти NFT нужного типа станции
                    for nft_item in nft_items:
                        meta = nft_item.get("metadata", {})
                        name = meta.get("name", "")
                        name_clean = name.split("(")[0].strip()
                        
                        if name_clean in ["Hydroelectric Power Station", "Orbital Power Station"]:
                            continue
                        
                        if name_clean.lower() == expected_name.lower():
                            # Получить адрес NFT и конвертировать в формат 0:hex
                            address_data = nft_item.get("address", {})
                            nft_addr_str = address_data.get("raw") or address_data.get("bounceable") or address_data.get("non_bounceable")
                            
                            if nft_addr_str:
                                try:
                                    nft_addr = Address(nft_addr_str)
                                    return f"0:{nft_addr.hash_part.hex()}"
                                except Exception:
                                    return nft_addr_str
                            return None
            except Exception as e:
                print(f"Direct API request failed: {e}, trying fallback method")
            
            # Метод 2: Fallback - через загрузку коллекции (как в fill_rollback_nft_addresses.py)
            try:
                tonapi = AsyncTonapi(api_key=API_KEY)
                
                async def get_nft_from_collection():
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
                        
                        if len(nfts.nft_items) < limit:
                            break
                        
                        offset += limit
                        time.sleep(0.01)
                    
                    # Найти NFT нужного типа
                    for nft in all_nfts:
                        if nft.owner.address.root == wallet_address:
                            meta = nft.metadata or {}
                            name = meta.get("name", "")
                            name_clean = name.split("(")[0].strip()
                            
                            if name_clean in ["Hydroelectric Power Station", "Orbital Power Station"]:
                                continue
                            
                            if name_clean.lower() == expected_name.lower():
                                # Конвертировать адрес NFT в формат 0:hex
                                try:
                                    nft_addr = Address(nft.address.root)
                                    return f"0:{nft_addr.hash_part.hex()}"
                                except Exception:
                                    return nft.address.root
                    
                    return None
                
                return async_to_sync(get_nft_from_collection)()
            except Exception as e:
                print(f"Fallback method also failed: {e}")
                return None
            
        except Exception as e:
            print(f"Error in get_user_nft_by_station_type_sync: {e}")
            return None
    
    # Ограничение: обрабатывать максимум 50 записей за раз для предотвращения таймаутов
    MAX_BATCH_SIZE = 50
    queryset_list = list(queryset[:MAX_BATCH_SIZE])
    
    if len(queryset) > MAX_BATCH_SIZE:
        modeladmin.message_user(
            request,
            f"⚠️  Выбрано {len(queryset)} записей, но будет обработано только {MAX_BATCH_SIZE} "
            f"для предотвращения таймаутов. Выполните action еще раз для оставшихся записей.",
            messages.WARNING
        )
    
    filled = 0
    not_found = 0
    errors = []
    skipped = 0
    
    for rollback_log in queryset_list:
        # Пропустить если уже есть NFT адрес
        if rollback_log.nft_address:
            skipped += 1
            continue
        
        user = rollback_log.user
        
        if not user.ton_wallet:
            errors.append(
                f"User {user.user_id}: нет TON wallet"
            )
            not_found += 1
            continue
        
        # Проверка LinkedUserNFT для Hydroelectric/Orbital станций
        if rollback_log.from_station in ["Hydroelectric Power Station", "Orbital Power Station"]:
            linked = LinkedUserNFT.objects.filter(
                user=user,
                wallet=user.ton_wallet
            ).first()
            
            if linked:
                rollback_log.nft_address = linked.nft_address
                rollback_log.save(update_fields=['nft_address'])
                filled += 1
                continue
        
        # Получить NFT адрес из TON API
        try:
            # Используем синхронную функцию напрямую (requests уже имеет timeout=5.0)
            nft_address = get_user_nft_by_station_type_sync(
                user.ton_wallet,
                rollback_log.from_station
            )
            
            if nft_address:
                rollback_log.nft_address = nft_address
                rollback_log.save(update_fields=['nft_address'])
                filled += 1
            else:
                errors.append(
                    f"User {user.user_id}: NFT не найден в TON API для станции '{rollback_log.from_station}'"
                )
                not_found += 1
            
            # Rate limiting: небольшая задержка между запросами
            time.sleep(0.05)  # 50ms для более стабильной работы
            
        except Exception as e:
            errors.append(
                f"User {user.user_id}: ошибка при получении NFT - {str(e)[:100]}"
            )
            not_found += 1
    
    # Вывести результаты
    result_messages = []
    if filled > 0:
        result_messages.append(f"✅ Заполнено NFT адресов: {filled}")
    if skipped > 0:
        result_messages.append(f"⏭️  Пропущено (уже есть NFT адрес): {skipped}")
    if not_found > 0:
        result_messages.append(f"⚠️  Не найдено: {not_found}")
    
    if result_messages:
        modeladmin.message_user(
            request,
            "\n".join(result_messages),
            messages.SUCCESS if filled > 0 else messages.WARNING
        )
    
    if errors:
        error_msg = f"❌ Ошибки ({len(errors)}):\n" + "\n".join(errors[:10])
        if len(errors) > 10:
            error_msg += f"\n... и еще {len(errors) - 10} ошибок"
        modeladmin.message_user(
            request,
            error_msg,
            messages.ERROR
        )

fill_nft_addresses_action.short_description = "🔍 Заполнить NFT адреса из TON API (Fill NFT Addresses)"


class StationRollbackLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'from_station',
        'generation_level',
        'storage_level',
        'engineer_level',
        'energy',
        'date',
        'is_restored',
        'restored_at',
        'nft_address',
    )
    list_filter = (
        'from_station',
        'is_restored',
        'date',
    )
    search_fields = (
        'user__user_id',
        'user__username',
        'nft_address',
    )
    readonly_fields = (
        'date',
        'is_restored',
        'restored_at',
    )
    autocomplete_fields = ['user']
    
    # Добавить actions
    actions = [fill_nft_addresses_action, restore_station_action, fill_current_mint_for_restored_action]
    
    fieldsets = (
        ('Информация о пользователе', {
            'fields': ('user',)
        }),
        ('Данные до отката', {
            'fields': (
                'from_station',
                'generation_level',
                'storage_level',
                'engineer_level',
                'energy',
            )
        }),
        ('NFT для восстановления', {
            'fields': ('nft_address',),
            'description': 'Введите адрес NFT станции для восстановления. '
                          'Этот адрес будет использован в StationNFTOwner.'
        }),
        ('Статус восстановления', {
            'fields': (
                'is_restored',
                'restored_at',
                'date',
            ),
            'classes': ('collapse',)
        }),
    )


admin.site.register(StationRollbackLog, StationRollbackLogAdmin)


@admin.register(NFTRentalAgreement)
class NFTRentalAgreementAdmin(admin.ModelAdmin):
    list_display = (
        "nft",
        "name",
        "owner",
        "renter",
        "rentals_days",
        "start_date",
        "end_date",
        "owner_percentage",
    )
    search_fields = ("nft", "owner__user_id", "renter__user_id")
    list_filter = ("owner_percentage", "rentals_days")
    autocomplete_fields = ["owner", "renter"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "notif_type", "is_read", "created_at")
    list_filter = ("notif_type", "is_read")
    search_fields = ("user__user_id", "notif_type")
    autocomplete_fields = ["user"]


@admin.register(NFTRentalConfig)
class NFTRentalConfigAdmin(admin.ModelAdmin):
    pass
    # list_display = ("nft", "rental_price", "rental_period")
    # search_fields = ("nft",)
    # list_filter = ("rental_period",)


from django.contrib import admin

from .models import ChartData


@admin.register(ChartData)
class ChartDataAdmin(admin.ModelAdmin):
    list_display = ("chart_type", "date", "value")
    list_filter = ("chart_type",)
    search_fields = ("chart_type", "date")


from django.template.response import TemplateResponse
@admin.register(GlobalStats)
class GlobalStatsAdmin(admin.ModelAdmin):
    change_list_template = "admin/globalstats_vertical.html"

    def changelist_view(self, request, extra_context=None):
        # In your case, probably only one row of stats exists
        stats = GlobalStats.objects.first()

        context = {
            **self.admin_site.each_context(request),
            "stats": stats,
        }
        return TemplateResponse(request, self.change_list_template, context)


@admin.register(StationUpgradeEvent)
class StationUpgradeEventAdmin(admin.ModelAdmin):
    change_list_template = "admin/station_upgrade_event_vertical.html"

    list_filter = (
        ("upgrade_date", DateTimeRangeFilter),
    )

    def changelist_view(self, request, extra_context=None):
        # 1. Отримуємо стандартний ChangeList
        cl = self.get_changelist_instance(request)

        # 2. Беремо queryset вже з урахуванням усіх фільтрів (у тому числі rangefilter)
        qs = cl.get_queryset(request)

        # 3. Рахуємо статистику
        stats = (
            qs.values("level")
            .annotate(count=Count("id"))
            .order_by("level")
        )

        # 4. Збираємо media
        media = self.media
        for spec in getattr(cl, "filter_specs", []):
            try:
                media = media + spec.field.widget.media
            except AttributeError:
                pass

        # 5. Віддаємо у шаблон
        context = {
            **self.admin_site.each_context(request),
            "stats": stats,
            "title": "Статистика апгрейдів станцій",
            "opts": self.model._meta,
            "cl": cl,
            "media": media,
        }
        return TemplateResponse(request, self.change_list_template, context)

from django.db.models import Sum, F, Value, Count
from django.db.models import Sum, Case, When, FloatField, Count, F, Value
from django.db.models.functions import Concat

@admin.register(UserRewardReport)
class UserRewardReportAdmin(admin.ModelAdmin):
    change_list_template = "admin/userreward_report.html"
    list_filter = (("created_at", DateTimeRangeFilter),)

    def changelist_view(self, request, extra_context=None):
        cl = self.get_changelist_instance(request)
        qs = cl.get_queryset(request)

        # формуємо Parameter name
        SPIN_PRICE = {
    "kW": 499,
    "tBTC": 49,
    "Stars": 249,
}
        
        report_qs = (
    qs.annotate(
        parameter_name=Concat(
            F("asset_type"),
            Value(" "),
            F("asset_quantity"),
            Value(" шт."),
            output_field=django.db.models.CharField()
        )
    )
    .values("parameter_name")
    .annotate(
        spins_count=Count("id"),
        # Spent = кількість спінів * ціна спіна
        spent_kW=Count(
            Case(
                When(paid_with="kW", then=1),
            )
        ) * SPIN_PRICE["kW"],
        spent_tBTC=Count(
            Case(
                When(paid_with="tBTC", then=1),
            )
        ) * SPIN_PRICE["tBTC"],
        spent_Stars=Count(
            Case(
                When(paid_with="Stars", then=1),
            )
        ) * SPIN_PRICE["Stars"],
        # Won = кількість призів (спінів) цього asset_type
        won_kW=Count(
            Case(
                When(paid_with="kW", then=1),
            )
        ),
        won_tBTC=Count(
            Case(
                When(paid_with="tBTC", then=1),
            )
        ),
        won_Stars=Count(
            Case(
                When(paid_with="Stars", then=1),
            )
        ),
    )
    .order_by("parameter_name")
)



        # 4. Збираємо media
        media = self.media
        for spec in getattr(cl, "filter_specs", []):
            try:
                media = media + spec.field.widget.media
            except AttributeError:
                pass

        context = {
            **self.admin_site.each_context(request),
            "cl": cl,
            "report": report_qs,
            "title": "Звіт Колеса Фортуни",
            "opts": self.model._meta,
            "media": media,
        }
        return TemplateResponse(request, self.change_list_template, context)



@admin.register(GlobalSpendStats)
class GlobalSpendStatsAdmin(admin.ModelAdmin):
    list_display = (
        "total_energy_accumulated",
        "energy_spent_build",
        "energy_spent_upgrade",
        "energy_spent_engineer",
        "energy_spent_repair",
        "tbtc_spent_build",
        "tbtc_spent_upgrade",
    )


@admin.register(models.DailyStat)
class DailyStatAdmin(admin.ModelAdmin):
    list_display = ("date", "stat_type", "value")
    list_filter = [
        ("date", DateRangeFilter),
    ]
    ordering = ("-date", "stat_type")


@admin.register(models.MiningStats)
class MiningStatsAdmin(admin.ModelAdmin):
    list_display = (
        "total_tbtc_mined",
        "total_tbtc_claimed",
        "energy_spent_mining",
        "energy_saved_powerbank",
        "energy_saved_magnet",
    )


@admin.register(models.JarvisEnergyStat)
class JarvisEnergyStatAdmin(admin.ModelAdmin):
    list_display = (
        "date",
        "total_jarvis_energy",
        "jarvis_level_1",
        "jarvis_level_2",
        "jarvis_level_3",
        "jarvis_level_4",
        "jarvis_level_5",
    )
    list_filter = [
        ("date", DateRangeFilter),
    ]


@admin.register(models.StationLevelStat)
class StationLevelStatAdmin(admin.ModelAdmin):
    list_display = (
        "count_10_3",
        "count_10_2",
        "count_10_1",
        "count_9_3",
        "count_9_2",
        "count_9_1",
        "count_8_3",
        "count_8_2",
        "count_8_1",
        "count_7_3",
        "count_7_2",
        "count_7_1",
        "count_6_3",
        "count_6_2",
        "count_6_1",
        "count_5_3",
        "count_5_2",
        "count_5_1",
        "count_4_3",
        "count_4_2",
        "count_4_1",
        "count_3_3",
        "count_3_2",
        "count_3_1",
        "count_2_3",
        "count_2_2",
        "count_2_1",
        "count_1_3",
        "count_1_2",
        "count_1_1",
    )


@admin.register(models.SpecialAsicStaking)
class SpecialAsicStakingAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "user__ton_wallet",
        "token_amount",
        "start_date",
        "end_date",
        "days",
        "apr",
        "status",
    )
    list_filter = ("status", "days")
    search_fields = (
        "user__user_id",
        "user__username",
    )
    autocomplete_fields = ["user"]


from import_export.admin import ImportExportModelAdmin
from import_export import resources
from .models import BurnedTBTCBase

class BurnedTBTCBaseResource(resources.ModelResource):
    class Meta:
        model = BurnedTBTCBase

@admin.register(models.BurnedTBTCBase)
class BurnedTBTCBaseAdmin(ImportExportModelAdmin):
    resource_class = BurnedTBTCBaseResource
    list_display = ("wallet", "amount", "upload_date")
    list_filter = [
        ("upload_date", DateTimeRangeFilter),
        ("amount", NumericRangeFilter),
    ]
    search_fields = ("wallet",)
    ordering = ("-upload_date",)


@admin.register(models.UserBurnedTBTC)
class UserBurnedTBTCAdmin(admin.ModelAdmin):
    list_display = ("user", "user__username", "wallet_readable", "amount", "apr", "unlock_date_1", 'unlock_date_2', "unlock_date_3", "unlock_date_4", "unlock_date_5", "unlock_date_6")
    list_filter = [
        ("amount", NumericRangeFilter),
    ]
    search_fields = ("user__user_id", "user__username", "wallet")
    autocomplete_fields = ["user"]

    def wallet_readable(self, obj):
        if not obj.wallet:
            return ""
        return pytoniq_core.Address(obj.wallet).to_str(is_user_friendly=True)
        
@admin.register(models.LinkedUserNFT)
class LinkedUserNFTAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet", "nft_address")
    search_fields = ("user__user_id", "user__username", "wallet", "nft_address")
    autocomplete_fields = ["user"]
    
    def nft_name(self, obj):
        nft = models.NFTDatabase.objects.filter(nft=obj.nft_address).first()
        return nft.name if nft else "-"


@admin.register(models.NFTDatabase)
class NFTDatabaseAdmin(admin.ModelAdmin):
    list_display = ("nft", "hashrate", "name", "mining_speed_tbtc", "consumption_kw")
    search_fields = ("nft", "name")
    list_filter = ("hashrate",)
    
    def has_add_permission(self, request):
        return False
    
@admin.register(models.BufferTransaction)
class BufferTransactionAdmin(admin.ModelAdmin):
    list_display = ("tx_hash", "address", "success")
    search_fields = ("tx_hash", "address")
    list_filter = ("success",)

    
@admin.register(models.GradationConfig)
class GradationConfigAdmin(admin.ModelAdmin):
    list_display = ("name", "gradation_minutes", "gradation_value")
    search_fields = ("name",)
    list_filter = ("name",)
    
@admin.register(models.TimedUserNFT)
class TimedUserNFTAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet", "name", "collection", "nft_address", "block_until")
    search_fields = ("user__user_id", "user__username", "wallet", "name", "collection", "nft_address")
    list_filter = ("collection", "name")
    autocomplete_fields = ["user"]
    

@admin.register(models.WalletInfo)
class WalletInfoAdmin(admin.ModelAdmin):
    list_display = ("user", "wallet", "kw_amount", "tbtc_amount", "tbtc_amount_s21", "tbtc_amount_sx", "block_until")
    search_fields = ("user__user_id", "user__username", "wallet")
    autocomplete_fields = ["user"]


@admin.register(OrbitalOwner)
class OrbitalOwnerAdmin(admin.ModelAdmin):
    list_display = ("user", "nft_address")
    search_fields = ("user__user_id", "user__username", "nft_address")
    autocomplete_fields = ["user"]