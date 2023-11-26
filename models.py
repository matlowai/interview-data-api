from pydantic import BaseModel, Field
from typing import Optional

class PolicyholderRequest(BaseModel):
    number_of_policyholders: int
    add_to_database: bool

class GenerateClaimNotesRequest(BaseModel):
    number_of_notes: int
    policyholder_id: str  # New field to link claim notes with a policyholder

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
