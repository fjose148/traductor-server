# 🚀 Guía de Despliegue 100% Gratuito en Hugging Face Spaces

Sigue estos 4 sencillos pasos para desplegar tu servidor de traducción en la nube sin costo y 24/7.

---

### Paso 1: Crear una cuenta en Hugging Face (Si no tienes una)
1. Entra a [https://huggingface.co/join](https://huggingface.co/join) y regístrate gratis.

---

### Paso 2: Crear un nuevo "Space" (Servidor Nube)
1. Ve a [https://huggingface.co/new-space](https://huggingface.co/new-space).
2. Asigna un nombre a tu Space, por ejemplo: `mi-traductor-manhwa`.
3. Selecciona **SDK**: `Docker` ➔ **Template**: `Blank`.
4. En **Space Hardware**, deja seleccionado **CPU basic (Free)** (16 GB RAM / 2 vCPU 100% Gratis).
5. Haz clic en **Create Space**.

---

### Paso 3: Subir los archivos del servidor
En la pestaña **Files and versions** de tu nuevo Space en Hugging Face, sube estos 3 archivos del directorio `server/`:
- `main.py`
- `requirements.txt`
- `Dockerfile`

---

### Paso 4: ¡Listo! Obtener tu URL de la API
Hugging Face construirá el contenedor automáticamente en ~1-2 minutos.
Una vez diga **Building ➔ Running**, la URL pública de tu API será:
`https://<TU-USUARIO>-mi-traductor-manhwa.hf.space/translate`

¡Copia esa URL y pégala en la App Android!
