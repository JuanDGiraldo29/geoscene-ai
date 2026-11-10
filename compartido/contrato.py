"""El CONTRATO entre las tres capas. Esto ya está hecho para que nadie espere a nadie.

Contiene:
  1. La forma de la respuesta del clasificador (y comprobar_respuesta para verificarla).
  2. El formato del checkpoint: guardar_checkpoint (lo usa entrenamiento) y
     leer_checkpoint (lo usa el wrapper).
  3. ClasificadorMock: un clasificador falso con la misma respuesta que el real,
     para que API e interfaz avancen antes de que exista el modelo entrenado.
"""
import hashlib
import os
from typing import TypedDict

import numpy as np
import torch

from compartido.constantes import CLASES

# ---------------------------------------------------------------- 1. Respuesta

class Puntuacion(TypedDict):
    categoria: str
    confianza: float


class Respuesta(TypedDict):
    categoria: str               # clase con mayor puntuación
    confianza: float             # entre 0 y 1 (softmax)
    top3: list[Puntuacion]       # de mayor a menor; el primero es `categoria`
    requiere_revision: bool      # confianza < umbral
    umbral: float                # calculado con VALIDACIÓN
    tiempo_inferencia_ms: float  # solo preprocesamiento + modelo


def comprobar_respuesta(r: dict) -> None:
    """Lanza AssertionError si la respuesta no cumple el contrato."""
    assert set(r) == set(Respuesta.__annotations__), f"Claves distintas: {sorted(r)}"
    assert r["categoria"] in CLASES
    assert len(r["top3"]) == 3
    confianzas = [p["confianza"] for p in r["top3"]]
    assert confianzas == sorted(confianzas, reverse=True)
    assert all(0 <= c <= 1 for c in confianzas)
    assert r["top3"][0]["categoria"] == r["categoria"]
    assert r["requiere_revision"] == (r["confianza"] < r["umbral"])


# --------------------------------------------------------------- 2. Checkpoint

CLAVES_CHECKPOINT = {"state_dict", "clases", "media", "desviacion", "umbral"}


def guardar_checkpoint(ruta, modelo, media, desviacion, umbral=0.5, **extra):
    """Lo llama el entrenamiento. `extra` sirve para guardar época, hiperparámetros, etc."""
    carpeta = os.path.dirname(ruta)
    if carpeta:
        os.makedirs(carpeta, exist_ok=True)
    torch.save({
        "state_dict": modelo.state_dict(),
        "clases": CLASES,
        "media": list(media),
        "desviacion": list(desviacion),
        "umbral": float(umbral),
        **extra,
    }, ruta)


def leer_checkpoint(ruta) -> dict:
    """Lo llama el wrapper. Avisa con claridad si falta algo."""
    ckpt = torch.load(ruta, map_location="cpu", weights_only=True)
    faltan = CLAVES_CHECKPOINT - set(ckpt)
    if faltan:
        raise ValueError(f"Al checkpoint le faltan claves: {sorted(faltan)}")
    return ckpt


# ----------------------------------------------------------------------- 3. Mock

class ClasificadorMock:
    """Misma respuesta que el clasificador real, pero inventada y repetible."""
    modo = "mock"

    def __init__(self, umbral: float = 0.6):
        self.clases = list(CLASES)
        self.umbral = umbral

    def predecir(self, imagen) -> Respuesta:
        semilla = int(hashlib.md5(imagen.convert("RGB").tobytes()).hexdigest()[:8], 16)
        logits = np.random.default_rng(semilla).normal(size=len(self.clases)) * 2.5
        probs = np.exp(logits) / np.exp(logits).sum()
        orden = np.argsort(probs)[::-1][:3]
        top3 = [{"categoria": self.clases[i], "confianza": round(float(probs[i]), 4)} for i in orden]
        return {
            "categoria": top3[0]["categoria"],
            "confianza": top3[0]["confianza"],
            "top3": top3,
            "requiere_revision": top3[0]["confianza"] < self.umbral,
            "umbral": self.umbral,
            "tiempo_inferencia_ms": 0.1,
        }
