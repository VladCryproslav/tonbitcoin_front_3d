from pytoniq_core import Address

from tonutils.client import TonapiClient
from tonutils.nft import CollectionEditable, NFTEditable
from tonutils.nft.content import NFTOffchainContent
from tonutils.wallet import WalletV5R1

# API key for accessing the Tonapi (obtainable from https://tonconsole.com)
API_KEY = "AH35FSWXEP7HOCQAAAAOYJLEKFZJ3KC24F6AO7LIVDG3HX7L45KYUX34C3PHRGN7QQB4LKI"

# Set to True for test network, False for main network
IS_TESTNET = True

# Mnemonic phrase used to connect the wallet
MNEMONIC: list[str] = (
    """panther
fluid
predict
library
protect
excite
since
more
consider
gravity
essay
donor
hour
forest
atom
oval
hand
enrich
avocado
flag
guitar
gain
pepper
lonely""".split()
)

# Address of the owner of the NFT and the NFT collection contract
OWNER_ADDRESS = "0QDVyeMeq4F6_3FX1AGG4KS6HqscNnPfchmTZd2Tgukra04O"
COLLECTION_ADDRESS = "kQAiog3Hy9kkrK0DVV9rtpt5Q8B9NEwfVEzbKTzlZJsqvQ7j"

# Index of the NFT to be minted
NFT_INDEX = 1

# Suffix URI of the NFT metadata
SUFFIX_URI = f"{NFT_INDEX}.json"


async def main() -> None:
    client = TonapiClient(api_key=API_KEY, is_testnet=IS_TESTNET)
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, MNEMONIC)

    nft = NFTEditable(
        index=NFT_INDEX,
        collection_address=Address(COLLECTION_ADDRESS),
    )
    body = CollectionEditable.build_mint_body(
        index=NFT_INDEX,
        owner_address=Address(OWNER_ADDRESS),
        content=NFTOffchainContent(suffix_uri=SUFFIX_URI),
    )

    """ If you deployed the collection using the Modified variant, replace the above code with:
        Replace `CollectionEditable` and `NFTEditable` with their modified versions,
        and use `NFTModifiedOffchainContent` to specify the full `URI` for the NFT metadata.

    Example:

    nft = NFTEditableModified(
        index=NFT_INDEX,
        collection_address=Address(COLLECTION_ADDRESS),
    )
    body = CollectionEditableModified.build_mint_body(
        index=NFT_INDEX,
        owner_address=Address(OWNER_ADDRESS),
        content=NFTModifiedOffchainContent(uri=URI),  # URI example: `https://example.com/nft/0.json`.
    )
    """

    tx_hash = await wallet.transfer(
        destination=COLLECTION_ADDRESS,
        amount=0.02,
        body=body,
    )

    print(
        f"Successfully minted NFT with index {NFT_INDEX}: {nft.address.to_str(is_test_only=True)}"
    )
    print(f"Transaction hash: {tx_hash}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
