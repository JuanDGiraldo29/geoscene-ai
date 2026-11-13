"""Pruebas del panel operativo, del reporte en vivo y de Swagger.

No recorren el dataset: la prueba de 503 sustituye la medición por un fallo
controlado, para que la suite siga siendo rápida y no dependa de data/.
"""
import hashlib

import pytest
from fastapi.testclient import TestClient

from api import main
from api.panel import PAGINA
from api.reporte import SinRecursoError


@pytest.fixture
def cliente():
    return TestClient(main.app)


def test_el_panel_sirve_el_centro_de_operaciones(cliente):
    respuesta = cliente.get("/panel")
    assert respuesta.status_code == 200
    assert "CENTRO DE OPERACIONES" in respuesta.text
    assert "/reporte" in respuesta.text


def test_el_panel_tiene_los_ids_que_usa_su_script():
    """El bug que dejó el panel a medias: kpi() buscaba un id que no existía."""
    for ident in ("kAccSub", "kF1Sub", "kTop3Sub", "kCobSub", "kSelSub", "kLatSub"):
        assert f'id="{ident}"' in PAGINA


def test_sin_checkpoint_el_reporte_da_503_con_motivo(cliente, monkeypatch):
    def falla(split="test", limite=None):
        raise SinRecursoError("Falta el checkpoint models/geoscene_cnn.pt")

    monkeypatch.setattr(main, "medir", falla)
    respuesta = cliente.get("/reporte")
    assert respuesta.status_code == 503
    assert "checkpoint" in respuesta.json()["detail"]


def test_swagger_se_sirve_con_assets_locales(cliente):
    respuesta = cliente.get("/docs")
    assert respuesta.status_code == 200
    assert "/estaticos/swagger-ui-bundle.js" in respuesta.text
    assert "cdn.jsdelivr" not in respuesta.text  # funciona sin internet
    assert cliente.get("/estaticos/swagger-ui.css").status_code == 200
    assert cliente.get("/redoc").status_code == 404  # una sola interfaz de documentación


def test_openapi_declara_procedencia_y_rutas(cliente):
    esquema = cliente.get("/openapi.json").json()
    assert "/reporte" in esquema["paths"]
    assert "/predict" in esquema["paths"]
    assert "/decision" in esquema["paths"]
    assert "Procedencia" in esquema["components"]["schemas"]
    assert "procedencia" in esquema["components"]["schemas"]["Reporte"]["properties"]


def test_openapi_no_se_cachea(cliente):
    respuesta = cliente.get("/openapi.json")
    assert respuesta.headers["cache-control"] == "no-store"


def test_el_panel_expone_la_seccion_de_procedencia():
    assert 'id="procedencia"' in PAGINA
    assert 'id="sello"' in PAGINA
    assert "PROCEDENCIA · CERTIFICACIÓN DE DATOS" in PAGINA
    assert "procedenciaContenido" in PAGINA


def test_el_panel_incluye_revelado_y_esqueletos():
    assert "IntersectionObserver" in PAGINA
    assert "MINIMO_ESQUELETO" in PAGINA
    assert "procedenciaContenido" in PAGINA


def test_la_huella_es_sha256_del_contenido(tmp_path):
    from api.reporte import _huella

    ruta = tmp_path / "evidencia.bin"
    ruta.write_bytes(b"geoscene")
    huella = _huella(str(ruta))
    assert huella["sha256"] == hashlib.sha256(b"geoscene").hexdigest()
    assert huella["bytes"] == 8
