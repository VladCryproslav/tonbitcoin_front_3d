from django.utils import timezone
import threading
import time
from .models import ChartData
from django.db import transaction
from django.db.models import Sum, F

def add_chart_kw(value: float):
    today = timezone.now().date()
    with transaction.atomic():
        if ChartData.objects.filter(date=today, chart_type="kw_mined").first():
            ChartData.objects.filter(date=today, chart_type="kw_mined").update(value=F("value") + value)
        else:
            ChartData.objects.create(date=today, chart_type="kw_mined", value=value)
            
