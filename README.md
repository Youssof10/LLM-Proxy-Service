# Local LLM Proxy Gateway

An asynchronous FastAPI proxy gateway that intelligently routes user prompts to isolated, locally hosted Large Language Models (LLMs) running inside Docker containers.

## 1. System Architecture

This project utilizes a microservices architecture to ensure isolation and scalability:

* **Gateway (FastAPI):** Acts as the entry point, receiving POST requests and routing them to the appropriate model based on the URL path. It handles asynchronous connections and error management.
* **Worker 1 (Phi-3):** A dedicated container running the official Ollama image, serving the Microsoft `phi3` model for tasks requiring complex reasoning and logic.
* **Worker 2 (TinyLlama):** A dedicated container serving the `tinyllama` model for high-speed, low-latency text generation.
* **Storage:** Persistent Docker Volumes (`phi3_data`, `tinyllama_data`) store multi-gigabyte model weights locally, ensuring containers remain stateless while avoiding repeated downloads on restart.

### Project Structure
```
LLM-Proxy-Service/
├── docker-compose.yml       # Orchestrates all services and resource limits
├── proxy/
│   ├── Dockerfile
│   ├── app.py               # FastAPI gateway — routes /generate/{model_name}
│   └── requirements.txt
├── model_phi3/
│   └── Dockerfile           # Ollama container for Phi-3
└── model_tinyllama/
    └── Dockerfile           # Ollama container for TinyLlama
```

### Resource Allocation

| Container | CPU Limit | Memory Limit |
|---|---|---|
| proxy | 1.0 cores | 1 GB |
| model-phi3-container | 6.0 cores | 8 GB |
| model-tinyllama-container | 4.0 cores | 4 GB |

## 2. Setup Instructions

**Prerequisites:**
* Docker Desktop installed and running.
* At least 10–15 GB of free local storage for the LLM weights.

**Step 1: Clone the repository**
```bash
git clone https://github.com/Youssof10/LLM-Proxy-Service.git
cd LLM-Proxy-Service
```

**Step 2: Build and start all services**
```bash
docker-compose up -d --build
```

**Step 3: Pull the model weights**

Model weights are intentionally excluded from the repository. Pull them directly into the persistent volumes:
```bash
docker exec -it model-tinyllama-container ollama pull tinyllama
docker exec -it model-phi3-container ollama pull phi3
```
*(Wait for both downloads to complete with "success" before proceeding.)*

**Step 4: Test the API**

Test the fast model (TinyLlama):
```bash
curl -X POST http://localhost:8000/generate/tinyllama \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Say hello to a Data Scientist!"}'
```

Test the smart model (Phi-3):
```bash
curl -X POST http://localhost:8000/generate/phi3 \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the three main pillars of Data Science?"}'
```

**Step 5: Stop the services**
```bash
docker-compose down
```

### API Reference

**Endpoint:** `POST /generate/{model_name}`

**Supported model names:** `phi3`, `tinyllama`

**Request body:**
```json
{ "prompt": "Your question here" }
```

**Success response:**
```json
{ "model": "phi3", "output": "The model's response..." }
```

**Error response:**
```json
{ "model": "phi3", "error": "model 'phi3' not found, try pulling it first" }
```

### Optional: GPU Acceleration

Each model container in `docker-compose.yml` includes a commented-out `reservations` block for NVIDIA GPU support. Uncomment it to enable GPU acceleration if the host machine has NVIDIA drivers installed:
```yaml
reservations:
  devices:
    - driver: nvidia
      count: all
      capabilities: [gpu]
```

## 3. Assumptions

* **Compute Constraints:** The architecture is designed to run on standard CPU hardware. GPU acceleration is optional and disabled by default.
* **Port Availability:** Port `8000` (FastAPI gateway) and internal container port `11434` (Ollama) must be available.
* **Network Independence:** Once the initial model weights are downloaded, the system operates fully offline.
* **Manual Model Initialization:** Model weights are pulled manually after startup to avoid race conditions and long startup delays.

## 4. Challenges

* **Hardware Constraints & Framework Limitations:** Initially built using `transformers` and `torch` with lightweight models (`gpt-2`, `distilgpt2`), but these produced insufficient output quality on CPU hardware.
  * *Solution:* Pivoted entirely to **Ollama**, which uses `llama.cpp` under the hood and is highly optimized for CPU inference — enabling much more capable models like Phi-3 without requiring a GPU.

* **CPU Inference Timeouts:** Running a 3.8-billion parameter model (Phi-3) on a CPU caused the FastAPI gateway to drop connections before inference completed.
  * *Solution:* Set a custom 300-second timeout on the `httpx.AsyncClient` to accommodate CPU-bound latency.

* **Container Race Conditions:** Auto-pulling models via Docker `entrypoint` scripts caused the API to receive requests before the multi-gigabyte download completed, resulting in "model not found" errors.
  * *Solution:* Decoupled weight fetching from container startup — models are pulled manually into persistent volumes after the containers are running.

## 5. Design Decisions

* **Iterative Framework Pivot:** Transitioning from Hugging Face `transformers` to Ollama was deliberate — maximizing output quality while strictly adhering to the CPU-only hardware constraint.
* **FastAPI for the Gateway:** Chosen for native `async`/`await` support, which is critical when proxying slow, I/O-bound LLM generation tasks.
* **Model Selection:** `phi3` demonstrates capability with a dense, highly capable reasoning model; `tinyllama` demonstrates a lightweight, high-throughput alternative.
* **Docker Volumes over Bind Mounts:** Named volumes (`phi3_data`, `tinyllama_data`) keep model weights safely within the Docker ecosystem and prevent accidental commits of large files.
* **Transparent Error Handling:** Ollama engine errors (e.g., missing weights) are surfaced directly through the gateway rather than swallowed, improving API observability.
