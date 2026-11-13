"""La API.   Responsable: capa de consumo.

Cómo se ejecuta (desde la carpeta raíz):
    uvicorn api.main:app --reload --port 8000

Documentación:  http://localhost:8000/docs   (Swagger UI, se puede ejecutar)
Panel en vivo:  http://localhost:8000/panel
Mapa de conexiones y orígenes: docs/API.md

El formato de cada respuesta está en docs/CONTRATO.md.
"""
import csv
import os
import uuid
from datetime import datetime
from typing import Literal

from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from api.clasificador import ArchivoInvalidoError, cargar_imagen, crear_predictor
from api.docs import PAGINA_DOCS
from api.panel import PAGINA
from api.reporte import SinRecursoError, medir
from compartido.constantes import AVISO_ALCANCE, CARPETA_SALIDAS, CLASES, CLASES_ES

DESCRIPCION = """
API de clasificación de imágenes satelitales **EuroSAT RGB 32×32** con revisión
humana. El modelo sugiere una categoría; una persona la acepta o la corrige y
ambas cosas quedan registradas por separado.

## Mapa de conexiones

| Origen | Verbo | Ruta | Efecto |
|---|---|---|---|
| Streamlit (`:8501`) | GET | `/health`, `/clases`, `/alcance` | estado y catálogo |
| Streamlit (`:8501`) | POST | `/predict` | top-3 + umbral · escribe `outputs/predicciones.csv` |
| Streamlit (`:8501`) | POST | `/decision` | aceptar/corregir · escribe `outputs/decisiones.csv` |
| Navegador | GET | `/reporte` | recorre la partición y **mide ahora** |
| Navegador | GET | `/panel` | tablero operativo (refresco 20 s) |

La interfaz nunca importa el modelo: solo HTTP + JSON. La API lee el checkpoint
`models/geoscene_cnn.pt` y, solo para `/reporte`, `splits/indices.json` y el
dataset. Nada se escribe en el checkpoint durante una consulta.

## Orígenes permitidos

CORS: variable `GEOSCENE_ORIGENES` (por defecto
`http://localhost:8501,http://127.0.0.1:8501`). Streamlit llama desde el
servidor; CORS aplica solo a clientes de navegador y se deja cerrado.

## Reglas del proyecto

Sin pesos preentrenados · particiones 500/100/100 por clase · validación para
elegir época y umbral · test solo como evidencia final.

## Documentación

`/docs` es Swagger UI con assets locales (funciona sin internet) y
`/openapi.json` es el contrato crudo que consume cualquier cliente.
`/panel` es el tablero operativo.
Ninguno de los dos lee `outputs/metricas_test.json`: todo se mide al consultar.
"""

ETIQUETAS = [
    {"name": "Sistema", "description": "Estado de la API y catálogo de clases."},
    {"name": "Predicción", "description": "Clasificación de una imagen con top-3 y umbral de revisión."},
    {"name": "Revisión humana", "description": "Aceptar o corregir una predicción, sin sobrescribirla."},
    {
        "name": "Observabilidad",
        "description": "Métricas calculadas en el momento de la consulta y panel operativo. No hay caché.",
    },
]

app = FastAPI(
    title="GeoScene AI · API de clasificación y observabilidad",
    version="1.3.0",
    docs_url=None,   # /docs se sirve abajo con Swagger UI local, sin CDN
    redoc_url=None,  # una sola interfaz: Swagger ya es ejecutable
    summary="EuroSAT RGB 32×32 · CNN propia · revisión humana · métricas en vivo",
    description=DESCRIPCION,
    openapi_tags=ETIQUETAS,
    contact={"name": "GeoScene AI · Deep Learning 2026"},
    license_info={"name": "Uso académico"},
)

ORIGENES = [
    origen.strip()
    for origen in os.getenv(
        "GEOSCENE_ORIGENES", "http://localhost:8501,http://127.0.0.1:8501"
    ).split(",")
    if origen.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGENES,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Swagger UI viaja con el proyecto: /docs funciona sin internet
app.mount(
    "/estaticos",
    StaticFiles(directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "estaticos")),
    name="estaticos",
)

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

    model_config = {
        "json_schema_extra": {
            "example": {
                "id_prediccion": "9f2c1ab34d0e",
                "categoria": "Forest",
                "confianza": 0.9412,
                "top3": [
                    {"categoria": "Forest", "confianza": 0.9412},
                    {"categoria": "HerbaceousVegetation", "confianza": 0.0321},
                    {"categoria": "AnnualCrop", "confianza": 0.0119},
                ],
                "requiere_revision": False,
                "umbral": 0.73,
                "tiempo_inferencia_ms": 0.24,
            }
        }
    }


