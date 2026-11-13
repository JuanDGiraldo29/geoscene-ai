"""Pruebas del wrapper. No dependen del modelo entrenado: usan un checkpoint de pesos aleatorios."""
import io

import pytest
from PIL import Image

from api.clasificador import ArchivoInvalidoError, Clasificador, cargar_imagen
from compartido.contrato import comprobar_respuesta, guardar_checkpoint
from modelo.red import GeoSceneCNN


def bytes_de(modo="RGB", formato="PNG", tamano=(64, 64)):
    buffer = io.BytesIO()
    Image.new(modo, tamano).save(buffer, format=formato)
    return buffer.getvalue()


@pytest.fixture
def clasificador(tmp_path):
    ruta = str(tmp_path / "modelo.pt")
    guardar_checkpoint(ruta, GeoSceneCNN(), [0.3, 0.3, 0.3], [0.2, 0.2, 0.2],
                       umbral=0.7, umbral_calibrado=True)
    return Clasificador(ruta)


@pytest.mark.parametrize("modo", ["RGB", "L", "RGBA"])
def test_la_respuesta_cumple_el_contrato(clasificador, modo):
    comprobar_respuesta(clasificador.predecir(Image.new(modo, (64, 64))))


def test_misma_imagen_misma_respuesta(clasificador):
    imagen = Image.new("RGB", (64, 64), (10, 120, 30))
    assert clasificador.predecir(imagen)["top3"] == clasificador.predecir(imagen)["top3"]


def test_cargar_imagen_valida_devuelve_rgb():
    assert cargar_imagen(bytes_de("L", "PNG")).mode == "RGB"
    assert cargar_imagen(bytes_de("RGB", "JPEG")).mode == "RGB"


@pytest.mark.parametrize("contenido", [
    b"",                                  # vacío
    b"esto es texto, no una imagen",      # no es imagen
    bytes_de()[:60],                      # imagen cortada
    b"0" * (11 * 1024 * 1024),            # más de 10 MB
])
def test_archivos_invalidos(contenido):
    with pytest.raises(ArchivoInvalidoError):
        cargar_imagen(contenido)