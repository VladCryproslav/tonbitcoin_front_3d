# Generated manually for energy run storage validation

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0123_engineerconfig_saved_percent_on_lose'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='energy_run_start_storage',
            field=models.DecimalField(
                blank=True,
                decimal_places=16,
                default=0,
                help_text='Storage при старте забега (для валидации)',
                max_digits=36,
                null=True,
            ),
        ),
    ]
