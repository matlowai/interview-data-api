from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def load_config_from_key_vault():
    key_vault_name = "AssignmentVault"
    kv_uri = f"https://{key_vault_name}.vault.azure.net"

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_uri, credential=credential)
    #active_key is setup but not being used right now since we aren't production to rotate keys
    config = {
        'cosmos_db': {
            'url': "https://matlowai.documents.azure.com:443/",
            'key_one': client.get_secret('assignment-cosmos-key-one').value,
            'database_name': "assignment-data",
            'container_name': "policyclaims",
            'key_two': client.get_secret('assignment-cosmos-key-two').value,
            'active_key': "key_one"
        },
        'azure_blob_storage': {
            'connection_string_one': client.get_secret('assignment-blob-connection-string-one').value,
            'connection_string_two': client.get_secret('assignment-blob-connection-string-two').value,
            'container_name': "assignmentclaim", 
            'active_string': "connection_string_one"
        },
        'azure_ad': {
            'client_id': client.get_secret('azure-ad-client-id').value,
            'client_secret': client.get_secret('azure-ad-client-secret').value,
            'tenant_id': client.get_secret('azure-ad-tenant-id').value
        }
    }
    return config

config = load_config_from_key_vault()
