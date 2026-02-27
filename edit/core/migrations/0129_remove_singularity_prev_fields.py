# Singularity uses hydro_prev_* like hydro/orbital (see docs/PREMIUM_POWER_STATIONS_ORBITAL_UPDATE.md)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0128_userprofile_prem_power_plant_old_owner_singularity'),
    ]

    operations = [
        migrations.RemoveField(model_name='userprofile', name='singularity_prev_energy'),
        migrations.RemoveField(model_name='userprofile', name='singularity_prev_power'),
        migrations.RemoveField(model_name='userprofile', name='singularity_prev_station_type'),
        migrations.RemoveField(model_name='userprofile', name='singularity_prev_storage_level'),
        migrations.RemoveField(model_name='userprofile', name='singularity_prev_generation_level'),
        migrations.RemoveField(model_name='userprofile', name='singularity_prev_engineer_level'),
    ]
