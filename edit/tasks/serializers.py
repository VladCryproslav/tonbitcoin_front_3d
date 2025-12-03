from core.models import UserStaking
from .models import UserReward, UserTask, Task, TaskCategory, Booster, WheelSlot
from rest_framework import serializers


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


class UserTaskSerializer(serializers.ModelSerializer):
    task = TaskSerializer()

    class Meta:
        model = UserTask
        fields = ["id", "task", "completed", "claimed", "claimed_at"]


class TaskCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskCategory
        fields = ["id", "name"]


class UserRewardSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserReward
        exclude = ["random_val"]


class BoosterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booster
        fields = "__all__"


class WheelSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = WheelSlot
        exclude = ["probability_kW", "probability_tBTC", "probability_stars"]


class UserStakingSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStaking
        fields = "__all__"
