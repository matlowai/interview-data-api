from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
import httpx
from config_loader import config  # Import the config module

# Extract Azure AD configuration values
azure_ad_config = config['azure_ad']
client_id = azure_ad_config['client_id']
client_secret = azure_ad_config['client_secret']
tenant_id = azure_ad_config['tenant_id']

# OAuth2 scheme for authorization code flow
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize",
    tokenUrl=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
    refreshUrl=f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
    scopes={
        "openid": "OpenID Connect standard claim",
        "profile": "User profile",
        "email": "User email",
    },
)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    async with httpx.AsyncClient() as client:
        # Exchange token for user information
        response = await client.post(
            "https://graph.microsoft.com/oidc/userinfo",
            headers={"Authorization": f"Bearer {token}"}
        )
        if response.status_code != 200:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        return response.json()

async def exchange_code_for_token(auth_code: str):
    # Define the token endpoint
    token_endpoint = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    params = {
        'client_id': client_id,
        'scope': 'openid profile email',
        'code': auth_code,
        'redirect_uri': 'http://localhost:8080/login',
        'grant_type': 'authorization_code',
        'client_secret': client_secret,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_endpoint, data=params)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=400, detail="Failed to exchange token")
