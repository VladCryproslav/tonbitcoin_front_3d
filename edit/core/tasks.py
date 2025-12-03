# from eventlet import monkey_patch

# monkey_patch()
from celery import shared_task
from celery.utils.log import get_task_logger
from pytonapi import AsyncTonapi

from core.models import UserProfile


logger = get_task_logger(__name__)


tonapi = AsyncTonapi(
    api_key="AFC7OVBKMNFMWMQAAAAMQ6FQASZILJAFPGKO5WEMZHUKBP42UCGI5DJ265YWUPH4H7WFNNQ"
)


from django.db.models import F, Value, Case, When, ExpressionWrapper, FloatField, Q
from asgiref.sync import async_to_sync
from core.models import BufferTransaction, UserProfile


async def get_trans():
    return await tonapi.blockchain.get_account_transactions(
        account_id="UQA1yfxD2yVTu_1QMycifyLMOhJoY_BiJBktI_dAeFjYHLid", limit=20
    )


from django.db.models import F


@shared_task
def check_transactions():

    transactions = async_to_sync(get_trans)()
    # return

    # print(transactions.transactions)

    for tx in transactions.transactions:
        try:
            buffer_tx = BufferTransaction.objects.get(tx_hash=tx.hash)
        except BufferTransaction.DoesNotExist:
            logger.info("1")
            # if tx.success:
            logger.info("2")
            if tx.in_msg.decoded_body is None:
                continue
            logger.info("3")
            sender = tx.in_msg.decoded_body.get("sender")
            amount = tx.in_msg.decoded_body.get("amount")
            if sender is None:
                continue
            logger.info("4", sender, amount)
            logger.info(tx)
            user = UserProfile.objects.filter(kw_address=sender).first()
            if user is None:
                continue
            logger.info("5")
            BufferTransaction.objects.create(tx_hash=tx.hash, address=sender)
            UserProfile.objects.filter(kw_address=sender).update(
                kw_wallet=F("kw_wallet") + float(amount)
            )


@shared_task
def generate_energy_task():
    for user in UserProfile.objects.all():
        actual_generation_rate = user.generation_rate * (user.power / 100) / 60
        user.storage += actual_generation_rate
        if user.storage > user.storage_limit:
            user.storage = user.storage_limit
        user.save()
    # logger.info("start")
    # transactions = asyncio.run(
    #     tonapi.blockchain.get_account_transactions(
    #         account_id="UQAQuUdtMQXeUeAHuxNHtQjsn-7ntLLgYAylKESmEoWNWitg", limit=3
    #     )
    # )
    # logger.info("end")
    # logger.info(transactions.transactions[0].success)


# @shared_task
# def sample_task():
#     logger.info("The sample task just ran.")
