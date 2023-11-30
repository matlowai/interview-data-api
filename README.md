For local language model implementation I used:
https://github.com/oobabooga/
https://huggingface.co/TheBloke/Capybara-Tess-Yi-34B-200K-GPTQ
8k context length is recommended, 200k context is max but exceeds 24GB card. default import settings are good

I also experimented with this but it would have needed additional tuning to make work
https://huggingface.co/TheBloke/openinstruct-mistral-7B-GPTQ/

# dylan-insurance-data-api
Interview python api

run this to make sure you have these libraries just 

pip install pandas azure-cosmos python-multipart fastapi uvicorn markovify faker pyyaml azure-storage-blob azure-storage-blob azure-identity azure-keyvault-secrets azure-appconfiguration httpx fastapi-security --index-url "https://art.nwie.net/artifactory/api/pypi/pypi/simple"

only use art if on nw network

Note for security keys to resolve:
check if azure cli is installed with az --version
az login with the test account.  Credentials are already setup and role assigned.


uvicorn main:app --reload --port 8001

For docker setup to run in a container on the cloud (currently running just it is http):

Note while the Vue application can connect from localhost http to cloud http for FastAPI outside of nationwide, within nationwide http is blocked so both will need to run locally.

docker build -t assignment-fastapi-app .
az acr create --resource-group Assignment --name matlowaiassignmentregistry --sku Basic
az acr login --name matlowaiassignmentregistry
docker tag assignment-fastapi-app matlowaiassignmentregistry.azurecr.io/assignment-fastapi-app:v1
docker push matlowaiassignmentregistry.azurecr.io/assignment-fastapi-app:v1

az ad sp create-for-rbac --name matlowaiassignmentprincipal --skip-assignment


cmd terminal use this
az container create \
  --resource-group Assignment \
  --name assignment-fastapi-app \
  --image matlowaiassignmentregistry.azurecr.io/assignment-fastapi-app:v1 \
  --cpu 1 --memory 1 \
  --registry-login-server matlowaiassignmentregistry.azurecr.io \
  --registry-username <acr-username> \
  --registry-password <acr-password> \
  --dns-name-label matlowaiassignmentfastapiapp-dns-name \
  --ports 8001

powershell use this
az container create `
  --resource-group Assignment `
  --name assignment-fastapi-app `
  --image matlowaiassignmentregistry.azurecr.io/assignment-fastapi-app:v1 `
  --cpu 1 --memory 1 `
  --registry-login-server matlowaiassignmentregistry.azurecr.io `
  --registry-username matlowaiassignmentregistry `
  --registry-password [Your_ACR_Password] `
  --dns-name-label matlowaiassignmentfastapiapp-dns-name `
  --ports 8001 `
  --environment-variables 'AZURE_CLIENT_ID=[Your_Service_Principal_AppId]' 'AZURE_CLIENT_SECRET=[Your_Service_Principal_Password]' 'AZURE_TENANT_ID=[Your_Tenant_ID]'

note to retrieve username and pwd:
az acr update -n matlowaiassignmentregistry --admin-enabled true
az acr credential show --name matlowaiassignmentregistry --resource-group Assignment

well it crashed so lets see what happened
az container logs --resource-group Assignment --name assignment-fastapi-app

it was missing access
