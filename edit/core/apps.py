from django.apps import AppConfig
import threading


class CoreConfig(AppConfig):
    name = "core"

    # def ready(self):
    # from .utils import generate_energy
    #     threading.Thread(target=generate_energy, daemon=True).start()
