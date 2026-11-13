"""Pruebas del panel operativo, del reporte en vivo y de Swagger.

No recorren el dataset: la prueba de 503 sustituye la medición por un fallo
controlado, para que la suite siga siendo rápida y no dependa de data/.
"""
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
