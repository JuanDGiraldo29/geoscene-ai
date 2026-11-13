"""Pruebas de la API. Usan el mock y una carpeta temporal: no tocan el modelo real ni outputs/."""
import csv
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from api import main
from compartido.contrato import ClasificadorMock, comprobar_respuesta


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "CARPETA_SALIDAS", str(tmp_path))
    monkeypatch.setattr(main, "RUTA_PREDICCIONES", str(tmp_path / "predicciones.csv"))
    monkeypatch.setattr(main, "RUTA_DECISIONES", str(tmp_path / "decisiones.csv"))
    monkeypatch.setattr(main, "predictor", ClasificadorMock())
    monkeypatch.setattr(main, "PREDICCIONES", {})
    monkeypatch.setattr(main, "DECISIONES", set())
    return TestClient(main.app)


def imagen_png():
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), (20, 100, 50)).save(buffer, format="PNG")
    return buffer.getvalue()


def predecir(cliente):
    return cliente.post("/predict", files={"file": ("img.png", imagen_png())}).json()


def filas(ruta):
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def test_health_y_clases(cliente):
    assert cliente.get("/health").json() == {"status": "ok", "modo": "mock"}
    assert len(cliente.get("/clases").json()["clases"]) == 10


def test_predict_cumple_el_contrato_y_se_registra(cliente, tmp_path):
    respuesta = predecir(cliente)
    id_prediccion = respuesta.pop("id_prediccion")
    comprobar_respuesta(respuesta)
    registro = filas(tmp_path / "predicciones.csv")
    assert len(registro) == 1 and registro[0]["id_prediccion"] == id_prediccion


def test_archivo_invalido_da_400_con_mensaje(cliente):
    r = cliente.post("/predict", files={"file": ("x.txt", b"no soy una imagen")})
    assert r.status_code == 400 and "imagen" in r.json()["detail"]


def test_sin_archivo_da_422(cliente):
    assert cliente.post("/predict").status_code == 422


def test_aceptar_una_prediccion(cliente):
    pred = predecir(cliente)
    r = cliente.post("/decision", json={"id_prediccion": pred["id_prediccion"],
                                        "categoria_humana": pred["categoria"]})
    assert r.status_code == 200 and r.json()["estado"] == "aceptada"


def test_corregir_deja_prediccion_y_decision_separadas(cliente, tmp_path):
    pred = predecir(cliente)
    otra = next(c for c in cliente.get("/clases").json()["clases"] if c != pred["categoria"])
    r = cliente.post("/decision", json={"id_prediccion": pred["id_prediccion"], "categoria_humana": otra})
    assert r.json()["estado"] == "corregida"
    assert r.json()["categoria_modelo"] == pred["categoria"]
    # La predicción original sigue intacta y la decisión vive en otro archivo
    assert filas(tmp_path / "predicciones.csv")[0]["categoria_modelo"] == pred["categoria"]
    assert filas(tmp_path / "decisiones.csv")[0]["decision_humana"] == otra


def test_errores_de_decision(cliente):
    pred = predecir(cliente)
    assert cliente.post("/decision", json={"id_prediccion": "no-existe",
                                           "categoria_humana": pred["categoria"]}).status_code == 404
    assert cliente.post("/decision", json={"id_prediccion": pred["id_prediccion"],
                                           "categoria_humana": "Luna"}).status_code == 400
    ok = {"id_prediccion": pred["id_prediccion"], "categoria_humana": pred["categoria"]}
    assert cliente.post("/decision", json=ok).status_code == 200
    assert cliente.post("/decision", json=ok).status_code == 409  # ya decidida