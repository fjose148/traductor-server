import os
import time
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("translator_server")

app = FastAPI(
    title="Webtoon Manhwa Translation Cloud API",
    description="API REST ultrarrápida y ligera para traducción de Manhwas en tiempo real con panel de inspección",
    version="2.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

translator_model = None
tokenizer = None
translation_cache = {}
history_logs: List[Dict[str, Any]] = []

MODEL_NAME = "Helsinki-NLP/opus-mt-en-es"
CT2_DIR = os.path.join(os.path.dirname(__file__), "opus-mt-en-es-ct2")


def init_translation_engine():
    global translator_model, tokenizer
    import ctranslate2
    import transformers

    log.info("Inicializando motor de traducción ligero CTranslate2 INT8...")
    if not os.path.exists(CT2_DIR):
        raise FileNotFoundError(f"Directorio de modelo pre-convertido no encontrado: {CT2_DIR}")

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
        "model": MODEL_NAME,
        "total_translations_logged": len(history_logs),
        "last_activity": history_logs[-1] if history_logs else "Sin peticiones aún"
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}


@app.get("/logs")
def get_logs():
    """Devuelve las últimas 30 traducciones recibidas desde el celular en tiempo real."""
    return {
        "count": len(history_logs),
        "recent_requests": list(reversed(history_logs[-30:]))
    }


@app.get("/last")
def get_last_translation():
    """Devuelve la última traducción enviada por el móvil."""
    if not history_logs:
        return {"status": "waiting", "message": "Aún no se han recibido peticiones desde el móvil"}
    return history_logs[-1]


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

    # Registrar en historial en memoria para que podamos inspeccionar las peticiones en vivo
    entry = {
        "id": len(history_logs) + 1,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "received_texts": req.texts,
        "translations": results,
        "process_time_ms": round(elapsed, 2)
    }
    history_logs.append(entry)
    if len(history_logs) > 100:
        history_logs.pop(0)

    return TranslationResponse(translations=results, process_time_ms=round(elapsed, 2))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
