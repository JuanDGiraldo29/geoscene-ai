"""La API.   Responsable: capa de consumo.

Cómo se ejecuta (desde la carpeta raíz):
    uvicorn api.main:app --reload --port 8000
Documentación automática para probar los endpoints: http://localhost:8000/docs

Esta versión YA FUNCIONA con el clasificador de prueba (mock), para que la
interfaz pueda empezar hoy. Los TODO son lo que falta para que sea la
versión final. El formato de cada respuesta está en docs/CONTRATO.md.
"""
import io
import uuid

from fastapi import FastAPI, File, HTTPException, UploadFile
from PIL import Image

from api.clasificador import crear_predictor
from compartido.constantes import AVISO_ALCANCE, CLASES, CLASES_ES

app = FastAPI(title="GeoScene AI")

# TODO 1: cargar el predictor UNA vez al arrancar la API (no en cada petición).
#         Con `predictor = crear_predictor()` a nivel de módulo ya se cumple;
#         opcionalmente muévanlo a un "lifespan" de FastAPI para aprender el patrón.
predictor = crear_predictor()

# TODO 4: esta memoria se pierde al reiniciar. Guardar en CSV (outputs/predicciones.csv
#         y outputs/decisiones.csv, dos archivos separados) para conservar el
#         resultado del modelo aparte de la decisión humana.
PREDICCIONES = {}
DECISIONES = {}


@app.get("/health")
def salud():
    return {"status": "ok", "modo": predictor.modo}


@app.get("/clases")
def clases():
    return {"clases": CLASES, "nombres_es": CLASES_ES}


@app.get("/alcance")
def alcance():
    return {"aviso": AVISO_ALCANCE}


@app.post("/predict")
async def predecir(file: UploadFile = File(...)):
    contenido = await file.read()

    # TODO 2: reemplazar estas líneas por cargar_imagen(contenido) de api/clasificador.py
    #         y devolver HTTPException(status_code=400, detail=str(error)) si lanza
    #         ArchivoInvalidoError (la interfaz muestra ese mensaje a la persona).
    imagen = Image.open(io.BytesIO(contenido)).convert("RGB")

    resultado = predictor.predecir(imagen)
    id_prediccion = uuid.uuid4().hex[:12]
    PREDICCIONES[id_prediccion] = {"archivo": file.filename, **resultado}
    return {"id_prediccion": id_prediccion, **resultado}


@app.post("/decision")
def decision(entrada: dict):
    """Cuerpo: {"id_prediccion": "...", "categoria_humana": "Forest"}"""
    id_prediccion = entrada.get("id_prediccion")
    categoria_humana = entrada.get("categoria_humana")

    if id_prediccion not in PREDICCIONES:
        raise HTTPException(status_code=404, detail="No existe una predicción con ese id.")
    if categoria_humana not in CLASES:
        raise HTTPException(status_code=400, detail="La categoría no es una de las 10 clases.")

    # TODO 3: si esa predicción ya tiene decisión, responder 409.
    # TODO 5: definir modelos Pydantic (clase Prediccion, clase Decision) y usarlos
    #         como response_model: FastAPI valida las respuestas y documenta el contrato.
    pred = PREDICCIONES[id_prediccion]
    DECISIONES[id_prediccion] = categoria_humana
    return {
        "id_prediccion": id_prediccion,
        "categoria_modelo": pred["categoria"],   # la predicción original NUNCA se modifica
        "decision_humana": categoria_humana,
        "estado": "aceptada" if categoria_humana == pred["categoria"] else "corregida",
    }
