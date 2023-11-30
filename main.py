# main.py
import json
import uuid
import traceback
import io
from typing import List, Optional
from fastapi import Body, FastAPI, HTTPException, UploadFile, File, Query, Form, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from azure.storage.blob import BlobServiceClient
import httpx
from analysis import analyze_claims
from logger import logger
from models import (
    AddClaimRequest, AuthCode, ClaimIdsRequest, Policyholder, PolicyholderRequest, 
    GenerateClaimNotesRequest, ProcessClaimsRequest
)
from crud import (
    delete_claim, generate_policyholder_data, add_policyholder_to_db,
    create_policyholder, get_claim_by_id, get_policyholders, get_policyholder,
    update_claim_with_file_blob_name, update_claim_with_gptmsg,
    update_policyholder, delete_policyholder, search_policyholders,
    calculate_average_policy_amount, generate_claim_notes,
    get_claims_for_policyholders, get_all_claims
)
from claims_data_generator import generate_claim_note, generate_claim_notes
from config_loader import config
from database import container
from auth import exchange_code_for_token, get_current_user

# Initialize Azure Blob Service Client
blob_service_client = BlobServiceClient.from_connection_string(config['azure_blob_storage']['connection_string_one'])
container_client = blob_service_client.get_container_client(config['azure_blob_storage']['container_name'])


gpt_service_url = "http://127.0.0.1:5000/v1/chat/completions"  # Adjust the URL if different

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:8080", "https://ashy-rock-000761b1e.4.azurestaticapps.net/"],  # Allows requests from your frontend
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)
@app.post("/analyze-claims")
async def analyze_claims_endpoint(user=Depends(get_current_user)):
    claims = get_all_claims()
    logger.info(claims)
    txtcounts, txtaverages, gptcounts, gptaverages = analyze_claims(claims)
    return {
        "textfile_category_counts": txtcounts,
        "textfile_category_averages": txtaverages,
        "gptmsg_category_counts": gptcounts,
        "gptmsg_category_averages": gptaverages
    }

