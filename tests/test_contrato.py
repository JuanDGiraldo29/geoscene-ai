"""Pruebas del contrato. Se ejecutan con:  python -m pytest

Cada capa puede añadir aquí sus propias pruebas (por ejemplo, el wrapper real
con comprobar_respuesta cuando esté listo).
"""
import pytest
import torch
from PIL import Image
from torch import nn

from compartido.constantes import CLASES
from compartido.contrato import (
    ClasificadorMock, comprobar_respuesta, guardar_checkpoint, leer_checkpoint,
)


@pytest.mark.parametrize("tamano", [(64, 64), (32, 32), (300, 200)])
def test_mock_cumple_el_contrato(tamano):
    comprobar_respuesta(ClasificadorMock().predecir(Image.new("RGB", tamano, (10, 90, 40))))


def test_mock_es_repetible():
    img = Image.new("RGB", (64, 64), (200, 10, 10))
    assert ClasificadorMock().predecir(img) == ClasificadorMock().predecir(img)


def test_checkpoint_ida_y_vuelta(tmp_path):
    ruta = str(tmp_path / "modelo.pt")
    guardar_checkpoint(ruta, nn.Linear(2, 2), [0.1, 0.2, 0.3], [0.4, 0.5, 0.6], umbral=0.7, epoca=3)
    ckpt = leer_checkpoint(ruta)
    assert ckpt["clases"] == CLASES and ckpt["umbral"] == 0.7 and ckpt["epoca"] == 3


def test_checkpoint_incompleto_avisa(tmp_path):
    ruta = tmp_path / "malo.pt"
    torch.save({"state_dict": {}}, ruta)
    with pytest.raises(ValueError, match="faltan claves"):
        leer_checkpoint(ruta)
