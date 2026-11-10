"""PASO 4 · Umbral de revisión y evaluación final.   Responsable: integrante 2.

Cómo se ejecuta:
    python -m modelo.evaluar --split val      # define el umbral (se puede repetir)
    python -m modelo.evaluar --split test     # evaluación final: UNA sola vez

REGLA DE ORO: el test solo se usa al final, con el modelo ya elegido.
No lo usen para comparar configuraciones.

Entregables (carpeta outputs/, para la ficha ejecutiva):
  accuracy global, macro F1, matriz de confusión, resultados por clase,
  tres errores reales, una confusión frecuente y el tiempo de inferencia.
"""
import argparse

import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from compartido.constantes import RUTA_MODELO
from compartido.contrato import leer_checkpoint
from modelo.datos import cargar_eurosat, cargar_indices
from modelo.red import GeoSceneCNN


def cargar_modelo():
    """Reconstruye la red con los pesos guardados."""
    ckpt = leer_checkpoint(RUTA_MODELO)
    modelo = GeoSceneCNN()
    modelo.load_state_dict(ckpt["state_dict"])
    modelo.eval()
    return modelo, ckpt


def obtener_probabilidades(modelo, ckpt, nombre_particion):
    """TODO 1: devolver (probabilidades, etiquetas_reales) de una partición ("val" o "test").
      - dataset = cargar_eurosat(crear_transformacion(ckpt["media"], ckpt["desviacion"]))
      - Subset con cargar_indices()[nombre_particion] y un DataLoader
      - con torch.no_grad(): softmax de las salidas del modelo
    """
    raise NotImplementedError("TODO 1")


def calibrar_umbral(confianzas, aciertos):
    """TODO 2: decidir con VALIDACIÓN a partir de qué confianza conviene revisar.

    Idea: probar umbrales de 0.30 a 0.99. Para cada uno calcular
      - cobertura: qué fracción de imágenes NO se marcan para revisión
      - accuracy de las imágenes no marcadas
    Elegir el umbral más bajo cuyo accuracy de las no marcadas llegue a un
    objetivo que justifiquen (por ejemplo 90 %). Guardar la gráfica
    umbral vs cobertura/accuracy: es la evidencia que pide la guía.
    Escribir el umbral elegido en el checkpoint (leer_checkpoint -> cambiar
    ckpt["umbral"] -> torch.save).
    """
    raise NotImplementedError("TODO 2")


def evaluar_test(modelo, ckpt):
    """TODO 3: calcular y guardar en outputs/
      - accuracy_score y f1_score(average="macro")
      - classification_report (resultados por clase) y confusion_matrix
      - la confusión más frecuente (la celda más alta fuera de la diagonal)
      - tres errores reales: imágenes mal clasificadas, con su clase real y la predicha
      - tiempo de inferencia: medir con time.perf_counter() varias predicciones y promediar
    """
    raise NotImplementedError("TODO 3")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["val", "test"], required=True)
    args = parser.parse_args()

    modelo, ckpt = cargar_modelo()
    if args.split == "val":
        probs, reales = obtener_probabilidades(modelo, ckpt, "val")
        calibrar_umbral(probs.max(axis=1), probs.argmax(axis=1) == reales)
    else:
        evaluar_test(modelo, ckpt)
