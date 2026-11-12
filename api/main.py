"""La API.   Responsable: capa de consumo.

Cómo se ejecuta (desde la carpeta raíz):
    uvicorn api.main:app --reload --port 8000
Documentación automática para probar los endpoints: http://localhost:8000/docs

El formato de cada respuesta está en docs/CONTRATO.md.
"""
import csv
import os
import uuid
from datetime import datetime

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from api.clasificador import ArchivoInvalidoError, cargar_imagen, crear_predictor
from compartido.constantes import AVISO_ALCANCE, CARPETA_SALIDAS, CLASES, CLASES_ES

app = FastAPI(title="GeoScene AI")

# El modelo se carga UNA vez, al arrancar la API (no en cada petición)
predictor = crear_predictor()

# Dos archivos SEPARADOS: lo que dijo el modelo y lo que decidió la persona
RUTA_PREDICCIONES = os.path.join(CARPETA_SALIDAS, "predicciones.csv")
RUTA_DECISIONES = os.path.join(CARPETA_SALIDAS, "decisiones.csv")
CAMPOS_PREDICCION = ["fecha", "id_prediccion", "archivo", "modo", "categoria_modelo",
                     "confianza", "requiere_revision", "top3"]
CAMPOS_DECISION = ["fecha", "id_prediccion", "archivo", "categoria_modelo", "confianza",
                   "requiere_revision", "decision_humana", "estado"]


def leer_filas(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def anadir_fila(ruta, campos, fila):
    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    es_nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=campos)
        if es_nuevo:
            escritor.writeheader()  # la cabecera solo se escribe al crear el archivo
        escritor.writerow(fila)


# Memoria de trabajo, recargada desde los CSV: así los ids siguen valiendo si se reinicia la API
PREDICCIONES = {fila["id_prediccion"]: fila for fila in leer_filas(RUTA_PREDICCIONES)}
DECISIONES = {fila["id_prediccion"] for fila in leer_filas(RUTA_DECISIONES)}


# Esquemas: FastAPI valida las respuestas con ellos y los muestra en /docs
class Puntuacion(BaseModel):
    categoria: str
    confianza: float


class Prediccion(BaseModel):
    id_prediccion: str
    categoria: str
    confianza: float
    top3: list[Puntuacion]
    requiere_revision: bool
    umbral: float
    tiempo_inferencia_ms: float


class DecisionEntrada(BaseModel):
    id_prediccion: str
    categoria_humana: str


class DecisionSalida(BaseModel):
    id_prediccion: str
    categoria_modelo: str
    decision_humana: str
    estado: str  # "aceptada" o "corregida"


@app.get("/health")
def salud():
    return {"status": "ok", "modo": predictor.modo}


@app.get("/clases")
def clases():
    return {"clases": CLASES, "nombres_es": CLASES_ES}


@app.get("/alcance")
def alcance():
    return {"aviso": AVISO_ALCANCE}


@app.post("/predict", response_model=Prediccion)
async def predecir(file: UploadFile = File(...)):
    contenido = await file.read()
    try:
        imagen = cargar_imagen(contenido)
    except ArchivoInvalidoError as error:
        raise HTTPException(status_code=400, detail=str(error))

    resultado = predictor.predecir(imagen)
    id_prediccion = uuid.uuid4().hex[:12]

    fila = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "id_prediccion": id_prediccion,
        "archivo": file.filename or "sin_nombre",
        "modo": predictor.modo,
        "categoria_modelo": resultado["categoria"],
        "confianza": resultado["confianza"],
        "requiere_revision": resultado["requiere_revision"],
        "top3": "; ".join(f"{p['categoria']}={p['confianza']}" for p in resultado["top3"]),
    }
    anadir_fila(RUTA_PREDICCIONES, CAMPOS_PREDICCION, fila)
    PREDICCIONES[id_prediccion] = fila
    return {"id_prediccion": id_prediccion, **resultado}


@app.post("/decision", response_model=DecisionSalida)
def decision(entrada: DecisionEntrada):
    if entrada.id_prediccion not in PREDICCIONES:
        raise HTTPException(status_code=404, detail="No existe una predicción con ese id.")
    if entrada.categoria_humana not in CLASES:
        raise HTTPException(status_code=400, detail="La categoría no es una de las 10 clases.")
    if entrada.id_prediccion in DECISIONES:
        raise HTTPException(status_code=409, detail="Esa predicción ya tiene una decisión registrada.")

    pred = PREDICCIONES[entrada.id_prediccion]
    estado = "aceptada" if entrada.categoria_humana == pred["categoria_modelo"] else "corregida"

    # La predicción original NUNCA se modifica: la decisión va en otro archivo
    anadir_fila(RUTA_DECISIONES, CAMPOS_DECISION, {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "id_prediccion": entrada.id_prediccion,
        "archivo": pred["archivo"],
        "categoria_modelo": pred["categoria_modelo"],
        "confianza": pred["confianza"],
        "requiere_revision": pred["requiere_revision"],
        "decision_humana": entrada.categoria_humana,
        "estado": estado,
    })
    DECISIONES.add(entrada.id_prediccion)

    return {
        "id_prediccion": entrada.id_prediccion,
        "categoria_modelo": pred["categoria_modelo"],
        "decision_humana": entrada.categoria_humana,
        "estado": estado,
    }