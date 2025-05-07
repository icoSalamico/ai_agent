from whatsapp.meta_cloud import MetaCloudProvider
from whatsapp.zapi import ZApiProvider
from utils.crypto import decrypt_value

def get_provider(provider_name: str, config: dict):
    provider_name = provider_name.strip().lower()

    if provider_name == "meta":
        return MetaCloudProvider(
            token=config["token"],
            phone_number_id=config["phone_number_id"]
        )

    elif provider_name == "zapi":
        decrypted_instance_id = decrypt_value(config["instance_id"])
        decrypted_api_token = decrypt_value(config["api_token"])

        if not decrypted_instance_id or not decrypted_api_token:
            raise ValueError("❌ Failed to decrypt Z-API credentials in get_provider")

        return ZApiProvider(
            instance_id=decrypted_instance_id,
            api_token=decrypted_api_token  # já descriptografado aqui
        )

    else:
        raise ValueError(f"Unsupported WhatsApp provider: {provider_name!r}")
