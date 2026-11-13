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
    assert list(dataset.classes) == CLASES, f"Las clases no coinciden: {dataset.classes}"
    return dataset


def crear_particiones(etiquetas):
    """Devuelve {"train": [...índices...], "val": [...], "test": [...]}, balanceadas por clase."""
    etiquetas = np.array(etiquetas)
    rng = np.random.default_rng(SEED)
    particiones = {nombre: [] for nombre in POR_CLASE}

    for clase in range(len(CLASES)):
        indices = rng.permutation(np.flatnonzero(etiquetas == clase))  # índices de la clase, mezclados
        inicio = 0
        for nombre, cantidad in POR_CLASE.items():
            particiones[nombre].extend(indices[inicio:inicio + cantidad].tolist())
            inicio += cantidad

    # Comprobaciones: sin repetidos entre particiones y tamaños correctos
    todos = [i for lista in particiones.values() for i in lista]
    assert len(todos) == len(set(todos)), "Hay imágenes repetidas entre particiones"
    for nombre, cantidad in POR_CLASE.items():
        assert len(particiones[nombre]) == cantidad * len(CLASES)
    return particiones


def guardar_indices(particiones):
    """Guarda las particiones en RUTA_INDICES como JSON."""
    os.makedirs(os.path.dirname(RUTA_INDICES), exist_ok=True)
    with open(RUTA_INDICES, "w") as archivo:
        json.dump(particiones, archivo)


def cargar_indices():
    """Lee RUTA_INDICES y devuelve el diccionario con train, val y test."""
    with open(RUTA_INDICES) as archivo:
        return json.load(archivo)

if __name__ == "__main__":
    dataset = cargar_eurosat(transform=crear_transformacion())
    if os.path.exists(RUTA_INDICES):
        print(f"Ya existen {RUTA_INDICES}. No se rehacen: se crean una sola vez.")
    else:
        particiones = crear_particiones(dataset.targets)
        guardar_indices(particiones)
        print({nombre: len(idx) for nombre, idx in particiones.items()})
