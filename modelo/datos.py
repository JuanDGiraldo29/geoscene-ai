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
    """Devuelve el dataset EuroSAT completo (RGB, 27.000 imágenes).

    TODO 1: usar datasets.EuroSAT(root=CARPETA_DATOS, download=True, transform=transform)
            (igual que hicieron con FashionMNIST en el curso).
    TODO 2: comprobar que dataset.classes == CLASES (mismo orden que compartido/constantes.py).
    """
    raise NotImplementedError("TODO 1 y 2")


def crear_particiones(etiquetas):
    """Recibe la lista de etiquetas (dataset.targets) y devuelve
    {"train": [...índices...], "val": [...], "test": [...]}.

    TODO 3: para cada clase
              - buscar los índices de esa clase (np.flatnonzero(etiquetas == clase))
              - mezclarlos con np.random.default_rng(SEED).permutation(...)
              - repartir: los primeros 500 a train, los siguientes 100 a val, los siguientes 100 a test
    TODO 4: comprobar con assert que
              - no hay índices repetidos entre particiones
              - cada partición tiene POR_CLASE[nombre] * 10 imágenes
    """
    raise NotImplementedError("TODO 3 y 4")


def guardar_indices(particiones):
    """TODO 5: guardar el diccionario en RUTA_INDICES como JSON
    (crear la carpeta con os.makedirs(..., exist_ok=True); los índices deben ser int de Python)."""
    raise NotImplementedError("TODO 5")


def cargar_indices():
    """TODO 6: leer RUTA_INDICES y devolver el diccionario con train, val y test.
    Se usa luego con torch.utils.data.Subset(dataset, indices['train'])."""
    raise NotImplementedError("TODO 6")


if __name__ == "__main__":
    dataset = cargar_eurosat(transform=crear_transformacion())
    if os.path.exists(RUTA_INDICES):
        print(f"Ya existen {RUTA_INDICES}. No se rehacen: se crean una sola vez.")
    else:
        particiones = crear_particiones(dataset.targets)
        guardar_indices(particiones)
        print({nombre: len(idx) for nombre, idx in particiones.items()})
