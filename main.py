import os
import re
import time
import base64
import logging
from io import BytesIO
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
log = logging.getLogger("translator_server")

app = FastAPI(
    title="Webtoon Manhwa Translation Cloud API",
    description="API REST ultrarrápida para traducción de Manhwas — soporta texto puro e imagen Base64",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Globales ─────────────────────────────────────────────────────────────────

translator_model = None
tokenizer        = None
ocr_reader       = None          # easyocr.Reader cargado bajo demanda
translation_cache: dict = {}

MODEL_NAME = "Helsinki-NLP/opus-mt-en-es"
CT2_DIR    = os.path.join(os.path.dirname(__file__), "opus-mt-en-es-ct2")


# ── Inicialización ────────────────────────────────────────────────────────────

def init_translation_engine():
    global translator_model, tokenizer
    import ctranslate2
    import transformers

    log.info("Inicializando CTranslate2 INT8...")
    if not os.path.exists(CT2_DIR):
        raise FileNotFoundError(f"Modelo no encontrado: {CT2_DIR}")

    translator_model = ctranslate2.Translator(CT2_DIR, device="cpu", compute_type="int8")
    tokenizer        = transformers.MarianTokenizer.from_pretrained(MODEL_NAME)
    log.info("Motor listo (<90 MB RAM).")


def get_ocr_reader():
    """Carga EasyOCR la primera vez que se necesita (lazy init para ahorrar RAM en arranque)."""
    global ocr_reader
    if ocr_reader is None:
        log.info("Cargando EasyOCR (primera petición de imagen)...")
        import easyocr
        ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        log.info("EasyOCR listo.")
    return ocr_reader


@app.on_event("startup")
def startup_event():
    init_translation_engine()


# ── Modelos de datos ──────────────────────────────────────────────────────────

class TranslationRequest(BaseModel):
    texts: List[str]
    src_lang: str = "en"
    tgt_lang: str = "es"


class TranslationResponse(BaseModel):
    translations: List[str]
    process_time_ms: float


# ── Helpers ───────────────────────────────────────────────────────────────────

def normalize_comic_casing(text: str) -> str:
    """Convierte texto en MAYÚSCULAS de viñetas a formato oración para máxima precisión en MarianMT."""
    alphas = [c for c in text if c.isalpha()]
    if not alphas:
        return text
    upper_ratio = sum(1 for c in alphas if c.isupper()) / len(alphas)
    if upper_ratio > 0.6:
        lowered = text.lower()
        parts = re.split(r'([\.!\?]\s*)', lowered)
        res = ""
        for i in range(0, len(parts), 2):
            part  = parts[i]
            punct = parts[i + 1] if i + 1 < len(parts) else ""
            if part:
                part = part[0].upper() + part[1:]
            res += part + punct
        return res
    return text


def clean_ocr_text(text: str) -> str:
    """Limpia artefactos típicos del OCR en cómics (caracteres sueltos, puntuación extraña)."""
    # Eliminar líneas de un solo carácter o con menos de 2 letras
    lines = [ln.strip() for ln in text.splitlines() if len(re.findall(r"[a-zA-Z]", ln)) >= 2]
    return " ".join(lines)


def do_batch_translate(texts: List[str]) -> List[str]:
    """Traduce una lista de textos usando CTranslate2, con caché."""
    if not texts or translator_model is None:
        return [""] * len(texts)

    results = [None] * len(texts)
    indices_to_translate = []
    token_batches        = []

    for idx, text in enumerate(texts):
        if not text.strip():
            results[idx] = ""
            continue
        normalized = normalize_comic_casing(text.strip())
        key = f"en:es:{normalized}"
        if key in translation_cache:
            results[idx] = translation_cache[key]
        else:
            indices_to_translate.append((idx, key, normalized))
            tokens = tokenizer.convert_ids_to_tokens(tokenizer.encode(normalized))
            token_batches.append(tokens)

    if token_batches:
        ct2_out = translator_model.translate_batch(token_batches)
        for (orig_idx, cache_key, _), res in zip(indices_to_translate, ct2_out):
            target_tokens  = res.hypotheses[0]
            translated_str = tokenizer.decode(tokenizer.convert_tokens_to_ids(target_tokens))
            translation_cache[cache_key] = translated_str
            results[orig_idx] = translated_str

    return results


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {
        "status": "online",
        "version": "3.0.0",
        "modes": ["text", "image_en"],
        "backend": "CTranslate2 INT8",
        "model": MODEL_NAME
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": time.time()}


@app.post("/translate", response_model=TranslationResponse)
async def translate_endpoint(req: TranslationRequest):
    """
    Endpoint unificado:
    - src_lang = "en"       → traduce los textos directamente (modo texto puro)
    - src_lang = "image_en" → cada elemento de `texts` es una imagen JPEG/PNG en Base64;
                              el servidor hace OCR y luego traduce el resultado.
    """
    if not req.texts:
        return TranslationResponse(translations=[], process_time_ms=0.0)

    start_t = time.time()
    texts_to_translate: List[str] = []

    # ── Modo imagen Base64 ────────────────────────────────────────────────
    if req.src_lang == "image_en":
        reader = get_ocr_reader()
        for b64_str in req.texts:
            try:
                img_bytes = base64.b64decode(b64_str)
                import numpy as np
                from PIL import Image
                img = Image.open(BytesIO(img_bytes)).convert("RGB")
                img_np = np.array(img)
                ocr_results = reader.readtext(img_np, detail=0, paragraph=True)
                raw_text    = " ".join(ocr_results)
                cleaned     = clean_ocr_text(raw_text)
                texts_to_translate.append(cleaned if cleaned else "")
            except Exception as e:
                log.warning(f"OCR error: {e}")
                texts_to_translate.append("")
    else:
        # ── Modo texto puro ───────────────────────────────────────────────
        texts_to_translate = req.texts

    translations = do_batch_translate(texts_to_translate)
    elapsed      = (time.time() - start_t) * 1000
    return TranslationResponse(translations=translations, process_time_ms=round(elapsed, 2))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
