"""El límite de subida debe ser el mismo en la interfaz y en la API.

Si Streamlit anuncia un límite distinto al que aplica la API, la persona
usuaria sube un archivo que la interfaz acepta y la API rechaza con un mensaje
contradictorio ("200 MB por archivo" frente a "pesa más de 10 MB").
"""
import re
from pathlib import Path

import pytest

from api.clasificador import ArchivoInvalidoError, cargar_imagen
from compartido.constantes import TAMANO_MAXIMO_BYTES, TAMANO_MAXIMO_MB

RAIZ = Path(__file__).resolve().parent.parent


def test_el_limite_es_de_10_mb():
    assert TAMANO_MAXIMO_MB == 10
    assert TAMANO_MAXIMO_BYTES == 10 * 1024 * 1024


def test_streamlit_anuncia_el_mismo_limite():
    texto = (RAIZ / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    encontrado = re.search(r"^\s*maxUploadSize\s*=\s*(\d+)\s*$", texto, re.MULTILINE)
    assert encontrado, "Falta server.maxUploadSize en .streamlit/config.toml"
    assert int(encontrado.group(1)) == TAMANO_MAXIMO_MB


def test_la_interfaz_usa_el_limite_compartido():
    texto = (RAIZ / "interfaz" / "app.py").read_text(encoding="utf-8")
    assert "TAMANO_MAXIMO_BYTES" in texto
    assert "TAMANO_MAXIMO_MB" in texto


def test_el_mensaje_de_error_cita_el_limite_real():
    with pytest.raises(ArchivoInvalidoError) as error:
        cargar_imagen(b"0" * (TAMANO_MAXIMO_BYTES + 1))
    assert f"{TAMANO_MAXIMO_MB} MB" in str(error.value)


def test_un_archivo_justo_en_el_limite_no_se_rechaza_por_tamano():
    # 10 MB exactos pasan el filtro de tamaño; fallan después porque no son
    # una imagen válida, así que el mensaje ya no es el del tamaño.
    with pytest.raises(ArchivoInvalidoError) as error:
        cargar_imagen(b"0" * TAMANO_MAXIMO_BYTES)
    assert "MB" not in str(error.value)
