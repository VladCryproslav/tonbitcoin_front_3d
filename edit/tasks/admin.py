from django.contrib import admin
from .models import Task, TaskCategory, UserTask, WheelSlot, UserReward, WheelSlot2


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "condition", "reward_type", "reward_amount")
    list_filter = ("condition", "reward_type")
    search_fields = ("title",)


@admin.register(TaskCategory)
class TaskCategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(UserTask)
class UserTaskAdmin(admin.ModelAdmin):
    list_display = ("profile", "task", "claimed", "completed")
    list_filter = ("claimed", "completed")
    search_fields = ("profile__user__username", "task__title")
    autocomplete_fields = ["profile"]


@admin.register(WheelSlot)
class WheelSlotAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "asset_name",
        "color",
        "asset_quantity",
        "probability_kW",
        "probability_tBTC",
        "probability_stars",
    )
    list_filter = ("color", "asset_name")
    search_fields = ("asset_name",)


@admin.register(WheelSlot2)
class WheelSlot2Admin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "asset_name",
        "color",
        "asset_quantity",
        "probability_kW",
        "probability_tBTC",
        "probability_stars",
    )
    list_filter = ("color", "asset_name")
    search_fields = ("asset_name",)


@admin.register(UserReward)
class UserAssetAdmin(admin.ModelAdmin):
    list_display = (
        "profile",
        "created_at",
        "wallet",
        "asset_type",
        "asset_quantity",
        "status",
        "processing_type",
        "paid_with",
    )
    list_filter = (
        "asset_type",
        "status",
        "processing_type",
        "asset_quantity",
        "paid_with",
    )
    search_fields = ("profile__username", "profile__user_id", "asset_type")
    autocomplete_fields = ["profile"]


from tasks.models import Booster


@admin.register(Booster)
class BoosterAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "order_number")
    search_fields = ("title", "slug")
