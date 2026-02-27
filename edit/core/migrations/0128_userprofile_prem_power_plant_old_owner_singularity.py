# Premium power stations update: prem_power_plant_old_owner + Singularity Reactor (see docs/PREMIUM_POWER_STATIONS_ORBITAL_UPDATE.md)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0127_userprofile_energy_run_claimed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='prem_power_plant_old_owner',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='has_singularity_station',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='singularity_prev_energy',
            field=models.FloatField(default=0),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='singularity_prev_power',
            field=models.FloatField(default=100),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='singularity_prev_station_type',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='singularity_prev_storage_level',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='singularity_prev_generation_level',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='singularity_prev_engineer_level',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
