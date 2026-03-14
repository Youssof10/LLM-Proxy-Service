from fastapi import FastAPI, HTTPException
import httpx

app = FastAPI()

WORKERS = {
    "phi3": "http://model-phi3-container:11434",
    "tinyllama": "http://model-tinyllama-container:11434"
}

@app.post("/generate/{model_name}")
async def route_request(model_name: str, payload: dict):
    if model_name not in WORKERS:
        raise HTTPException(status_code=404, detail="Model not found.")
    
    prompt = payload.get("prompt")
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is missing.")

    target_url = f"{WORKERS[model_name]}/api/generate"
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            response = await client.post(
                target_url,
                json={"model": model_name, "prompt": prompt, "stream": False}
            )
            data = response.json()

            if "error" in data:
                return {"model": model_name, "error": data["error"]}
            return {"model": model_name,
                    "output": data.get("response", "")
                    }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Container error: {str(e)}")