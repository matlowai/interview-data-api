import uuid
from fastapi import FastAPI, HTTPException, UploadFile, File
from models import AddClaimRequest, Policyholder, PolicyholderRequest, GenerateClaimNotesRequest
from crud import (generate_policyholder_data, add_policyholder_to_db,
                  create_policyholder, get_policyholders, get_policyholder,
                  update_policyholder, delete_policyholder, search_policyholders,
                  calculate_average_policy_amount)
from claims_data_generator import generate_claim_note, generate_claim_notes
from fastapi.middleware.cors import CORSMiddleware
from azure.storage.blob import BlobServiceClient
from config_loader import config
from database import container
import traceback

# Initialize Azure Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(config['azure_blob_storage']['connection_string_one'])
container_client = blob_service_client.get_container_client(config['azure_blob_storage']['container_name'])


app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:8080"],  # Allows requests from your frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.post("/generate-synthetic-policyholders")
async def generate_synthetic_policyholders_data(request: PolicyholderRequest):
    print(request)
    policyholders = [generate_policyholder_data() for _ in range(request.number_of_policyholders)]
    if request.add_to_database:
        for policyholder_data in policyholders:
            add_policyholder_to_db(policyholder_data)
    return policyholders

@app.post("/policyholders")
async def create_policyholder_endpoint(policyholder: Policyholder):
    try:
        return create_policyholder(policyholder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholders")
async def get_policyholders_endpoint():
    try:
        return {"policyholders": get_policyholders()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholders/{id}")
async def get_policyholder_endpoint(id: str):
    try:
        return {"policyholder": get_policyholder(id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/policyholders/{id}")
async def update_policyholder_endpoint(id: str, policyholder: Policyholder):
    try:
        return update_policyholder(id, policyholder.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/policyholders/{id}")
async def delete_policyholder_endpoint(id: str):
    try:
        return delete_policyholder(id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholders/search")
async def search_policyholders_endpoint(name: str):
    try:
        return {"policyholders": search_policyholders(name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholders/average-amount")
async def calculate_average_policy_amount_endpoint():
    try:
        return {"average_amount": calculate_average_policy_amount()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-claim-notes")
async def generate_claim_notes_api(request: GenerateClaimNotesRequest):
    try:
        uploaded_notes = []
        for policyholder_id in request.policyholder_ids:
            claim_notes = generate_claim_notes(request.number_of_notes, policyholder_id)
            for note in claim_notes:
                claim_note_data = {
                    "id": str(uuid.uuid4()),
                    "policyholder_id": policyholder_id,
                    "textfile": note,
                }
                container.upsert_item(claim_note_data)
                uploaded_notes.append({"policyholder_id": policyholder_id, "claim_note": claim_note_data})

        return {"message": "Claim notes generated", "uploaded_notes": uploaded_notes}
    except Exception as e:
        traceback_details = traceback.format_exc()
        print(traceback_details)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search-blob-filenames")
async def search_blob_filenames():
    try:
        # Fetch all blobs in the container
        blob_list = container_client.list_blobs()
        # Extract the names of the blobs
        blob_names = [blob.name for blob in blob_list]
        return {"blob_names": blob_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/claim-notes")
async def upload_claim_note(file: UploadFile = File(...)):
    try:
        blob_name = f"claim_note_{file.filename}"
        blob_client = container_client.get_blob_client(blob_name)
        await blob_client.upload_blob(file.file, overwrite=True)
        return {"message": "Claim note uploaded", "blob_name": blob_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/claim-notes")
async def get_claim_notes():
    try:
        blob_list = container_client.list_blobs()
        return {"claim_notes": [blob.name for blob in blob_list]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/claim-notes/{blob_name}")
async def get_claim_note(blob_name: str):
    try:
        blob_client = container_client.get_blob_client(blob_name)
        download_stream = blob_client.download_blob()
        return {"claim_note": download_stream.readall().decode("utf-8")}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Claim note {blob_name} not found")

@app.get("/claim-notes/analyze")
async def analyze_claim_notes():
    # Logic to analyze claim notes, such as aggregating data or extracting insights
    # Placeholder for actual analysis logic
    return {"analysis": "This is a placeholder for claim notes analysis."}

@app.post("/add-claim")
async def add_claim(request: AddClaimRequest):
    try:
        # Extract details from request
        policyholder_id = request.policyholder_id
        details = request.details if not request.generate_random else generate_claim_note(policyholder_id)

        # Generate a claim note
        claim_note_data = {
            "id": str(uuid.uuid4()),
            "policyholder_id": policyholder_id,
            "textfile": details,
        }

        # Add claim note to the database
        created_claim_note = container.upsert_item(claim_note_data)

        # Return the created claim note
        return {"message": "Claim note added", "claim_note": created_claim_note}
    except Exception as e:
        traceback_details = traceback.format_exc()
        print(traceback_details)
        raise HTTPException(status_code=500, detail=str(e))



# Additional endpoints for claim notes...
# ...

@app.get("/")
async def root():
    return {"message": "Insurance Data API Root"}
