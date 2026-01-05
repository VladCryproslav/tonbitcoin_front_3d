from django.db import models


# Create your models here.
class TaskCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    ORDER_DEPENDENCIES = [
        (
            "referral_station",
            "Реферали | >= n1 шт. | Станція >= n2 рівня",
        ),
        ("station", "Юзер | Станція >= n1 рівня"),
        ("storage", "Юзер | Станція >= n1 рівня і Storage >= n2 "),
        ("generation", "Юзер | Станція >= n1 рівня і Generation >= n2"),
        ("balance_energizer", "Юзер | Баланс Energizer >= n1"),
        ("balance_kW", "Юзер | Balance ingame wallet kW >= n1"),
        ("balance_tBTC", "Юзер | Balance ingame wallet tBTC >= n1"),
        ("subscribed_channel", "Юзер | Підписка на канал"),
        ("chat_message", "Юзер | Повідомлення в чаті"),
        ("nft_asic", "Юзер | NFT ASIC кількість >= n1"),
        ("roulette", "Юзер | Рулетка"),
    ]

    REWARD_TYPES = [
        ("kW", "kW"),
        ("tBTC", "tBTC"),
    ]

    order_number = models.FloatField()
    icon = models.FileField(upload_to="task_icons/", null=True, blank=True)
    title = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200, blank=True)
    title_ru = models.CharField(max_length=200, blank=True)
    modal_description = models.TextField()
    modal_description_en = models.TextField(blank=True)
    modal_description_ru = models.TextField(blank=True)
    modal_button_text = models.CharField(max_length=100)
    modal_button_text_en = models.CharField(max_length=100, blank=True)
    modal_button_text_ru = models.CharField(max_length=100, blank=True)
    condition = models.CharField(max_length=100, choices=ORDER_DEPENDENCIES)
    reward_type = models.CharField(max_length=10, choices=REWARD_TYPES)
    reward_amount = models.FloatField()
    categories = models.ManyToManyField(TaskCategory, blank=True)

    n1 = models.TextField(default="", blank=True)
    n2 = models.TextField(default="", blank=True)
    n3 = models.TextField(default="", blank=True)

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return f"{self.order_number}. {self.title}"


class UserTask(models.Model):
    profile = models.ForeignKey("core.UserProfile", on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    started = models.BooleanField(default=False)
    claimed = models.BooleanField(default=False)
    claimed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (
            "profile",
            "task",
        )  # Запрещает дублирование заданий у пользователя


class WheelSlot(models.Model):
    COLOR_CHOICES = [
        ("superprize", "Superprize"),
        ("regular", "Regular"),
    ]

    ASSET_CHOICES = [
        ("kW", "kW"),
        ("tBTC", "tBTC"),
        ("ASIC", "ASIC"),
        ("Stars", "Stars"),
        ("Chip", "Chip"),
        ("autostart", "Автостартер"),
        ("azot", "Жидкий азот"),
        ("powerbank", "Павер Банк"),
        ("magnit", "Магніт"),
        ("asic_manager", "Асик Менеджер"),
        ("electrics", "Інженер"),
        ("jarvis", "Джарвіс"),
    ]

    order_number = models.FloatField(default=0)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES)
    asset_name = models.CharField(max_length=50, choices=ASSET_CHOICES)
    asset_image = models.FileField(upload_to="wheel_assets/", null=True, blank=True)
    n_parameter = models.TextField(null=True, blank=True)
    asset_quantity = models.FloatField(null=True, blank=True)
    probability_kW = models.FloatField()
    probability_tBTC = models.FloatField()
    probability_stars = models.FloatField()

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return f"{self.asset_name} ({self.color})"


class WheelSlot2(models.Model):
    COLOR_CHOICES = [
        ("superprize", "Superprize"),
        ("regular", "Regular"),
    ]

    ASSET_CHOICES = [
        ("kW", "kW"),
        ("tBTC", "tBTC"),
        ("ASIC", "ASIC"),
        ("Stars", "Stars"),
        ("Chip", "Chip"),
        ("autostart", "Автостартер"),
        ("azot", "Жидкий азот"),
        ("powerbank", "Павер Банк"),
        ("magnit", "Магніт"),
        ("asic_manager", "Асик Менеджер"),
        ("electrics", "Інженер"),
        ("jarvis", "Джарвіс"),
    ]

    order_number = models.FloatField(default=0)
    color = models.CharField(max_length=20, choices=COLOR_CHOICES)
    asset_name = models.CharField(max_length=50, choices=ASSET_CHOICES)
    asset_image = models.FileField(upload_to="wheel_assets/", null=True, blank=True)
    n_parameter = models.TextField(null=True, blank=True)
    asset_quantity = models.FloatField(null=True, blank=True)
    probability_kW = models.FloatField()
    probability_tBTC = models.FloatField()
    probability_stars = models.FloatField()

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return f"{self.asset_name} ({self.color})"


