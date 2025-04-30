from whatsapp.meta_cloud import MetaCloudProvider
from whatsapp.zapi import ZApiProvider

def get_provider(provider_name: str, config: dict):
    if provider_name == "meta":
        return MetaCloudProvider(token=config["token"], phone_number_id=config["phone_number_id"])
    elif provider_name == "zapi":
        return ZApiProvider(instance_id=config["instance_id"], api_token=config["api_token"])
    else:
        raise ValueError("Unsupported WhatsApp provider")
