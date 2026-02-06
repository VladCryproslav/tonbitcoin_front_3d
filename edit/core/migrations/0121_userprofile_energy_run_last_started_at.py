# Generated manually for energy run cooldown (60 min)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0120_stationrollbacklog_restore_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='energy_run_last_started_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
