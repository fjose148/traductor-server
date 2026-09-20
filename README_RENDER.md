# 🚀 Guía de Despliegue Gratuito en Render.com

Render.com ofrece un plano **Free Tier ($0/mes)** perfecto para alojar el servidor backend Python de traducción.

---

### Paso 1: Crear cuenta en Render.com
1. Ingresa a [https://render.com](https://render.com) y créate una cuenta gratuita usando GitHub o Google.

---

### Paso 2: Subir el servidor a GitHub
1. Crea un repositorio en tu cuenta de GitHub (ejemplo: `traductor-manhwa-server`).
2. Sube los archivos del directorio `server/`:
   - `main.py`
   - `requirements.txt`
   - `render.yaml`

---

### Paso 3: Crear el Servicio Web en Render
1. En el panel de Render, haz clic en el botón **New +** ➔ selecciona **Web Service**.
2. Conecta tu repositorio de GitHub `traductor-manhwa-server`.
3. Configura los datos principales:
   - **Name**: `traductor-manhwa-api` (o el nombre que gustes)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Selecciona **Free ($0/month)**.
4. Haz clic en **Create Web Service**.

---

### Paso 4: ¡Obtener tu URL Pública para la APK!
Render compilará e iniciará la aplicación en ~1-2 minutos.
Una vez listo, te entregará una URL pública funcional como:
`https://tu-traductor.onrender.com/translate`

¡Pega esa URL en tu App Android y listo!
