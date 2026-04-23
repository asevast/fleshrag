from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import torch
import uvicorn

app = FastAPI(title="Multilingual E5 Large Embeddings")

# Загрузка модели с префиксом для e5
model = None
device = None

class EmbedRequest(BaseModel):
    texts: list[str]
    is_query: bool = False

class EmbedResponse(BaseModel):
    embeddings: list[list[float]]

@app.on_event("startup")
async def load_model():
    global model, device
    # Определение устройства: GPU если доступен, иначе CPU
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading multilingual-e5-large model on {device}...")
    if device == "cuda":
        print(f"CUDA available: {torch.cuda.get_device_name(0)}")
        print(f"CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    model = SentenceTransformer("intfloat/multilingual-e5-large", device=device)
    print("Model loaded successfully")

@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest):
    if model is None:
        raise RuntimeError("Model not loaded")
    
    prefix = "query: " if request.is_query else "passage: "
    prefixed_texts = [prefix + t for t in request.texts]
    embeddings = model.encode(prefixed_texts, normalize_embeddings=True).tolist()
    
    return EmbedResponse(embeddings=embeddings)

@app.get("/health")
async def health():
    return {"status": "ok", "model": "multilingual-e5-large"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
