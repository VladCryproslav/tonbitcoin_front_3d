# Generated for runner claim idempotency (see docs/RUNNER_ENERGY_CLAIM_ANALYSIS.md)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0126_runnerconfig_run_speed_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='energy_run_claimed_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Время последнего успешного начисления за забег (для идемпотентности claim)',
            ),
        ),
    ]
