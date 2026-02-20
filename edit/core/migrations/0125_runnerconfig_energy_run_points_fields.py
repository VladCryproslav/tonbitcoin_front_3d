# Generated manually for energy run points by time

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0124_userprofile_energy_run_start_storage'),
    ]

    operations = [
        migrations.AddField(
            model_name='runnerconfig',
            name='energy_points_per_minute',
            field=models.IntegerField(
                default=2,
                help_text='Базовых поинтов за 1 минуту ожидания (1 ч → 120 при 2)',
            ),
        ),
        migrations.AddField(
            model_name='runnerconfig',
            name='energy_points_reserve_percent',
            field=models.IntegerField(
                default=20,
                help_text='Процент запаса поинтов сверх базового количества',
            ),
        ),
        migrations.AddField(
            model_name='runnerconfig',
            name='energy_run_max_hours',
            field=models.IntegerField(
                default=4,
                help_text='Максимум часов для расчёта поинтов (4 ч × 60 × 2 = 480 поинтов)',
            ),
        ),
    ]
