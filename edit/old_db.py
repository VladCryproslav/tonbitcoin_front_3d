import os
import csv
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tonbtc.settings")
django.setup()

from core.models import UserProfile

from tonsdk.utils import Address
import pytoniq_core


def export_csv_tg_id_wallet(csv_path):
    """
    Exports TG ID and wallet address from the database into a CSV file.
    Each row will contain two columns: tg_id,wallet_address
    """
    user_profiles = UserProfile.objects.all()

    with open(csv_path, mode="w", encoding="utf-8", newline="") as csvfile:
        writer = csv.writer(csvfile)
        # Optionally, write a header
        writer.writerow(["tg_id", "id", "wallet_address"])

        for user_profile in user_profiles:
            tg_id = user_profile.user_id
            wallet_address = user_profile.ton_wallet or ""
            wallet_address = (
                pytoniq_core.Address(wallet_address).to_str(is_user_friendly=True)
                if wallet_address
                else ""
            )

            writer.writerow([tg_id, user_profile.pk, wallet_address])

    print(f"Exported {user_profiles.count()} records to {csv_path}")


export_csv_tg_id_wallet("tg_id_wallet.csv")
