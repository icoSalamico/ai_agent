from whatsapp.meta_cloud import MetaCloudProvider
from whatsapp.zapi import ZApiProvider
from utils.crypto import decrypt_value


def is_encrypted(value: str | None) -> bool:
    return isinstance(value, str) and value.startswith("gAAAAA")


def get_provider(provider_name: str, config: dict):
    provider_name = provider_name.strip().lower()

    if provider_name == "meta":
        return MetaCloudProvider(
            token=config["token"],
            phone_number_id=config["phone_number_id"]
        )

    elif provider_name == "zapi":
        instance_id = config["instance_id"]
        api_token = config["api_token"]

        # ✅ Descriptografa apenas se necessário
        if is_encrypted(instance_id):
            instance_id = decrypt_value(instance_id)
        if is_encrypted(api_token):
            api_token = decrypt_value(api_token)

        if not instance_id or not api_token:
            raise ValueError("❌ Failed to decrypt Z-API credentials in get_provider")

        return ZApiProvider(
            instance_id=instance_id,
            api_token=api_token
        )

    else:
        raise ValueError(f"Unsupported WhatsApp provider: {provider_name!r}")
