"""PASO 1 · Datos y particiones.   Responsable: integrante 1.

Entregable: el archivo splits/indices.json, que se sube a GitHub para que todo
el equipo (y el docente) use exactamente las mismas imágenes.

Cómo se ejecuta (desde la carpeta raíz del proyecto):
    python -m modelo.datos

Reglas de la guía:
  - 10 clases, 500 imágenes por clase para train, 100 para validación y 100 para test.
  - Semilla 42, sin imágenes repetidas entre particiones.
  - Las particiones se crean UNA sola vez y se guardan.
"""
import json
import os

import numpy as np
from torchvision import datasets

from compartido.constantes import CARPETA_DATOS, CLASES, POR_CLASE, RUTA_INDICES, SEED
from compartido.preprocesamiento import crear_transformacion


def cargar_eurosat(transform=None):
    """Devuelve el dataset EuroSAT completo (RGB, 27.000 imágenes)."""
    dataset = datasets.EuroSAT(root=CARPETA_DATOS, download=True, transform=transform)
    assert list(dataset.classes) == CLASES, (
        f"El orden de clases de torchvision cambió: {dataset.classes}"
    )
    return dataset


def crear_particiones(etiquetas):
    """Recibe la lista de etiquetas (dataset.targets) y devuelve
    {"train": [...índices...], "val": [...], "test": [...]}."""
    etiquetas = np.asarray(etiquetas)
    rng = np.random.default_rng(SEED)
    particiones = {"train": [], "val": [], "test": []}

    for clase in range(len(CLASES)):
        idx_clase = np.flatnonzero(etiquetas == clase)
        idx_clase = rng.permutation(idx_clase)
        n_train = POR_CLASE["train"]
        n_val = POR_CLASE["val"]
        n_test = POR_CLASE["test"]
        assert len(idx_clase) >= n_train + n_val + n_test, (
            f"La clase {CLASES[clase]} tiene solo {len(idx_clase)} imágenes"
        )
        particiones["train"].extend(idx_clase[:n_train].tolist())
        particiones["val"].extend(idx_clase[n_train:n_train + n_val].tolist())
        particiones["test"].extend(idx_clase[n_train + n_val:n_train + n_val + n_test].tolist())

    # Sin repetidos entre particiones y con el tamaño exacto por clase
    todos = particiones["train"] + particiones["val"] + particiones["test"]
    assert len(todos) == len(set(todos)), "Hay índices repetidos entre particiones"
    for nombre, idx in particiones.items():
        assert len(idx) == POR_CLASE[nombre] * len(CLASES), (
            f"{nombre} tiene {len(idx)} imágenes, se esperaban {POR_CLASE[nombre] * len(CLASES)}"
        )
    return {k: [int(i) for i in v] for k, v in particiones.items()}


def guardar_indices(particiones):
    """Guarda el diccionario en RUTA_INDICES como JSON (una sola vez)."""
    os.makedirs(os.path.dirname(RUTA_INDICES), exist_ok=True)
    with open(RUTA_INDICES, "w", encoding="utf-8") as f:
        json.dump(particiones, f)


def cargar_indices():
    """Lee RUTA_INDICES y devuelve el diccionario con train, val y test."""
    with open(RUTA_INDICES, encoding="utf-8") as f:
        particiones = json.load(f)
    return {nombre: [int(i) for i in idx] for nombre, idx in particiones.items()}


if __name__ == "__main__":
    dataset = cargar_eurosat(transform=crear_transformacion())
    if os.path.exists(RUTA_INDICES):
        print(f"Ya existen {RUTA_INDICES}. No se rehacen: se crean una sola vez.")
    else:
        particiones = crear_particiones(dataset.targets)
        guardar_indices(particiones)
        print({nombre: len(idx) for nombre, idx in particiones.items()})
