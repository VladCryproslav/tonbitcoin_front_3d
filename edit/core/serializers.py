from rest_framework import serializers

from .models import (
    ChartData,
    EngineerConfig,
    HashrateInfo,
    NFTRentalConfig,
    NFTStation,
    RoadmapItem,
    SpecialAsicStaking,
    StakingPeriodConfig,
    StationRollbackLog,
    TimedUserNFT,
    WalletInfo,
    UserActionLog,
    UserBurnedTBTC,
    UserStaking,
    WithdrawalConfig,
    GradationConfig
)


class RoadmapItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoadmapItem
        fields = ["id", "title", "status", "order", "item_date", "title_en", "title_ru"]


from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    last_withdrawal_date = serializers.SerializerMethodField()
    last_withdrawal_date_tbtc = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        exclude = [
            "stop_mining_at1",
            "stop_mining_at2",
            "stop_mining_at3",
            "stop_mining_next",
            "wheel_slot2",
        ]

    def get_last_withdrawal_date(self, obj):
        last_request_kw = (
            WithdrawalRequest.objects.filter(
                user=obj,
                token_contract_address="EQDSYiFUtMVS9rhBDhbTfP-zbj_uqa69bHv6e5IberQH5n1N",
            )
            .order_by("-claimed_at")
            .first()
        )
        return last_request_kw.claimed_at if last_request_kw else None

    def get_last_withdrawal_date_tbtc(self, obj):
        last_request_tbtc = (
            WithdrawalRequest.objects.filter(
                user=obj,
                token_contract_address="EQBDdyCZeFFRoOmvEPZw3q_xuwGAb4qXgE2_q4WdmiBTnZLu",
            )
            .order_by("-claimed_at")
            .first()
        )
        return last_request_tbtc.claimed_at if last_request_tbtc else None


from .models import (
    GenPowerStationConfig,
    RepairPowerStationConfig,
    StoragePowerStationConfig,
)


class GenPowerStationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GenPowerStationConfig
        fields = "__all__"


class StoragePowerStationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StoragePowerStationConfig
        fields = "__all__"


class RepairPowerStationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = RepairPowerStationConfig
        fields = "__all__"


from .models import WithdrawalRequest


class WithdrawalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalRequest
        fields = "__all__"


class EngineerConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EngineerConfig
        fields = "__all__"


class WithdrawConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = WithdrawalConfig
        fields = "__all__"


class NFTRentalConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = NFTRentalConfig
        fields = "__all__"


class StakingPeriodConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = StakingPeriodConfig
        fields = "__all__"


class HashrateInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = HashrateInfo
        fields = "__all__"


class UserActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActionLog
        fields = "__all__"


class StationRollbackLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationRollbackLog
        fields = "__all__"


class NFTStationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NFTStation
        fields = "__all__"


from .models import Notification  # Import the Notification model


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "notif_type", "is_read", "user"]


from .models import NFTRentalAgreement


class NFTRentalAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = NFTRentalAgreement
        fields = [
            "id",
            "nft",
            "hashrate",
            "rentals_days",
            "start_date",
            "end_date",
            "owner_percentage",
            "platform_fee",
            "mining_speed_tbtc",
        ]


class ChartDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChartData
        fields = ["chart_type", "filter_type", "date", "value"]


class SpecialAsicStakingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialAsicStaking
        fields = "__all__"

class UserBurnedTBTCSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserBurnedTBTC
        fields = "__all__"
        
class TimedUserNFTSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimedUserNFT
        fields = "__all__"
        
class WalletInfoSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        model = WalletInfo

class GradationConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = GradationConfig
        fields = "__all__"