class UserReward(models.Model):
    ASSET_CHOICES = [
        ("kW", "kW"),
        ("tBTC", "tBTC"),
        ("ASIC", "ASIC"),
        ("Stars", "Stars"),
        ("Chip", "Chip"),
        ("autostart", "Автостартер"),
        ("azot", "Жидкий азот"),
        ("powerbank", "Павер Банк"),
        ("magnit", "Магніт"),
        ("asic_manager", "Асик Менеджер"),
        ("electrics", "Інженер"),
        ("jarvis", "Джарвіс"),
    ]

    STATUS_CHOICES = [
        ("unclaimed", "Неотриманий"),
        ("processing", "В обробці"),
        ("claimed", "Отриманий"),
    ]

    PROCESSING_CHOICES = [
        ("automatic", "Автоматичне"),
        ("manual", "Ручне"),
    ]

    profile = models.ForeignKey("core.UserProfile", on_delete=models.CASCADE)
    slot = models.ForeignKey(WheelSlot, on_delete=models.CASCADE, null=True)
    asset_type = models.CharField(max_length=50, choices=ASSET_CHOICES)
    n_parameter = models.TextField(null=True, blank=True)
    asset_quantity = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="unclaimed"
    )
    processing_type = models.CharField(max_length=20, choices=PROCESSING_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    random_val = models.FloatField(null=True, blank=True)
    paid_with = models.CharField(max_length=50, null=True, blank=True)

    wallet = models.CharField(max_length=250, null=True, blank=True)

    def __str__(self):
        return f"{self.asset_type} ({self.status})"

    class Meta:
        ordering = ["-created_at"]

class UserRewardReport(UserReward):
    class Meta:
        proxy = True
        verbose_name = "UserReward Report"
        verbose_name_plural = "UserReward Reports"

class Booster(models.Model):
    BOOSTER_CHOICES = [
        ("azot", "Жидкий азот | +n1 за каждую активацию"),
        ("jarvis", "J.A.R.V.I.S. Бот | собирает n1% энергии"),
        ("cryo", "Криокамера"),
        ("autostart", "Автостартер"),
        ("powerbank", "PowerBank | доступен раз в n1 часов"),
        ("magnit", "Магнит на счетчик | снижание на n1%"),
        ("asic_manager", "ASIC Менеджер | остановка от 1 до n1 (макс. 3) раз"),
        ("electrics", "Электрики | +n1 инженеров"),
        ("premium_sub", "Премиум подписка"),
        ("repair_kit", "Рем. Комплект | фиксирует Power на n1%"),
    ]

    order_number = models.FloatField()
    slug = models.CharField(max_length=100, choices=BOOSTER_CHOICES)

    title = models.CharField(max_length=200)
    title_ru = models.CharField(max_length=200, blank=True)
    title_en = models.CharField(max_length=200, blank=True)
    icon = models.FileField(upload_to="booster_icons/", null=True, blank=True)
    status1 = models.CharField(blank=True, max_length=100)
    status1_ru = models.CharField(blank=True, max_length=100)
    status1_en = models.CharField(blank=True, max_length=100)
    status2 = models.CharField(blank=True, max_length=100)
    status2_ru = models.CharField(blank=True, max_length=100)
    status2_en = models.CharField(blank=True, max_length=100)
    additional_info1 = models.TextField(blank=True)
    additional_info1_ru = models.TextField(blank=True)
    additional_info1_en = models.TextField(blank=True)
    additional_info2 = models.TextField(blank=True)
    additional_info2_ru = models.TextField(blank=True)
    additional_info2_en = models.TextField(blank=True)

    description = models.TextField(blank=True)
    description_ru = models.TextField(blank=True)
    description_en = models.TextField(blank=True)
    popup = models.TextField(blank=True)
    popup_ru = models.TextField(blank=True)
    popup_en = models.TextField(blank=True)

    price1 = models.IntegerField()
    price2 = models.IntegerField()
    price3 = models.IntegerField()
    price4 = models.IntegerField()
    price5 = models.IntegerField()
    price6 = models.IntegerField()
    price7 = models.IntegerField()
    price8 = models.IntegerField(default=0)
    price9 = models.IntegerField(default=0)
    price10 = models.IntegerField(default=0)
    
    price1_fbtc = models.FloatField(default=0)
    price2_fbtc = models.FloatField(default=0)
    price3_fbtc = models.FloatField(default=0)
    price4_fbtc = models.FloatField(default=0)
    price5_fbtc = models.FloatField(default=0)
    price6_fbtc = models.FloatField(default=0)
    price7_fbtc = models.FloatField(default=0)
    price8_fbtc = models.FloatField(default=0)
    price9_fbtc = models.FloatField(default=0)
    price10_fbtc = models.FloatField(default=0)

    n1 = models.TextField(default="", blank=True)
    n2 = models.TextField(default="", blank=True)
    n3 = models.TextField(default="", blank=True)

    class Meta:
        ordering = ["order_number"]

    def __str__(self):
        return f"{self.order_number}. {self.title}"
