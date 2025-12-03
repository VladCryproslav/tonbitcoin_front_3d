"""
URL configuration for tonbtc project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from rest_framework import permissions


from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path, re_path
from debug_toolbar.toolbar import debug_toolbar_urls

from core.views import GeckoProxyView
from .views import (
    ActivateBoosterFTBCView,
    CheckTaskCompletionView,
    UserTasksView,
    TaskCategoriesView,
    SpinWheelView,
    UserRewardsView,
    WheelSlotsView,
    WheelStarsView,
    ClaimUserRewardView,
    BoosterListView,
    ActivateBoosterView,
)

urlpatterns = [
    path(
        "check_task_completion/",
        CheckTaskCompletionView.as_view(),
        name="check_task_completion",
    ),
    path("user_tasks/", UserTasksView.as_view(), name="user_tasks"),
    path("task_categories/", TaskCategoriesView.as_view(), name="task_categories"),
    path("spin_wheel/", SpinWheelView.as_view(), name="spin_wheel"),
    path("wheel_stars/", WheelStarsView.as_view(), name="wheel_stars"),
    path("user_rewards/", UserRewardsView.as_view(), name="user_rewards"),
    path("claim_user_reward/", ClaimUserRewardView.as_view(), name="claim_user_reward"),
    path("boosters/", BoosterListView.as_view(), name="booster_list"),
    path("activate_booster/", ActivateBoosterView.as_view(), name="activate_booster"),
    path("activate_booster_fbtc/", ActivateBoosterFTBCView.as_view(), name="activate_booster_fbtc"),
    path("wheel_slots/", WheelSlotsView.as_view(), name="wheel_slots"),
]
