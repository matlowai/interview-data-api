import os
import random
from faker import Faker
#pip install markovify --index-url "https://art.nwie.net/artifactory/api/pypi/pypi/simple" 
import markovify
import numpy as np
from azure.storage.blob import BlobServiceClient, BlobClient
from config_loader import config

# Initialize Azure Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(config['azure_blob_storage']['connection_string_one'])
container_client = blob_service_client.get_container_client(config['azure_blob_storage']['container_name'])

# Initialize Faker
fake = Faker()

# Directory to store claim notes
os.makedirs('claim_notes', exist_ok=True)

# Sample sentences categorized by incident type
sample_sentences_by_type = {
    "Water Damage": [
        "Significant water leakage in the basement.",
        "Pipe burst in the bathroom, causing floor damage.",
        # ... more sentences for Water Damage
    ],
    "Fire Damage": [
        "Kitchen fire damaged appliances and cabinets.",
        "Electrical fault caused a small fire in the living room.",
        # ... more sentences for Fire Damage
    ],
    # ... additional categories with their sentences
}

# Claim amount ranges by incident type
claim_amount_ranges = {
    "Water Damage": (3000, 20000),
    "Fire Damage": (10000, 50000),
    # ... other categories with their ranges
}

# Create Markov models for each incident type
markov_models = { 
    incident_type: markovify.Text(" ".join(sentences), state_size=1)
    for incident_type, sentences in sample_sentences_by_type.items()
}

# Function to generate a random claim amount, occasionally very high, with normal distribution
def generate_claim_amount(incident_type):
    base_min, base_max = claim_amount_ranges[incident_type]
    mean = (base_max + base_min) / 2
    std_dev = (base_max - base_min) / 4  # Approx. 95% data within [base_min, base_max]

    if random.random() < 0.1:  # 10% chance of an unusually high or low claim
        if random.random() < 0.5:
            # High outlier - significantly above the max
            return round(random.uniform(base_max * 1.5, base_max * 3), 2)
        else:
            # Low outlier - not below 1/3 of the lower bound
            low_outlier_min = base_min / 3
            return round(random.uniform(low_outlier_min, base_min), 2)
    else:
        # Normal distribution within the defined range
        claim_amount = np.random.normal(mean, std_dev)
        # Ensuring claim amount does not fall below the minimum
        return round(max(claim_amount, base_min), 2)


# Function to generate a single claim note, now accepting a policyholder_id
def generate_claim_note(policyholder_id: str):
    print("Claim data generator starting to attempt this")
    category = random.choice(list(sample_sentences_by_type.keys()))
    markov_model = markov_models[category]
    incident_date = fake.date_between(start_date='-2y', end_date='today')
    policyholder_name = fake.name()  # This could be fetched based on the policyholder_id if needed
    detail = markov_model.make_short_sentence(320)
    claim_amount = generate_claim_amount(category)

    claim_note_text = (
        f"{incident_date} - Claim by {policyholder_name}.\n"
        f"Policyholder ID: {policyholder_id}\n"  # Include the policyholder ID in the note
        f"Category: {category}\nDetails: {detail}\n"
        f"Estimated Claim Amount: ${claim_amount}\n"
    )

    # Additional note for high claim amounts
    if claim_amount > claim_amount_ranges[category][1]:
        claim_note_text += "Note: High claim amount - requires additional review.\n"
    print(claim_note_text)
    return claim_note_text

# Update the generate_claim_notes function to pass the policyholder_id
def generate_claim_notes(number_of_notes: int, policyholder_id: str):
    print("Generating claim notes with policyholder_id:", policyholder_id)
    return [generate_claim_note(policyholder_id) for _ in range(number_of_notes)]


# Functions to generate and save multiple claim notes
def generate_and_save_claim_notes_local(n):
    for i in range(n):
        claim_note = generate_claim_note()
        with open(f'claim_notes/claim_note_{i}.txt', 'w') as file:
            file.write(claim_note)

def generate_and_save_claim_notes(n):
    for i in range(n):
        claim_note = generate_claim_note()
        blob_name = f'claim_note_{i}.txt'
        print(blob_name)
        blob_client = container_client.get_blob_client(blob_name)
        print(blob_client)
        blob_client.upload_blob(claim_note, overwrite=True)

def generate_claim_notes(n):
    print("I'm a generate claim notes inside generator.py")
    return [generate_claim_note() for _ in range(n)]