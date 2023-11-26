from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from faker import Faker
import random
from datetime import datetime
from database import container  # Import the Cosmos DB container client
from config_loader import config  # Import the configuration
import uuid

from claims_data_generator import generate_claim_notes

# Initialize FastAPI app
app = FastAPI()

# Initialize Faker
fake = Faker()

class PolicyholderRequest(BaseModel):
    number_of_policyholders: int
    add_to_database: bool

class GenerateClaimNotesRequest(BaseModel):
    number_of_notes: int

# Policyholder Pydantic Model
class Policyholder(BaseModel):
    id: str
    name: str
    age: int
    policy_start_date: str
    policy_amount: float

# Function to generate a single policyholder's data using uuid import instead of faker due to slighly better algo
def generate_policyholder():
    return {
        "id": uuid.uuid4(),
        "name": fake.name(),
        "age": random.randint(18, 99),
        "policy_start_date": fake.date_between(start_date='-5y', end_date='today').strftime('%Y-%m-%d'),
        "policy_amount": round(random.uniform(90000, 900000), 2)
    }

# Endpoint to generate synthetic policyholder data
@app.post("/generate-synthetic-policyholders")
async def generate_synthetic_policyholders_data(request: PolicyholderRequest):
    policyholders = [generate_policyholder() for _ in range(request.number_of_policyholders)]
    #if add_to_database is true we will do that
    print(request.add_to_database)
    if request.add_to_database:
        print("Adding to database")
        for policyholder in policyholders:
            # Convert to a dict and add/modify necessary fields for Cosmos DB
            policyholder_dict = policyholder
            policyholder_dict['id'] = str(policyholder_dict['id'])  # Ensure 'id' is a string
            # Add more modifications if necessary
            container.upsert_item(policyholder_dict)

    return policyholders

# Endpoint for generating claim notes
@app.post("/generate-claim-notes")
async def generate_claim_notes_api(request: GenerateClaimNotesRequest):
    return generate_claim_notes(request.number_of_notes)

# CRUD Endpoints for Policyholders
@app.post("/policyholders")
async def create_policyholder(policyholder: Policyholder):
    # Logic to add policyholder to DB
    return {"message": "Policyholder created"}

@app.get("/policyholders")
async def get_policyholders():
    # Logic to get all policyholders
    return {"policyholders": []}

@app.get("/policyholders/{id}")
async def get_policyholder(id: str):
    # Logic to get a specific policyholder
    return {"policyholder": {}}

@app.put("/policyholders/{id}")
async def update_policyholder(id: str, policyholder: Policyholder):
    # Logic to update policyholder details
    return {"message": "Policyholder updated"}

@app.delete("/policyholders/{id}")
async def delete_policyholder(id: str):
    # Logic to delete a policyholder
    return {"message": "Policyholder deleted"}

# Endpoint for Searching Policyholders by Name
@app.get("/policyholders/search")
async def search_policyholders(name: str):
    # Logic to search policyholders by name
    return {"policyholders": []}

# Endpoint for Calculating Average Policy Amount
@app.get("/policyholders/average-amount")
async def calculate_average_policy_amount():
    # Logic to calculate average policy amount
    return {"average_amount": 0}

# Endpoint for Uploading Claim Notes
@app.post("/claim-notes")
async def upload_claim_note(file: UploadFile = File(...)):
    # Logic to upload claim note file and update DB
    return {"message": "Claim note uploaded"}

# Endpoint for Retrieving Claim Notes
@app.get("/claim-notes")
async def get_claim_notes():
    # Logic to retrieve all claim notes
    return {"claim_notes": []}

@app.get("/claim-notes/{id}")
async def get_claim_note(id: str):
    # Logic to retrieve a specific claim note
    return {"claim_note": {}}

# Endpoint for Analyzing Claim Notes
@app.get("/claim-notes/analyze")
async def analyze_claim_notes():
    # Logic to analyze claim notes
    return {"analysis": {}}

# Root Endpoint
@app.get("/")
async def root():
    return {"message": "Insurance Data API Root"}
