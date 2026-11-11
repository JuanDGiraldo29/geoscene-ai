"""PASO 3 · Entrenamiento.   Responsable: integrante 1 (con apoyo del 2).

Entregable: models/geoscene_cnn.pt (se sube a GitHub cuando sea el modelo final).

Cómo se ejecuta:
    python -m modelo.entrenar

Cambios respecto al script del curso (FashionMNIST):
  1. Además de entrenar, se mide en VALIDACIÓN al final de cada época.
  2. Se elige la mejor época con la validación (nunca con el test).
  3. Se guarda el mejor modelo con guardar_checkpoint (compartido/contrato.py).
  4. El test NO se toca en este archivo.
  5. Detección temprana (early stopping): si la validación no mejora durante
     PACIENCIA épocas seguidas, se corta el entrenamiento y se queda el mejor
     checkpoint. Así se evita seguir entrenando de más (sobreajuste).
"""
import os
import random
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset

from compartido.constantes import CARPETA_SALIDAS, RUTA_MODELO, SEED
from compartido.contrato import guardar_checkpoint
from compartido.preprocesamiento import crear_transformacion
from modelo.datos import cargar_eurosat, cargar_indices
from modelo.red import GeoSceneCNN

# ------------------------------------------------------------- Hiperparámetros
EPOCAS_MAX = 60        # tope de épocas
PACIENCIA = 10         # early stopping: épocas sin mejorar en validación
MIN_MEJORA = 1e-4      # mejora mínima para considerar que hubo avance
TAM_LOTE = 64
FACTOR_APRENDIZAJE = 1e-3
PESO_DECAY = 1e-4        # regularización L2: frena el sobreajuste


def fijar_semillas():
    """Para que los resultados sean repetibles."""
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def calcular_media_desviacion(cargador):
    """Media y desviación por canal (R, G, B) calculadas SOLO con train."""
    suma = torch.zeros(3)
    suma_cuadrados = torch.zeros(3)
    n_pixeles = 0
    for x, _ in cargador:
        suma += x.sum(dim=(0, 2, 3))
        suma_cuadrados += (x ** 2).sum(dim=(0, 2, 3))
        n_pixeles += x.shape[0] * x.shape[2] * x.shape[3]
    media = suma / n_pixeles
    desviacion = torch.sqrt(suma_cuadrados / n_pixeles - media ** 2)
    return media.tolist(), desviacion.tolist()


def entrenar_una_epoca(modelo, cargador, funcion_perdida, optimizador):
    """Época de entrenamiento. Devuelve (pérdida_promedio, accuracy)."""
    modelo.train()
    perdida_total = 0.0
    aciertos = 0
    n = 0
    for x, y in cargador:
        optimizador.zero_grad()
        logits = modelo(x)
        perdida = funcion_perdida(logits, y)
        perdida.backward()
        optimizador.step()
        perdida_total += perdida.item() * y.shape[0]
        aciertos += (logits.argmax(dim=1) == y).sum().item()
        n += y.shape[0]
    return perdida_total / n, aciertos / n


def evaluar_una_epoca(modelo, cargador, funcion_perdida):
    """Evaluación SIN actualizar pesos. Devuelve (pérdida_promedio, accuracy)."""
    modelo.eval()
    perdida_total = 0.0
    aciertos = 0
    n = 0
    with torch.no_grad():
        for x, y in cargador:
            logits = modelo(x)
            perdida = funcion_perdida(logits, y)
            perdida_total += perdida.item() * y.shape[0]
            aciertos += (logits.argmax(dim=1) == y).sum().item()
            n += y.shape[0]
    return perdida_total / n, aciertos / n


def graficar_historial(historial):
    """Gráficas de pérdida y accuracy (train vs validación) en outputs/."""
    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    epocas = range(1, len(historial["train_perdida"]) + 1)

    fig, ejes = plt.subplots(1, 2, figsize=(11, 4))
    ejes[0].plot(epocas, historial["train_perdida"], label="train")
    ejes[0].plot(epocas, historial["val_perdida"], label="val")
    ejes[0].set_title("Pérdida")
    ejes[0].set_xlabel("Época")
    ejes[0].legend()

    ejes[1].plot(epocas, historial["train_acc"], label="train")
    ejes[1].plot(epocas, historial["val_acc"], label="val")
    ejes[1].set_title("Accuracy")
    ejes[1].set_xlabel("Época")
    ejes[1].legend()

    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_SALIDAS, "curvas_entrenamiento.png"), dpi=120)
    plt.close(fig)


