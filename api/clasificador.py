"""El WRAPPER: la clase que consume el modelo entrenado.   Responsable: capa de consumo.

Recibe una imagen y devuelve una Respuesta con la forma definida en
compartido/contrato.py (puedes verificarla con comprobar_respuesta).
"""
import io
import os

from PIL import Image, UnidentifiedImageError

from compartido.constantes import RUTA_MODELO
from compartido.contrato import ClasificadorMock, leer_checkpoint  # noqa: F401
from compartido.preprocesamiento import crear_transformacion  # noqa: F401
from modelo.red import GeoSceneCNN  # noqa: F401


class ArchivoInvalidoError(ValueError):
    """El archivo no es una imagen válida. El mensaje se muestra a la persona usuaria."""


def cargar_imagen(contenido: bytes) -> Image.Image:
    """Convierte los bytes de un archivo en una imagen RGB.

    TODO 1: lanzar ArchivoInvalidoError con un mensaje claro si
            - contenido está vacío
            - Image.open(io.BytesIO(contenido)) falla (captura UnidentifiedImageError)
            - pesa más de 10 MB
            Al final devuelve la imagen con .convert("RGB") (maneja escala de grises, PNG con alfa...).
    """
    raise NotImplementedError("TODO 1")


class Clasificador:
    modo = "real"

    def __init__(self, ruta_checkpoint: str = RUTA_MODELO):
        """TODO 2: cargar el modelo entrenado.
          - ckpt = leer_checkpoint(ruta_checkpoint)
          - self.modelo = GeoSceneCNN(); load_state_dict(ckpt["state_dict"]); .eval()
          - self.transformacion = crear_transformacion(ckpt["media"], ckpt["desviacion"])
          - guardar self.clases = ckpt["clases"] y self.umbral = ckpt["umbral"]
        .eval() es importante: desactiva dropout y fija el comportamiento de BatchNorm.
        """
        raise NotImplementedError("TODO 2")

    def predecir(self, imagen: Image.Image) -> dict:
        """TODO 3: devolver el diccionario del contrato.
          - medir el tiempo con time.perf_counter() (solo transformación + modelo)
          - x = self.transformacion(imagen)  y agregar la dimensión de batch con .unsqueeze(0)
          - con torch.no_grad(): probabilidades = torch.softmax(self.modelo(x), dim=1)[0]
          - los tres mayores con probabilidades.topk(3)
          - requiere_revision = confianza < self.umbral
        Prueba tu resultado con comprobar_respuesta(...) de compartido/contrato.py.
        """
        raise NotImplementedError("TODO 3")


def crear_predictor():
    """Usa el modelo real si ya existe el checkpoint; si no, el mock."""
    if os.path.exists(RUTA_MODELO):
        return Clasificador(RUTA_MODELO)
    return ClasificadorMock()
