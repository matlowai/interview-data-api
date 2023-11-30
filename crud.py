from fastapi import HTTPException
from models import Policyholder
from database import container
from typing import List, Optional
from faker import Faker
from logger import logger
import uuid
import random
import os
import markovify
import numpy as np
from claims_data_generator import generate_claim_note

fake = Faker()
# Directory for claim notes
CLAIM_NOTES_DIR = 'claim_notes'
os.makedirs(CLAIM_NOTES_DIR, exist_ok=True)

# Function to generate and add claim notes to Cosmos DB
def generate_and_add_claim_notes_to_db(number_of_notes: int, policyholder_id: str):
    claim_notes = generate_claim_notes(number_of_notes, policyholder_id)
    for note in claim_notes:
        # Create a unique ID for each claim note
        claim_note_id = str(uuid.uuid4())
        claim_note_item = {
            "id": claim_note_id,
            "policyholder_id": policyholder_id,
            "textfile": note,  # Store the note text to cosmos instead because its better for text file data
            # Additional metadata eventually if there is time
        }
        container.upsert_item(claim_note_item)
    print("Claim notes added to Cosmos DB")


def generate_claim_notes(number_of_notes: int, policyholder_id: str):
    return generate_and_add_claim_notes_to_db(number_of_notes, policyholder_id)

def get_all_claims():
    query = "SELECT * FROM c WHERE IS_DEFINED(c.policyholder_id) AND IS_DEFINED(c.analysis)"
    return list(container.query_items(query=query, enable_cross_partition_query=True))

# Function to save a claim note to a file
def save_claim_note_file(claim_note: str, file_name: str):
    file_path = os.path.join(CLAIM_NOTES_DIR, file_name)
    with open(file_path, 'w') as file:
        file.write(claim_note)

# Function to retrieve all claim note files
def get_all_claim_note_files():
    return [file for file in os.listdir(CLAIM_NOTES_DIR) if file.endswith('.txt')]

# Function to retrieve a specific claim note file
def get_claim_note_file_local(file_name: str):
    file_path = os.path.join(CLAIM_NOTES_DIR, file_name)
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.read()
    return None

def get_claim_note_file(file_name: str):
    blob_client = container.get_blob_client(file_name)
    try:
        download_stream = blob_client.download_blob()
        return download_stream.readall().decode("utf-8")
    except Exception as e:
        # Handle exceptions (e.g., Blob not found)
        return None


# Function to analyze claim notes (Placeholder for actual logic)
#def analyze_claim_notes():
    # Placeholder for analysis logic
#    return {"analysis": "Analysis results"}


def generate_policyholder_data():
    return {
        "id": str(uuid.uuid4()),
        "name": fake.name(),
        "age": random.randint(18, 99),
        "policy_start_date": fake.date_between(start_date='-5y', end_date='today').strftime('%Y-%m-%d'),
        "policy_amount": round(random.uniform(90000, 900000), 2)
    }

def add_policyholder_to_db(policyholder_data: dict):
    container.upsert_item(policyholder_data)


def create_policyholder(policyholder: Policyholder):
    created_item = container.upsert_item(policyholder.dict())
    return {
        "message": "Policyholder created",
        "policyholder": created_item
    }

def get_policyholders():
    query = "SELECT * FROM c WHERE NOT IS_DEFINED(c.policyholder_id)"
    ret = list(container.query_items(query=query, enable_cross_partition_query=True))
    logger.info(ret)
    return ret


def get_policyholder(id: str):
    try:
        item = container.read_item(item=id, partition_key=id)
        return item
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Policyholder with id {id} not found")

def update_policyholder(id: str, policyholder_data: dict):
    policyholder_data['id'] = id
    updated_item = container.upsert_item(policyholder_data)
    return {
        "message": "Policyholder updated",
        "policyholder": updated_item
    }

def delete_policyholder(id: str):
    try:
        container.delete_item(id, partition_key=id)
        return {"message": "Policyholder deleted"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Policyholder with id {id} not found")

def search_policyholders(name: str):
    query = "SELECT * FROM c WHERE CONTAINS(LOWER(c.name), LOWER(@name))"
    parameters = [{"name": "@name", "value": name.lower()}]
    ret = list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))
    logger.info(ret)
    return ret

def calculate_average_policy_amount():
    policyholders = get_policyholders()
    if not policyholders:
        return 0
    total = sum(p['policy_amount'] for p in policyholders)
    return total / len(policyholders)

# Fetch claims for specific policyholder IDs
def get_claims_for_policyholders(ids: List[str]):
    query = "SELECT * FROM c WHERE c.policyholder_id IN (@ids)"
    parameters = [{"name": "@ids", "value": ids}]
    return list(container.query_items(query=query, parameters=parameters, enable_cross_partition_query=True))

# Fetch all claims
def get_all_claims():
    query = "SELECT * FROM c WHERE IS_DEFINED(c.policyholder_id)"
    return list(container.query_items(query=query, enable_cross_partition_query=True))

#gets claim by claim id
def get_claim_by_id(claim_id: str):
    try:
        return container.read_item(item=claim_id, partition_key=claim_id)
    except Exception as e:
        return None

def update_claim_with_gptmsg(claim_id: str, gptmsg: str):
    claim = get_claim_by_id(claim_id)
    if claim:
        claim['gptmsg'] = gptmsg
        container.upsert_item(claim)

def delete_claim(claim_id: str):
    try:
        container.delete_item(claim_id, partition_key=claim_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Claim with id {claim_id} not found")

def update_claim_with_file_blob_name(claim_id: str, blob_name: str):
    try:
        #other tenant didn't like blobs but I'm ok in mine it looks like
        claim_item = get_claim_by_id(claim_id)
        if claim_item:
            claim_item['file_blob_name'] = blob_name
            container.upsert_item(claim_item)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating claim {claim_id}")