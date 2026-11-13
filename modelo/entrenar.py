"""PASO 3 · Entrenamiento.   Responsable: integrante 1 (con apoyo del 2).

Entregable: models/geoscene_cnn.pt (se sube a GitHub cuando sea el modelo final).

Cómo se ejecuta:
    python -m modelo.entrenar
"""
import os
import random

import matplotlib
matplotlib.use("Agg")  # dibuja sin abrir ventanas: guarda la figura en un archivo
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset

from compartido.constantes import (
    CARPETA_SALIDAS,
    FUNCION_PERDIDA,
    OPTIMIZADOR,
    PLAN_LR,
    RUTA_MODELO,
    SEED,
)
from compartido.contrato import guardar_checkpoint
from compartido.preprocesamiento import crear_transformacion
from modelo.datos import cargar_eurosat, cargar_indices
from modelo.red import GeoSceneCNN

# Hiperparámetros: anótenlos, van en la ficha ejecutiva
EPOCAS = 20
TASA_APRENDIZAJE = 0.001
TAMANO_LOTE = 64
DECAIMIENTO_PESOS = 1e-4


def fijar_semillas():
    """Para que los resultados sean repetibles."""
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def calcular_media_desviacion(cargador):
    """Media y desviación por canal (R, G, B) calculadas SOLO con train."""
    suma = torch.zeros(3)
    suma_cuadrados = torch.zeros(3)
    total_pixeles = 0

    for X, _ in cargador:
        suma += X.sum(dim=(0, 2, 3))                 # suma por canal
        suma_cuadrados += (X ** 2).sum(dim=(0, 2, 3))
        total_pixeles += X.shape[0] * X.shape[2] * X.shape[3]

    media = suma / total_pixeles
    desviacion = (suma_cuadrados / total_pixeles - media ** 2).sqrt()
    return media.tolist(), desviacion.tolist()


def entrenar_una_epoca(modelo, cargador, funcion_perdida, optimizador):
    """Una pasada completa por train, actualizando los pesos. Devuelve (pérdida, accuracy)."""
    modelo.train()
    perdida_total, aciertos, total = 0, 0, 0

    for X, y in cargador:
        prediccion = modelo(X)
        perdida = funcion_perdida(prediccion, y)

        optimizador.zero_grad()
        perdida.backward()
        optimizador.step()

        perdida_total += perdida.item()
        aciertos += (prediccion.argmax(1) == y).sum().item()
        total += y.size(0)

    return perdida_total / len(cargador), aciertos / total


def evaluar_una_epoca(modelo, cargador, funcion_perdida):
    """Una pasada por validación SIN actualizar pesos. Devuelve (pérdida, accuracy)."""
    modelo.eval()
    perdida_total, aciertos, total = 0, 0, 0

    with torch.no_grad():
        for X, y in cargador:
            prediccion = modelo(X)
            perdida_total += funcion_perdida(prediccion, y).item()
            aciertos += (prediccion.argmax(1) == y).sum().item()
            total += y.size(0)

    return perdida_total / len(cargador), aciertos / total


def graficar(historial, mejor_epoca):
    """Curvas de pérdida y accuracy: train vs validación."""
    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    epocas = range(1, len(historial["train_perdida"]) + 1)
    figura, ejes = plt.subplots(1, 2, figsize=(10, 4))

    for eje, metrica, titulo in [(ejes[0], "perdida", "Pérdida"), (ejes[1], "accuracy", "Accuracy")]:
        eje.plot(epocas, historial[f"train_{metrica}"], label="train")
        eje.plot(epocas, historial[f"val_{metrica}"], label="validación")
        eje.axvline(mejor_epoca, linestyle="--", color="gray", label="época elegida")
        eje.set_title(titulo)
        eje.set_xlabel("Época")
        eje.legend()

    figura.tight_layout()
    ruta = os.path.join(CARPETA_SALIDAS, "curvas_entrenamiento.png")
    figura.savefig(ruta, dpi=120)
    print(f"Gráfica guardada en {ruta}")


def main():
    fijar_semillas()
    indices = cargar_indices()

    # Media y desviación de train (con imágenes SIN normalizar y SIN giros)
    dataset_crudo = cargar_eurosat(crear_transformacion())
    cargador_crudo = DataLoader(Subset(dataset_crudo, indices["train"]), batch_size=256)
    media, desviacion = calcular_media_desviacion(cargador_crudo)
    print("Media por canal:", [round(v, 4) for v in media])
    print("Desviación por canal:", [round(v, 4) for v in desviacion])

    # Train lleva giros aleatorios; validación NO (se evalúa con las imágenes tal cual)
    dataset_train = cargar_eurosat(crear_transformacion(media, desviacion, aumentar=True))
    dataset_val = cargar_eurosat(crear_transformacion(media, desviacion))
    generador = torch.Generator().manual_seed(SEED)  # mezcla repetible en cada época
    cargador_train = DataLoader(Subset(dataset_train, indices["train"]), batch_size=TAMANO_LOTE,
                                shuffle=True, generator=generador)
    cargador_val = DataLoader(Subset(dataset_val, indices["val"]), batch_size=TAMANO_LOTE)

    modelo = GeoSceneCNN()
    funcion_perdida = nn.CrossEntropyLoss()
    optimizador = torch.optim.Adam(modelo.parameters(), lr=TASA_APRENDIZAJE, weight_decay=DECAIMIENTO_PESOS)

    historial = {"train_perdida": [], "train_accuracy": [], "val_perdida": [], "val_accuracy": []}
    mejor_accuracy, mejor_epoca = 0.0, 0

    for epoca in range(1, EPOCAS + 1):
        tp, ta = entrenar_una_epoca(modelo, cargador_train, funcion_perdida, optimizador)
        vp, va = evaluar_una_epoca(modelo, cargador_val, funcion_perdida)

        historial["train_perdida"].append(tp)
        historial["train_accuracy"].append(ta)
        historial["val_perdida"].append(vp)
        historial["val_accuracy"].append(va)

        marca = ""
        if va > mejor_accuracy:  # el mejor modelo se elige con VALIDACIÓN
            mejor_accuracy, mejor_epoca = va, epoca
            guardar_checkpoint(
                RUTA_MODELO, modelo, media, desviacion,
                epoca=epoca, val_accuracy=va,
                hiperparametros={"epocas": EPOCAS, "lr": TASA_APRENDIZAJE, "lote": TAMANO_LOTE,
                                 "weight_decay": DECAIMIENTO_PESOS,
                                 "optimizador": OPTIMIZADOR,
                                 "funcion_perdida": FUNCION_PERDIDA,
                                 "plan_lr": PLAN_LR},
            )
            marca = "  <- mejor hasta ahora, guardado"

        print(f"Época {epoca:2d} | train: pérdida={tp:.4f} acc={ta*100:.2f}% "
              f"| val: pérdida={vp:.4f} acc={va*100:.2f}%{marca}")

    print(f"\nMejor época: {mejor_epoca} (accuracy de validación: {mejor_accuracy*100:.2f}%)")
    print(f"Modelo guardado en {RUTA_MODELO}")
    graficar(historial, mejor_epoca)


if __name__ == "__main__":
    main()