class DecisionEntrada(BaseModel):
    id_prediccion: str
    categoria_humana: str


class DecisionSalida(BaseModel):
    id_prediccion: str
    categoria_modelo: str
    decision_humana: str
    estado: str  # "aceptada" o "corregida"


class MetaReporte(BaseModel):
    split: Literal["val", "test"]
    n_imagenes: int
    medido_en: str
    duracion_ms: float
    fuente: str
    parcial: bool
    version: str


class CapaModelo(BaseModel):
    capa: str
    parametros: int
    forma: list[int]


class Normalizacion(BaseModel):
    media: list[float]
    desviacion: list[float]


class ModeloInfo(BaseModel):
    checkpoint: str
    bytes: int
    epoca: int | None
    val_accuracy: float | None
    parametros: int
    parametros_entrenables: int
    macs: int
    flops: int
    entrada: list[int]
    canales: int
    capas: int
    arquitectura: list[CapaModelo]
    hiperparametros: dict[str, int | float] | None
    funcion_perdida: str
    optimizador: str
    plan_lr: str
    tasa_aprendizaje: float | None
    device: str
    torch: str
    umbral: float
    umbral_calibrado: bool
    objetivo_precision: float | None
    img_size: int
    clases: int
    normalizacion: Normalizacion


class MetricasReporte(BaseModel):
    accuracy: float
    top3: float
    top5: float
    perdida: float
    precision_macro: float
    recall_macro: float
    macro_f1: float
    f1_weighted: float
    confianza_media: float
    errores: int


class ClaseMetricas(BaseModel):
    precision: float
    recall: float
    f1: float
    soporte: int


class ConfusionReporte(BaseModel):
    clases: list[str]
    matriz: list[list[int]]


class ConfusionPar(BaseModel):
    real: str
    predicho: str
    veces: int


class ErrorAltaConfianza(BaseModel):
    real: str
    predicho: str
    confianza: float


class ReglaRevision(BaseModel):
    umbral: float
    cobertura: float
    porcentaje_marcadas: float
    accuracy_no_marcadas: float
    accuracy_marcadas: float


class BinCalibracion(BaseModel):
    rango: str
    n: int
    confianza: float
    accuracy: float


class Calibracion(BaseModel):
    """ECE, Brier y NLL miden si la confianza del softmax dice la verdad."""
    ece: float
    brier: float
    nll: float
    confianza_media: float
    confianza_mediana: float
    confianza_p10: float
    confianza_p90: float
    entropia_media: float
    fiabilidad: list[BinCalibracion]


class Latencia(BaseModel):
    ms_por_imagen_media: float
    ms_por_imagen_p50: float
    ms_por_imagen_p95: float
    ms_por_imagen_p99: float
    ms_por_imagen_lote: float
    ms_camino_completo_media: float
    imagenes_por_segundo: float
    muestra: int


class Particion(BaseModel):
    split: str
    n: int
    por_clase: dict[str, int]
    tamanos: dict[str, int]


class Artefacto(BaseModel):
    nombre: str
    ruta: str
    existe: bool
    bytes: int
    modificado: str | None


class PuntoBarrido(BaseModel):
    umbral: float
    cobertura: float
    accuracy_no_marcadas: float


class DecisionesReporte(BaseModel):
    predicciones_registradas: int
    decisiones_registradas: int
    aceptadas: int
    corregidas: int
    tasa_correccion: float
    ultima_decision: str | None


class SistemaReporte(BaseModel):
    uptime_s: float
    python: str
    torch: str
    device: str
    hilos_torch: int
    tamano_checkpoint_mb: float


