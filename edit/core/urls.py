from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views
from .views import AccelerateRentBlockView, SwitchOrbitalView, TimedUserNFTView, UserBurnedTBTCView  # Import the new view
from .views import AddTonWalletView  # Import the new view
from .views import AvailableNFTRentalsView  # Import the new view
from .views import BufferTransactionView  # Import the new view
from .views import CreateUserStakingView  # Import the new view
from .views import DeleteTonWalletView  # Import the new view
from .views import EnableStationView  # Import the new view
from .views import GetKwReferralBonusesView  # Import the new view
from .views import LastWithdrawalDateView  # Import the new view
from .views import MarkNotificationAsReadView  # Import the new view
from .views import PowerStationConfigView  # Import the new view
from .views import RentNFTView  # Import the new view
from .views import RepairPowerStationConfigView  # Import the new view
from .views import ReturnNFTRentalView  # Import the new view
from .views import UpgradeEngineerView  # Import the new view
from .views import UpgradeGenerationView  # Import the new view
from .views import UpgradeStationView  # Import the new view
from .views import UpgradeStorageView  # Import the new view
from .views import UserNotificationsView  # Import the new view
from .views import UserRentedNFTsView  # Import the new view
from .views import UserTapInfoView2  # Import the new view
from .views import (
    AddKwToWalletView,
    AddTbtcToWalletView,
    CreateWithdrawalRequestView,
    EnergyRunStartView,
    EngineerConfigView,
    EngineerStarsView,
    GameRunCompleteView,
    GameRunClaimView,
    GameRunResetOverheatFlagView,
    GameRunUpdateOverheatView,
    GenPowerStationConfigView,
    GetTbtcReferralBonusesView,
    ReferralInfoView,
    RepairStationView,
    RoadmapItemViewSet,
    SpecificAsicsView,
    StakingPeriodConfigView,
    StartMiningView,
    StopMiningView,
    StoragePowerStationConfigView,
    TapEnergyView,
    UserProfileView,
    UserStakingsView,
    UserTapInfoView,
)

router = DefaultRouter()
router.register(r"roadmap-items", RoadmapItemViewSet)

from django.http import JsonResponse

def health(request):
    return JsonResponse({"ok": True})