def main():
    fijar_semillas()
    indices = cargar_indices()

    # Media y desviación de train (dataset sin normalizar)
    dataset_crudo = cargar_eurosat(crear_transformacion())
    media, desviacion = calcular_media_desviacion(
        DataLoader(Subset(dataset_crudo, indices["train"]), batch_size=TAM_LOTE, shuffle=False)
    )
    print(f"Media por canal: {[round(m, 4) for m in media]}")
    print(f"Desviación por canal: {[round(d, 4) for d in desviacion]}")

    # DataLoaders con la transformación NORMALIZADA.
    # El train además usa augmentar=True (volteos y rotación) para que el
    # modelo generalice mejor; val nunca se aumenta.
    dataset_train = cargar_eurosat(crear_transformacion(media, desviacion, augmentar=True))
    dataset_val = cargar_eurosat(crear_transformacion(media, desviacion))
    cargador_train = DataLoader(
        Subset(dataset_train, indices["train"]), batch_size=TAM_LOTE, shuffle=True
    )
    cargador_val = DataLoader(
        Subset(dataset_val, indices["val"]), batch_size=TAM_LOTE, shuffle=False
    )

    modelo = GeoSceneCNN(canales=(64, 128), neuronas_ocultas=512, dropout=0.4)
    funcion_perdida = nn.CrossEntropyLoss()
    optimizador = torch.optim.Adam(
        modelo.parameters(), lr=FACTOR_APRENDIZAJE, weight_decay=PESO_DECAY
    )
    # Baja el LR si la val deja de mejorar: ayuda a afinar sin pasarse
    planificador = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizador, mode="max", factor=0.5, patience=2
    )

    historial = {"train_perdida": [], "val_perdida": [], "train_acc": [], "val_acc": []}
    mejor_acc_val = -1.0
    mejor_epoca = 0
    epocas_sin_mejora = 0

    for epoca in range(1, EPOCAS_MAX + 1):
        inicio = time.perf_counter()
        perdida_train, acc_train = entrenar_una_epoca(
            modelo, cargador_train, funcion_perdida, optimizador
        )
        perdida_val, acc_val = evaluar_una_epoca(modelo, cargador_val, funcion_perdida)
        planificador.step(acc_val)
        tiempo = time.perf_counter() - inicio
        lr_actual = optimizador.param_groups[0]["lr"]

        historial["train_perdida"].append(perdida_train)
        historial["val_perdida"].append(perdida_val)
        historial["train_acc"].append(acc_train)
        historial["val_acc"].append(acc_val)

        print(
            f"Época {epoca:02d} | "
            f"train loss {perdida_train:.4f} acc {acc_train:.4f} | "
            f"val loss {perdida_val:.4f} acc {acc_val:.4f} | "
            f"lr {lr_actual:.1e} | "
            f"{tiempo:.1f}s"
        )

        # Mejor modelo según VALIDACIÓN (nunca según test)
        if acc_val > mejor_acc_val + MIN_MEJORA:
            mejor_acc_val = acc_val
            mejor_epoca = epoca
            epocas_sin_mejora = 0
            guardar_checkpoint(
                RUTA_MODELO, modelo, media, desviacion,
                epoca=epoca,
                acc_val=acc_val,
                hiperparametros={
                    "canales": [64, 128],
                    "neuronas_ocultas": 512,
                    "dropout": 0.4,
                    "epocas_max": EPOCAS_MAX,
                    "paciencia": PACIENCIA,
                    "tam_lote": TAM_LOTE,
                    "lr": FACTOR_APRENDIZAJE,
                    "weight_decay": PESO_DECAY,
                    "optimizador": "Adam",
                    "augmentar_train": True,
                    "seed": SEED,
                },
            )
        else:
            epocas_sin_mejora += 1
            print(f"   sin mejora en val ({epocas_sin_mejora}/{PACIENCIA})")
            if epocas_sin_mejora >= PACIENCIA:
                print(f"Early stopping en la época {epoca}.")
                break

    graficar_historial(historial)
    print(
        f"Mejor época: {mejor_epoca} con accuracy de validación {mejor_acc_val:.4f}. "
        f"Checkpoint guardado en {RUTA_MODELO}"
    )


if __name__ == "__main__":
    main()
