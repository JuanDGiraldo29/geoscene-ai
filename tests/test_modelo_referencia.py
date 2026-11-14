"""Certifica que el checkpoint versionado es el modelo de referencia.

El checkpoint debe ser exactamente el de `feature/juanda`: CNN de dos bloques
(32/64 canales, sin BatchNorm), 545.098 parámetros, época 20, umbral 0.73.
No recorre el dataset ni mide métricas; solo verifica identidad y arquitectura
para que un reemplazo accidental no pase desapercibido.
"""
import hashlib
from pathlib import Path

import pytest
from torch import nn

from compartido.constantes import RUTA_MODELO
from compartido.contrato import leer_checkpoint
from modelo.red import GeoSceneCNN

SHA256_REFERENCIA = "e073084ab5c7633b21f80d72a84612adc801cb5663f3672faab340acd58de571"


def test_el_checkpoint_es_el_modelo_de_referencia():
    ckpt = leer_checkpoint(RUTA_MODELO)
    modelo = GeoSceneCNN()
    modelo.load_state_dict(ckpt["state_dict"])

    assert ckpt["epoca"] == 20
    assert ckpt["val_accuracy"] == pytest.approx(0.807)
    assert ckpt["umbral"] == pytest.approx(0.73)
    assert ckpt["umbral_calibrado"] is True

    assert sum(p.numel() for p in modelo.parameters()) == 545_098
    assert not any(isinstance(capa, nn.BatchNorm2d) for capa in modelo.modules())

    assert ckpt["state_dict"]["convolucionales.0.weight"].shape == (32, 3, 3, 3)
    assert ckpt["state_dict"]["convolucionales.3.weight"].shape == (64, 32, 3, 3)
    assert ckpt["state_dict"]["clasificador.1.weight"].shape == (128, 64 * 8 * 8)


def test_la_huella_del_checkpoint_coincide_con_la_documentada():
    huella = hashlib.sha256(Path(RUTA_MODELO).read_bytes()).hexdigest()
    assert huella == SHA256_REFERENCIA
