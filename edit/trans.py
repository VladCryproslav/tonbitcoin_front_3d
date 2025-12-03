from pytoniq_core import Address, begin_cell

from tonutils.client import TonapiClient
from tonutils.jetton import JettonMaster, JettonWallet
from tonutils.wallet import WalletV5R1

from django.conf import settings


async def send_tbtc(dest: str, amount: int, comment: str) -> None:
    JETTON_MASTER_ADDRESS = "EQBDdyCZeFFRoOmvEPZw3q_xuwGAb4qXgE2_q4WdmiBTnZLu"
    JETTON_DECIMALS = 9
    DESTINATION_ADDRESS = dest
    JETTON_AMOUNT = amount
    COMMENT = comment

    client = TonapiClient(
        api_key="AFC7OVBKMNFMWMQAAAAMQ6FQASZILJAFPGKO5WEMZHUKBP42UCGI5DJ265YWUPH4H7WFNNQ"
    )
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, settings.TBTC_MNEMONICS.split())

    jetton_wallet_address = await JettonMaster.get_wallet_address(
        client=client,
        owner_address=wallet.address.to_str(),
        jetton_master_address=JETTON_MASTER_ADDRESS,
    )

    body = JettonWallet.build_transfer_body(
        recipient_address=Address(DESTINATION_ADDRESS),
        response_address=wallet.address,
        jetton_amount=int(JETTON_AMOUNT * (10**JETTON_DECIMALS)),
        forward_payload=(
            begin_cell()
            .store_uint(0, 32)  # Text comment opcode
            .store_snake_string(COMMENT)
            .end_cell()
        ),
        forward_amount=1,
    )

    tx_hash = await wallet.transfer(
        destination=jetton_wallet_address,
        amount=0.05,
        body=body,
    )

    print(f"Successfully transferred {JETTON_AMOUNT} tbtc!")
    print(f"Transaction hash: {tx_hash}")


async def send_kw(dest: str, amount: int, comment: str) -> None:
    JETTON_MASTER_ADDRESS = "EQBhF8jWase_Cn1dNTTe_3KMWQQzDbVw_lUUkvW5k6s61ikb"
    JETTON_DECIMALS = 9
    DESTINATION_ADDRESS = dest
    JETTON_AMOUNT = amount
    COMMENT = comment

    client = TonapiClient(
        api_key="AFC7OVBKMNFMWMQAAAAMQ6FQASZILJAFPGKO5WEMZHUKBP42UCGI5DJ265YWUPH4H7WFNNQ"
    )
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, settings.KW_MNEMONICS.split())

    jetton_wallet_address = await JettonMaster.get_wallet_address(
        client=client,
        owner_address=wallet.address.to_str(),
        jetton_master_address=JETTON_MASTER_ADDRESS,
    )

    body = JettonWallet.build_transfer_body(
        recipient_address=Address(DESTINATION_ADDRESS),
        response_address=wallet.address,
        jetton_amount=int(JETTON_AMOUNT * (10**JETTON_DECIMALS)),
        forward_payload=(
            begin_cell()
            .store_uint(0, 32)  # Text comment opcode
            .store_snake_string(COMMENT)
            .end_cell()
        ),
        forward_amount=1,
    )

    tx_hash = await wallet.transfer(
        destination=jetton_wallet_address,
        amount=0.05,
        body=body,
    )

    print(f"Successfully transferred {JETTON_AMOUNT} kw!")
    print(f"Transaction hash: {tx_hash}")