async def call_gpt_service(textfile: str):
    request_body = {
        "messages": [
            {
                "role": "user",
                "content": f"Please transform this brief note into a more detailed claim adjuster's note. Focus on the date, the type of damage, and the details of the claim. Keep it factual and under three sentences. Here's the note: {textfile} Please elaborate on the incident, ensuring it reads naturally stick to the facts and number provided."
            }
        ],
        "mode": "instruct",
        "instruction_template": "Alpaca"
    }
    timeout = httpx.Timeout(6000.0, connect=6000.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(gpt_service_url, json=request_body)
        if response.status_code == 200:
            response_data = response.json()
            # Extract the transformed text from the response
            transformed_text = response_data['choices'][0]['message']['content']
            return transformed_text
        else:
            # Handle errors or unexpected response format
            return None


async def categorize_claim(claim_text: str, better_prompt: bool = False):
    if better_prompt:
        content = (
            "Please extract the Claim Amount, Claims Category, Date, and Policyholder ID from the following text, structuring the data in JSON format. For categorization, use these guidelines:\n\n"
            "- Water Damage: Look for keywords like 'pipe burst', 'flooding', 'leakage'.\n"
            "- Fire Damage: Identify phrases like 'fire', 'burned', 'smoke damage'.\n"
            "- Theft/Burglary: Extract incidents involving 'theft', 'stolen', 'break-in'.\n"
            "- Auto Accident: Include cases with 'car crash', 'vehicle damage', 'collision'.\n"
            "- Natural Disaster: Categorize incidents related to 'storm', 'earthquake', 'hurricane'.\n"
            "- Health/Medical: Focus on 'medical care', 'hospitalization', 'health treatment'.\n"
            "- Liability Claims: Consider 'legal liability', 'personal injury', 'property damage'.\n\n"
            f"Example text for extraction:\n'{claim_text}'.\n\n"
            "If uncertain about the category, suggest the most likely one and confirm. For unique incidents, provide your best judgment on categorization based on these guidelines."
        )
    else:
        content = f"Please extract the Claim Amount, Claims Category, Date, and Policyholder ID from the following text. Please structure data in JSON: '{claim_text}'"

    request_body = {
        "messages": [{
            "role": "user",
            "content": content
        }],
        "mode": "instruct",
        "instruction_template": "Alpaca"
    }

    max_attempts = 4
    for attempt in range(max_attempts):
        try:
            timeout = httpx.Timeout(6000.0, connect=6000.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(gpt_service_url, json=request_body)
                if response.status_code == 200:
                    gpt_response = response.json()
                    content = gpt_response['choices'][0]['message']['content']
                    # Attempt to parse JSON
                    json_data = json.loads(content.split("</s>")[0])
                    return json_data
                else:
                    print(f"Attempt {attempt + 1}: Non-200 response")
        except json.JSONDecodeError:
            print(f"Attempt {attempt + 1}: Malformed JSON received. Response content: {content}")

    # If all attempts fail, return a predefined error object
    return {
        "Date": "error",
        "PolicyholderId": "error",
        "ClaimAmount": "error",
        "ClaimsCategory": "error",
        "BadReturn": content
    }


@app.post("/claims-analysis")
async def claims_analysis(data: dict = Body(...)):

    try:
        claims = data.get("claims", [])
        better_prompt = data.get("betterPrompt", False)
        analysis = []

        for claim in claims:
            claim_id = claim.get("id")
            textfile = claim.get("textfile")
            gptmsg = claim.get("gptmsg")

            # Analyze textfile
            textfile_analysis = await categorize_claim(textfile, better_prompt) if textfile else None
    
            # Analyze gptmsg
            gptmsg_analysis = await categorize_claim(gptmsg, better_prompt) if gptmsg else None

            analysis_data = {
                "textfile_analysis": textfile_analysis,
                "gptmsg_analysis": gptmsg_analysis
            }

            analysis.append({
                "id": claim_id,
                **analysis_data
            })

            # Update the claim in the database
            update_claim_with_analysis(claim_id, analysis_data)

        return {"analysis": analysis}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def update_claim_with_analysis(claim_id: str, analysis_data: dict):
    try:
        claim = get_claim_by_id(claim_id)
        if claim:
            claim['analysis'] = analysis_data
            container.upsert_item(claim)
    except Exception as e:
        print(f"Error updating claim {claim_id} with analysis: {str(e)}")

    
@app.post("/exchange-code")
async def exchange_auth_code(auth_code: AuthCode):
    token_response = await exchange_code_for_token(auth_code.code)
    return {"token": token_response.get("access_token")}

@app.post("/generate-synthetic-policyholders")
async def generate_synthetic_policyholders_data(request: PolicyholderRequest, user=Depends(get_current_user)):
    print(request)
    policyholders = [generate_policyholder_data() for _ in range(request.number_of_policyholders)]
    if request.add_to_database:
        for policyholder_data in policyholders:
            add_policyholder_to_db(policyholder_data)
    return policyholders

@app.post("/policyholders")
async def create_policyholder_endpoint(policyholder: Policyholder, user=Depends(get_current_user)):
    try:
        return create_policyholder(policyholder)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholders")
async def get_policyholders_endpoint(user=Depends(get_current_user)):
    try:
        return {"policyholders": get_policyholders()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholders/{id}")
async def get_policyholder_endpoint(id: str, user=Depends(get_current_user)):
    try:
        return {"policyholder": get_policyholder(id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/policyholders/{id}")
async def update_policyholder_endpoint(id: str, policyholder: Policyholder, user=Depends(get_current_user)):
    try:
        return update_policyholder(id, policyholder.dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/policyholders/{id}")
async def delete_policyholder_endpoint(id: str, user=Depends(get_current_user)):
    try:
        return delete_policyholder(id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/policyholders/search")
async def search_policyholders_endpoint(request_body: dict = Body(...), user=Depends(get_current_user)):
    name = request_body.get("name", "")
    try:
        return {"policyholders": search_policyholders(name)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/policyholders/average-amount")
async def calculate_average_policy_amount_endpoint(user=Depends(get_current_user)):
    try:
        return {"average_amount": calculate_average_policy_amount()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-claim-notes")
async def generate_claim_notes_api(request: GenerateClaimNotesRequest, user=Depends(get_current_user)):
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

@app.get("/download/{filename}")
async def download_blob(filename: str, user=Depends(get_current_user)):
    try:
        blob_client = container_client.get_blob_client(blob=filename)
        download_stream = blob_client.download_blob()
        data = download_stream.readall()

        # Create an in-memory buffer with the data
        return StreamingResponse(io.BytesIO(data), media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error downloading blob: {str(e)}")

@app.get("/search-blob-filenames")
async def search_blob_filenames(user=Depends(get_current_user)):
    try:
        # Fetch all blobs in the container
        blob_list = container_client.list_blobs()
        # Extract the names of the blobs
        blob_names = [blob.name for blob in blob_list]
        return {"blob_names": blob_names}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/claim-notes")
async def get_claim_notes(user=Depends(get_current_user)):
    try:
        blob_list = container_client.list_blobs()
        blobs_with_metadata = []
        for blob in blob_list:
            blob_client = container_client.get_blob_client(blob.name)
            blob_props = blob_client.get_blob_properties()
            blobs_with_metadata.append({
                "name": blob.name,
                "metadata": blob_props.metadata
            })
        return {"claim_notes": blobs_with_metadata}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/claim-notes/{blob_name}")
async def get_claim_note(blob_name: str, user=Depends(get_current_user)):
    try:
        blob_client = container_client.get_blob_client(blob_name)
        download_stream = blob_client.download_blob()
        return {"claim_note": download_stream.readall().decode("utf-8")}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Claim note {blob_name} not found")

@app.get("/claim-notes/analyze")
async def analyze_claim_notes(user=Depends(get_current_user)):
    # Logic to analyze claim notes, such as aggregating data or extracting insights
    # Placeholder for actual analysis logic
    return {"analysis": "This is a placeholder for claim notes analysis."}

@app.post("/claim-notes")
async def upload_claim_note(file: UploadFile = File(...), claimId: str = Form(...), user=Depends(get_current_user)):
    try:
        blob_name = f"claim_note_{claimId}_{file.filename}"
        blob_client = container_client.get_blob_client(blob_name)
        file_content = await file.read()  # Read file content as bytes

        # Define metadata with claim_id
        metadata = {"claim_id": claimId}

        blob_client.upload_blob(file_content, metadata=metadata, overwrite=True)  # Include metadata

        # Update CosmosDB item for the claim to include file_blob_name
        update_claim_with_file_blob_name(claimId, blob_name)

        return {"message": "Claim note uploaded", "blob_name": blob_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add-claim")
async def add_claim(request: AddClaimRequest, user=Depends(get_current_user)):
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


@app.get("/claims")
async def get_claims(policyholder_ids: Optional[List[str]] = Query(None), user=Depends(get_current_user)):
    try:
        if policyholder_ids:
            claims = get_claims_for_policyholders(policyholder_ids)
        else:
            claims = get_all_claims()
        return {"claims": claims}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process-claims")
async def process_claims(request: ProcessClaimsRequest, user=Depends(get_current_user)):
    responses = {}
    for claim_id in request.claimIds:
        gpt_response = await process_single_claim(claim_id)
        if gpt_response:
            responses[claim_id] = gpt_response
    return responses

async def process_single_claim(claim_id: str):
    claim = get_claim_by_id(claim_id)
    if claim and claim.get('textfile'):
        gpt_response = await call_gpt_service(claim['textfile'])
        if gpt_response:
            update_claim_with_gptmsg(claim_id, gpt_response)
            return gpt_response
    return None
@app.post("/delete-claims")
async def delete_claims(request: ClaimIdsRequest, user=Depends(get_current_user)):
    try:
        for claim_id in request.claimIds:
            delete_claim(claim_id)  # Implement this function in CRUD operations
        return {"message": "Claims deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Additional endpoints for claim notes and pdf and file analysis if we have time...
# ...

@app.get("/")
async def root():
    return {"message": "Insurance Data API Root"}
