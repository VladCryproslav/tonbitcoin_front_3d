# Generated manually for runner speed settings

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0125_runnerconfig_energy_run_points_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='runnerconfig',
            name='run_base_speed',
            field=models.FloatField(
                default=0.15,
                help_text='Минимальная скорость (старт)',
            ),
        ),
        migrations.AddField(
            model_name='runnerconfig',
            name='run_mid_speed',
            field=models.FloatField(
                default=0.25,
                help_text='Скорость на 60% дистанции',
            ),
        ),
        migrations.AddField(
            model_name='runnerconfig',
            name='run_max_speed',
            field=models.FloatField(
                default=0.32,
                help_text='Максимальная скорость (с 90%)',
            ),
        ),
        migrations.AddField(
            model_name='runnerconfig',
            name='run_first_ramp_end',
            field=models.IntegerField(
                default=60,
                help_text='Процент дистанции, до которого идет первый набор скорости (0% -> 60%)',
            ),
        ),
        migrations.AddField(
            model_name='runnerconfig',
            name='run_second_ramp_end',
            field=models.IntegerField(
                default=90,
                help_text='Процент дистанции, до которого идет второй набор скорости (60% -> 90%)',
            ),
        ),
    ]
