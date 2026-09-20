import os
import time
import logging
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("translator_server")

app = FastAPI(
    title="Webtoon Manhwa Translation Cloud API",
    description="API REST ultrarrápida y ligera para traducción de Manhwas en tiempo real",
    version="2.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global variables for model and tokenizer
translator_model = None
tokenizer = None
translation_cache = {}

MODEL_NAME = "Helsinki-NLP/opus-mt-en-es"
CT2_DIR = os.path.join(os.path.dirname(__file__), "opus-mt-en-es-ct2")


def init_translation_engine():
    global translator_model, tokenizer
    import ctranslate2
    import transformers

    log.info("Inicializando motor de traducción ligero CTranslate2 INT8...")
    if not os.path.exists(CT2_DIR):
        raise FileNotFoundError(f"Directorio de modelo pre-convertido no encontrado: {CT2_DIR}")

    # Cargar modelo CTranslate2 directamente sin sobrecarga de PyTorch (RAM < 90MB)
    translator_model = ctranslate2.Translator(CT2_DIR, device="cpu", compute_type="int8")
    tokenizer = transformers.MarianTokenizer.from_pretrained(MODEL_NAME)
    log.info("Motor de traducción CTranslate2 listo (Consumo de RAM < 90MB).")


@app.on_event("startup")
def startup_event():
    init_translation_engine()


class TranslationRequest(BaseModel):
    texts: List[str]
    src_lang: str = "en"
    tgt_lang: str = "es"


class TranslationResponse(BaseModel):
    translations: List[str]
    process_time_ms: float


def normalize_comic_casing(text: str) -> str:
    """Convierte texto en MAYÚSCULAS de viñetas a formato oración para máxima precisión en MarianMT."""
    alphas = [c for c in text if c.isalpha()]
    if not alphas:
        return text
    upper_ratio = sum(1 for c in alphas if c.isupper()) / len(alphas)
    if upper_ratio > 0.6:
        lowered = text.lower()
        import re
        parts = re.split(r'([\.\!\?]\s*)', lowered)
        res = ""
        for i in range(0, len(parts), 2):
            part = parts[i]
            punct = parts[i+1] if i+1 < len(parts) else ""
            if part:
                part = part[0].upper() + part[1:]
            res += part + punct
        return res
    return text


@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Webtoon Translation Cloud API",
        "backend": "CTranslate2 INT8 (Lightweight)",
        "ram_usage": "< 90 MB",
        "model": MODEL_NAME
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/translate", response_model=TranslationResponse)
async def translate_endpoint(req: TranslationRequest):
    if not req.texts:
        return TranslationResponse(translations=[], process_time_ms=0.0)

    start_t = time.time()
    results = [None] * len(req.texts)
    to_translate_indices = []
    to_translate_tokens = []

    for idx, text in enumerate(req.texts):
        cleaned = text.strip()
        if not cleaned:
            results[idx] = ""
            continue

        normalized = normalize_comic_casing(cleaned)
        cache_key = f"{req.src_lang}:{req.tgt_lang}:{normalized}"

        if cache_key in translation_cache:
            results[idx] = translation_cache[cache_key]
        else:
            to_translate_indices.append((idx, cache_key))
            tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(normalized))
            to_translate_tokens.append(tokens)

    if to_translate_tokens and translator_model is not None:
        ct2_results = translator_model.translate_batch(to_translate_tokens)
        for (original_idx, cache_key), res in zip(to_translate_indices, ct2_results):
            target_tokens = res.hypotheses[0]
            translated_str = tokenizer.decode(tokenizer.convert_tokens_to_ids(target_tokens))
            translation_cache[cache_key] = translated_str
            results[original_idx] = translated_str

    elapsed = (time.time() - start_t) * 1000
    return TranslationResponse(translations=results, process_time_ms=round(elapsed, 2))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