class Reporte(BaseModel):
    meta: MetaReporte
    modelo: ModeloInfo
    metricas: MetricasReporte
    por_clase: dict[str, ClaseMetricas]
    confusion: ConfusionReporte
    top_confusiones: list[ConfusionPar]
    errores_alta_confianza: list[ErrorAltaConfianza]
    regla_revision: ReglaRevision
    calibracion: Calibracion
    barrido_umbral: list[PuntoBarrido]
    latencia: Latencia
    particion: Particion
    artefactos: list[Artefacto]
    decisiones: DecisionesReporte
    sistema: SistemaReporte

    model_config = {
        "json_schema_extra": {
            "example": {
                "meta": {
                    "split": "test",
                    "n_imagenes": 1000,
                    "medido_en": "2026-11-12T15:04:05",
                    "duracion_ms": 1840.2,
                    "fuente": "calculado_en_vivo_sin_cache",
                    "parcial": False,
                    "version": "1.3.0",
                },
                "modelo": {
                    "checkpoint": "models/geoscene_cnn.pt",
                    "epoca": 20,
                    "parametros": 545098,
                    "device": "cpu",
                    "torch": "2.15.0",
                    "umbral": 0.73,
                    "umbral_calibrado": True,
                    "img_size": 32,
                    "clases": 10,
                },
                "metricas": {
                    "accuracy": 0.827,
                    "top3": 0.975,
                    "top5": 0.996,
                    "perdida": 0.5055,
                    "precision_macro": 0.8312,
                    "recall_macro": 0.827,
                    "macro_f1": 0.8244,
                    "f1_weighted": 0.8244,
                    "confianza_media": 0.825,
                    "errores": 173,
                },
                "regla_revision": {
                    "umbral": 0.73,
                    "cobertura": 0.731,
                    "porcentaje_marcadas": 0.269,
                    "accuracy_no_marcadas": 0.9275,
                    "accuracy_marcadas": 0.5539,
                },
            }
        }
    }


@app.get("/", include_in_schema=False)
def raiz():
    """Abre el panel operativo."""
    return RedirectResponse(url="/panel")


@app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
def swagger():
    """Swagger UI con assets locales: el contrato ejecutable de esta API."""
    return HTMLResponse(content=PAGINA_DOCS, headers={"Cache-Control": "no-store"})


@app.get("/health", tags=["Sistema"], summary="Estado de la API (real o mock)")
def salud():
    return {"status": "ok", "modo": predictor.modo}


@app.get("/clases", tags=["Sistema"], summary="Las 10 clases de EuroSAT, en orden")
def clases():
    return {"clases": CLASES, "nombres_es": CLASES_ES}


@app.get("/alcance", tags=["Sistema"], summary="Aviso de alcance que muestra la interfaz")
def alcance():
    return {"aviso": AVISO_ALCANCE}


@app.post("/predict", response_model=Prediccion, tags=["Predicción"],
          summary="Clasifica una imagen y devuelve el top-3")
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


@app.post("/decision", response_model=DecisionSalida, tags=["Revisión humana"],
          summary="Acepta o corrige una predicción (sin sobrescribirla)")
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


@app.get("/reporte", response_model=Reporte, tags=["Observabilidad"],
         summary="Métricas recalculadas en cada consulta (sin caché)",
         responses={503: {"description": "Falta el checkpoint, las particiones o el dataset"}})
def reporte(
    response: Response,
    split: Literal["val", "test"] = Query("test", description="Partición a recorrer."),
    limite: int | None = Query(None, ge=1, le=5000,
                               description="Mide solo las primeras N imágenes (pruebas rápidas)."),
):
    """Carga el checkpoint, recorre la partición y devuelve todo medido ahora.

    No lee `outputs/metricas_test.json`: ese archivo es evidencia histórica. Aquí
    se vuelve a inferir sobre las imágenes en cada llamada.
    """
    response.headers["Cache-Control"] = "no-store"
    try:
        return medir(split, limite)
    except SinRecursoError as error:
        raise HTTPException(status_code=503, detail=str(error))


@app.get("/panel", response_class=HTMLResponse, tags=["Observabilidad"],
         summary="Centro de operaciones (autocontenido, refresco 20 s)")
def panel():
    """Tablero HTML: KPIs, F1 por clase, matriz, errores, decisiones y mapa."""
    return HTMLResponse(content=PAGINA, headers={"Cache-Control": "no-store"})
