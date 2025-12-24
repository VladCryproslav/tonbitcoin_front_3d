# Generated manually for station rollback restore functionality

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0117_userprofile_hydro_prev_power'),
    ]

    operations = [
        migrations.AddField(
            model_name='stationrollbacklog',
            name='nft_address',
            field=models.CharField(
                blank=True,
                help_text='Адрес NFT станции для восстановления',
                max_length=255,
                null=True,
                verbose_name='NFT Address'
            ),
        ),
        migrations.AddField(
            model_name='stationrollbacklog',
            name='is_restored',
            field=models.BooleanField(
                default=False,
                help_text='Была ли станция восстановлена',
                verbose_name='Восстановлено'
            ),
        ),
        migrations.AddField(
            model_name='stationrollbacklog',
            name='restored_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Дата и время восстановления станции',
                null=True,
                verbose_name='Дата восстановления'
            ),
        ),
    ]

