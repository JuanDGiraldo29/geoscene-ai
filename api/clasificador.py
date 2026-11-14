"""El WRAPPER: la clase que consume el modelo entrenado.   Responsable: capa de consumo.

Recibe una imagen y devuelve una Respuesta con la forma definida en
compartido/contrato.py (puedes verificarla con comprobar_respuesta).
"""
import io
import os
import time
import warnings

import torch
from PIL import Image, UnidentifiedImageError

from compartido.constantes import RUTA_MODELO, TAMANO_MAXIMO_BYTES, TAMANO_MAXIMO_MB
from compartido.contrato import ClasificadorMock, leer_checkpoint
from compartido.preprocesamiento import crear_transformacion
from modelo.red import GeoSceneCNN


class ArchivoInvalidoError(ValueError):
    """El archivo no es una imagen válida. El mensaje se muestra a la persona usuaria."""


def cargar_imagen(contenido: bytes) -> Image.Image:
    """Convierte los bytes de un archivo en una imagen RGB, o lanza ArchivoInvalidoError."""
    if not contenido:
        raise ArchivoInvalidoError("El archivo está vacío.")
    if len(contenido) > TAMANO_MAXIMO_BYTES:
        raise ArchivoInvalidoError(f"El archivo pesa más de {TAMANO_MAXIMO_MB} MB.")

    try:
        imagen = Image.open(io.BytesIO(contenido))
        imagen.load()  # fuerza a leer toda la imagen: así se detectan los archivos corruptos
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        raise ArchivoInvalidoError("El archivo no es una imagen válida. Usa una imagen JPG o PNG.")

    return imagen.convert("RGB")  # unifica escala de grises, PNG con transparencia, etc.


class Clasificador:
    modo = "real"

    def __init__(self, ruta_checkpoint: str = RUTA_MODELO):
        ckpt = leer_checkpoint(ruta_checkpoint)

        self.modelo = GeoSceneCNN()
        self.modelo.load_state_dict(ckpt["state_dict"])
        self.modelo.eval()  # desactiva el dropout: sin esto las predicciones serían aleatorias

        self.transformacion = crear_transformacion(ckpt["media"], ckpt["desviacion"])
        self.clases = ckpt["clases"]
        self.umbral = ckpt["umbral"]

        if not ckpt.get("umbral_calibrado"):
            warnings.warn("El umbral del checkpoint no está calibrado con validación.")

    def predecir(self, imagen: Image.Image) -> dict:
        inicio = time.perf_counter()

        x = self.transformacion(imagen.convert("RGB")).unsqueeze(0)  # añade la dimensión de lote
        with torch.no_grad():
            probabilidades = torch.softmax(self.modelo(x), dim=1)[0]

        tiempo_ms = (time.perf_counter() - inicio) * 1000

        valores, posiciones = probabilidades.topk(3)
        top3 = [
            {"categoria": self.clases[int(i)], "confianza": round(float(v), 4)}
            for v, i in zip(valores, posiciones)
        ]
        confianza = top3[0]["confianza"]

        return {
            "categoria": top3[0]["categoria"],
            "confianza": confianza,
            "top3": top3,
            "requiere_revision": confianza < self.umbral,
            "umbral": self.umbral,
            "tiempo_inferencia_ms": round(tiempo_ms, 2),
        }


def crear_predictor():
    """Usa el modelo real si ya existe el checkpoint; si no, el mock."""
    if os.path.exists(RUTA_MODELO):
        return Clasificador(RUTA_MODELO)
    return ClasificadorMock()