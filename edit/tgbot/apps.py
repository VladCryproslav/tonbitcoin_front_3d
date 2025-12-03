import traceback
from django.apps import AppConfig
from django.conf import settings
import telebot


class TgbotConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tgbot"

    def ready(self):
        try:
            bot = telebot.TeleBot(settings.BOT_TOKEN)
            webhook_url = settings.WEBHOOK_URL
            # bot.remove_webhook()
            # bot.set_webhook(url=webhook_url)
        except Exception:
            traceback.print_exc()
