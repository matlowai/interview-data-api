from azure.cosmos import CosmosClient
from config_loader import config  # Import the config module

cosmosdb_config = config['cosmos_db']
client = CosmosClient(cosmosdb_config['url'], credential=cosmosdb_config['key_one'])
database = client.get_database_client(cosmosdb_config['database_name'])
container = database.get_container_client(cosmosdb_config['container_name'])
