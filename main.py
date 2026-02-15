from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from openai import OpenAI
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods including OPTIONS
    allow_headers=["*"],  # Allows all headers
)

# === COMPONENT FUNCTIONS ===

def fetch_uuids(count=3):
    """Fetch UUIDs from HTTPBin"""
    uuids = []
    for i in range(count):
        try:
            response = httpx.get("https://httpbin.org/uuid", timeout=10.0)
            response.raise_for_status()
            data = response.json()
            uuids.append(data["uuid"])
        except Exception as e:
            print(f"Error fetching UUID {i+1}: {e}")
    return uuids

def analyze_with_ai(text):
    """Use AI to analyze the text"""
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        prompt = f"""Analyze this UUID and respond with ONLY a JSON object:
        
UUID: {text}

Format:
{{"analysis": "2-3 sentence analysis", "sentiment": "optimistic/pessimistic/balanced"}}"""
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        result = response.choices[0].message.content.strip()
        parsed = json.loads(result)
        return parsed["analysis"], parsed["sentiment"]
        
    except Exception as e:
        return f"Analysis unavailable: {str(e)}", "neutral"

def store_results(results):
    """Store results in JSON file"""
    try:
        filename = "pipeline_results.json"
        
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        else:
            existing_data = []
        
        existing_data.extend(results)
        
        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Storage error: {e}")
        return False

def send_notification(email, success_count, error_count):
    """Send notification (simulated)"""
    try:
        message = f"""
        ✉️ NOTIFICATION SENT TO: {email}
        -----------------------------------
        Pipeline Processing Complete
        Successfully processed: {success_count} items
        Errors encountered: {error_count}
        """
        print(message)
        return True
    except Exception as e:
        print(f"Notification error: {e}")
        return False

# === MAIN PIPELINE ===

def run_pipeline(email):
    """Main pipeline orchestration"""
    errors = []
    results = []
    
    print("\n🚀 === PIPELINE STARTED ===\n")
    
    # Stage 1: Fetch
    print("📥 Stage 1: Fetching UUIDs from HTTPBin...")
    uuids = fetch_uuids(3)
    if not uuids:
        errors.append("Failed to fetch any UUIDs")
        return {"items": [], "notificationSent": False, "errors": errors}
    print(f"✓ Fetched {len(uuids)} UUIDs\n")
    
    # Stage 2: AI Analysis
    print("🤖 Stage 2: AI Analysis...")
    for idx, uuid in enumerate(uuids, 1):
        try:
            print(f"  Analyzing UUID {idx}/{len(uuids)}...")
            analysis, sentiment = analyze_with_ai(uuid)
            
            result = {
                "original": uuid,
                "analysis": analysis,
                "sentiment": sentiment,
                "stored": False,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            results.append(result)
            print(f"  ✓ Sentiment: {sentiment}")
            
        except Exception as e:
            errors.append(f"Failed to process UUID {uuid}: {str(e)}")
            print(f"  ❌ Error: {e}")
    
    print(f"✓ Analyzed {len(results)} items\n")
    
    # Stage 3: Storage
    print("💾 Stage 3: Storing results...")
    storage_success = store_results(results)
    for result in results:
        result["stored"] = storage_success
    print(f"✓ Storage {'successful' if storage_success else 'failed'}\n")
    
    # Stage 4: Notification
    print("📧 Stage 4: Sending notification...")
    notification_sent = send_notification(email, len(results), len(errors))
    print(f"✓ Notification sent to {email}\n")
    
    print("✅ === PIPELINE COMPLETE ===\n")
    
    return {
        "items": results,
        "notificationSent": notification_sent,
        "processedAt": datetime.utcnow().isoformat() + "Z",
        "errors": errors
    }

# === API ENDPOINTS ===

class PipelineRequest(BaseModel):
    email: str
    source: str

@app.post("/pipeline")
def pipeline_endpoint(request: PipelineRequest):
    """Main pipeline API endpoint"""
    if request.source != "HTTPBin UUID":
        raise HTTPException(
            status_code=400, 
            detail="Source must be 'HTTPBin UUID'"
        )
    
    result = run_pipeline(request.email)
    return result

@app.get("/")
def health_check():
    return {
        "status": "🟢 Pipeline API is running",
        "endpoint": "POST /pipeline",
        "example": {
            "email": "your@email.com",
            "source": "HTTPBin UUID"
        }
    }

# === FOR LOCAL TESTING ===

if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
