from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

def load_config_from_key_vault():
    key_vault_name = "AssignmentVault"
    kv_uri = f"https://{key_vault_name}.vault.azure.net"

    credential = DefaultAzureCredential()
    client = SecretClient(vault_url=kv_uri, credential=credential)

    config = {
        'cosmos_db': {
            'url': "https://matlowai.documents.azure.com:443/",
            'key_one': client.get_secret('assignment-cosmos-key-one').value,  # Adjust the name if needed
            'database_name': "assignment-data",
            'container_name': "policyclaims",
            'key_two': client.get_secret('assignment-cosmos-key-two').value,  # Adjust the name if needed
            'active_key': "key_one"  # or "key_two", decide based on your application logic
        },
        'azure_blob_storage': {
            'connection_string_one': client.get_secret('assignment-blob-connection-string-one').value,
            'connection_string_two': client.get_secret('assignment-blob-connection-string-two').value,
            'container_name': "assignmentclaim", 
            'active_string': "connection_string_one"  # or "connection_string_two", decide based on your application logic
        }
    }
    print(config)
    return config

config = load_config_from_key_vault()