urlpatterns = [
    path("", include(router.urls)),
    path("tap-energy/", TapEnergyView.as_view(), name="tap_energy"),
    path(
        "gen-power-station-configs/",
        GenPowerStationConfigView.as_view(),
        name="power-station-configs",
    ),
    path(
        "storage-power-station-configs/",
        StoragePowerStationConfigView.as_view(),
        name="storage-station-configs",
    ),
    path(
        "repair-power-station-configs/",
        RepairPowerStationConfigView.as_view(),
        name="get_repair_cost",
    ),  # New endpoint
    path(
        "eng-configs/",
        EngineerConfigView.as_view(),
        name="get_repair_cost",
    ),  # New endpoint
    path("repair-station/", RepairStationView.as_view(), name="repair_station"),
    path(
        "create-withdrawal-request/",
        CreateWithdrawalRequestView.as_view(),
        name="create_withdrawal_request",
    ),
    path("user-profile/", UserProfileView.as_view(), name="user_profile"),
    path("referral-info/", ReferralInfoView.as_view(), name="referral_info"),
    path("start-mining/", StartMiningView.as_view(), name="start_mining"),
    path("stop-mining/", StopMiningView.as_view(), name="stop_mining"),
    path("energy-run-start/", EnergyRunStartView.as_view(), name="energy_run_start"),
    path("game-run-complete/", GameRunCompleteView.as_view(), name="game_run_complete"),
    path("game-run-claim/", GameRunClaimView.as_view(), name="game_run_claim"),
    path("game-run-update-overheat/", GameRunUpdateOverheatView.as_view(), name="game-run-update-overheat"),
    path("game-run-reset-overheat-flag/", GameRunResetOverheatFlagView.as_view(), name="game-run-reset-overheat-flag"),
    path("add-kw-to-wallet/", AddKwToWalletView.as_view(), name="add_kw_to_wallet"),
    path(
        "add-tbtc-to-wallet/", AddTbtcToWalletView.as_view(), name="add_tbtc_to_wallet"
    ),
    path(
        "add-ton-wallet/", AddTonWalletView.as_view(), name="add_ton_wallet"
    ),  # New endpoint
    path(
        "delete-ton-wallet/", DeleteTonWalletView.as_view(), name="delete_ton_wallet"
    ),  # New endpoint
    path(
        "upgrade-storage/", UpgradeStorageView.as_view(), name="upgrade_storage"
    ),  # New endpoint
    path(
        "upgrade-generation/",
        UpgradeGenerationView.as_view(),
        name="upgrade_generation",
    ),  # New endpoint
    path(
        "upgrade-station/", UpgradeStationView.as_view(), name="upgrade_station"
    ),  # New endpoint
    path(
        "upgrade-engineer/", UpgradeEngineerView.as_view(), name="upgrade_engineer"
    ),  # New endpoint
    path(
        "power-station-configs/",
        PowerStationConfigView.as_view(),
        name="power_station_configs",
    ),  # New endpoint
    path(
        "buffer-transaction/<str:tx_hash>/",
        BufferTransactionView.as_view(),
        name="buffer_transaction",
    ),  # New endpoint
    path(
        "last-withdrawal-date/",
        LastWithdrawalDateView.as_view(),
        name="last_withdrawal_date",
    ),  # New endpoint
    path(
        "get-kw-referral-bonuses/",
        GetKwReferralBonusesView.as_view(),
        name="get_kw_referral_bonuses",
    ),
    path(
        "get-tbtc-referral-bonuses/",
        GetTbtcReferralBonusesView.as_view(),
        name="get_tbtc_referral_bonuses",
    ),
    path(
        "get-staking-referral-bonuses/",
        views.GetStakingReferralBonusesView.as_view(),
        name="get_tbtc_referral_bonuses",
    ),
    path("user-info/", UserTapInfoView.as_view(), name="user_tap_info"),
    path("user-info-2/", UserTapInfoView2.as_view(), name="user_tap_info"),
    path(
        "enable-station/", EnableStationView.as_view(), name="enable_station"
    ),  # New endpoint
    path("stars-engineer/", EngineerStarsView.as_view(), name="engineer_config"),
    path("tasks/", include("tasks.urls")),
    path("staking-configs/", StakingPeriodConfigView.as_view(), name="staking_configs"),
    path(
        "create-user-staking/",
        CreateUserStakingView.as_view(),
        name="create_user_staking",
    ),  # New endpoint
    path("user-stakings/", UserStakingsView.as_view(), name="user_stakings"),
    path(
        "earn-deposit/",
        views.EarnDepositView.as_view(),
        name="earn_deposit",
    ),
    path(
        "reconnect-mining/",
        views.ReconnectMiningView.as_view(),
        name="reconnect_mining",
    ),
    path(
        "hashrate-info/",
        views.HashrateInfoView.as_view(),
        name="hashrate_info",
    ),
    path(
        "speed-build-stars/",
        views.SpeedBuildStarsView.as_view(),
        name="speed_build_stars",
    ),
    path(
        "mint-station/",
        views.MintStationView.as_view(),
        name="mint-station",
    ),
    path(
        "rollback-station/",
        views.RollbackStationView.as_view(),
        name="rollback-station",
    ),
    path(
        "nft-rental/",
        views.NFTRentalView.as_view(),
        name="nft_rental",
    ),
    path(
        "notifications/", UserNotificationsView.as_view(), name="user-notifications"
    ),  # New endpoint
    path(
        "notifications/mark-read/",
        MarkNotificationAsReadView.as_view(),
        name="mark-notification-as-read",
    ),  # New endpoint
    path(
        "available-nft-rentals/",
        AvailableNFTRentalsView.as_view(),
        name="available_nft_rentals",
    ),  # New endpoint
    path(
        "user-rented-nfts/",
        UserRentedNFTsView.as_view(),
        name="user_rented_nfts",
    ),  # New endpoint
    path(
        "return-nft-rental/",
        ReturnNFTRentalView.as_view(),
        name="return_nft_rental",
    ),  # New endpoint
    path(
        "cancel-nft-rental/",
        views.CancelNFTRentalView.as_view(),
        name="cancel_nft_rental",
    ),
    path(
        "accelerate-rent-block/",
        AccelerateRentBlockView.as_view(),
        name="accelerate_rent_block",
    ),  # New endpoint
    path("rent-nft/", RentNFTView.as_view(), name="rent_nft"),  # New endpoint
    path("user-lent-nfts/", views.UserLentNFTsView.as_view(), name="user_lent_nfts"),
    path(
        "all-charts-dashboard/",
        views.AllChartsView.as_view(),
        name="all_charts_dashboard",
    ),
    path("gecko/<path:path>/", views.GeckoProxyView.as_view(), name="gecko-proxy"),
    path("dashboard-info/", views.DashboardInfoView.as_view(), name="dashboard_info"),
    path("special-asics/", SpecificAsicsView.as_view(), name="special-asics-list"),
    path("user-burned-tbtc/", UserBurnedTBTCView.as_view(), name="user-burned-tbtc"),
    path("user-timed-nfts/", TimedUserNFTView.as_view(), name="user-timed-nfts"),
    path("timed-nft-stars/", views.TimedNFTStarsView.as_view(), name="timed-nft-stars"),
    path("user-wallet-info/", views.CurrentWalletInfoView.as_view(), name="user_wallet_info"),
    path("user-wallet-info-stars/", views.CurrentWalletInfoStarsView.as_view(), name="user_wallet_info_stars"),
    path("switch-orbital/", SwitchOrbitalView.as_view(), name="switch_orbital"),
    path("craft-nft/", views.CraftNFTView.as_view(), name="craft_nft"),
    path("switch-orbital-station/", views.SwitchOrbitalStationView.as_view(), name="switch_orbital_station"),
    # path("health/", health, name="test_endpoint"),
]
