from pydantic import BaseModel, Field
from typing import Optional, List

class PolicyholderRequest(BaseModel):
    number_of_policyholders: int
    add_to_database: bool

class GenerateClaimNotesRequest(BaseModel):
    number_of_notes: int
    policyholder_ids: List[str]  # Array of policyholder IDs

class ProcessClaimsRequest(BaseModel):
    claimIds: List[str]

class Policyholder(BaseModel):
    id: str
    name: str
    age: int
    policy_start_date: str
    policy_amount: float

class AddClaimRequest(BaseModel):
    policyholder_id: str
    details: Optional[str] = None  # Making details optional
    generate_random: bool = Field(default=False, description="Flag to indicate if the claim should be randomly generated")

class ClaimIdsRequest(BaseModel):
    claimIds: List[str]
    
class AuthCode(BaseModel):
    code: str