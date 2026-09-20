import sys
import os
import requests
import time
from pathlib import Path

# Setup sys.path
sys.path.insert(0, str(Path(__file__).parent))

from main import normalize_comic_casing, init_translation_engine, translate_endpoint, TranslationRequest

print("=== 1. Probando Normalización de Viñeta ===")
text1 = "Y, YOUR MAJESTY...!"
text2 = "THE MAIN PROTAGONIST TRAVELS TO ANOTHER DIMENSION..."
print(f"Original 1: {text1} -> Normalizado: {normalize_comic_casing(text1)}")
print(f"Original 2: {text2} -> Normalizado: {normalize_comic_casing(text2)}")

print("\n=== 2. Probando Inferencia Local CTranslate2 ===")
init_translation_engine()

import asyncio

async def test_async():
    req = TranslationRequest(texts=["Y, YOUR MAJESTY...!", "THE MAIN PROTAGONIST TRAVELS TO ANOTHER DIMENSION..."])
    res = await translate_endpoint(req)
    print(f"Tiempo de respuesta API: {res.process_time_ms} ms")
    for orig, trad in zip(req.texts, res.translations):
        print(f"Original:   {orig}")
        print(f"Traducido:  {trad}")
        print("-" * 40)

asyncio.run(test_async())
