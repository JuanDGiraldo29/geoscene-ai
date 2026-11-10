"""PASO 3 · Entrenamiento.   Responsable: integrante 1 (con apoyo del 2).

Entregable: models/geoscene_cnn.pt (se sube a GitHub cuando sea el modelo final).

Cómo se ejecuta:
    python -m modelo.entrenar

Cambios respecto al script del curso (FashionMNIST):
  1. Además de entrenar, se mide en VALIDACIÓN al final de cada época.
  2. Se elige la mejor época con la validación (nunca con el test).
  3. Se guarda el mejor modelo con guardar_checkpoint (compartido/contrato.py).
  4. El test NO se toca en este archivo.
"""
import random

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Subset

from compartido.constantes import RUTA_MODELO, SEED
from compartido.contrato import guardar_checkpoint
from compartido.preprocesamiento import crear_transformacion
from modelo.datos import cargar_eurosat, cargar_indices
from modelo.red import GeoSceneCNN


def fijar_semillas():
    """Para que los resultados sean repetibles."""
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)


def calcular_media_desviacion(cargador):
    """Media y desviación por canal (R, G, B) calculadas SOLO con train.

    TODO 1: recorrer el cargador (imágenes sin normalizar) y acumular
            - la suma de los valores por canal   -> x.sum(dim=(0, 2, 3))
            - la suma de los cuadrados           -> (x ** 2).sum(dim=(0, 2, 3))
            - el número total de píxeles por canal (batch * alto * ancho)
            Media = suma / n.   Desviación = raíz de (suma_cuadrados / n - media**2).
            Devuelve dos listas de 3 números.
    """
    raise NotImplementedError("TODO 1")


def entrenar_una_epoca(modelo, cargador, funcion_perdida, optimizador):
    """TODO 2: es la función train_epoch que ya hicieron en el curso
    (model.train(), predicción, loss, zero_grad, backward, step).
    Devuelve (pérdida_promedio, accuracy)."""
    raise NotImplementedError("TODO 2")


def evaluar_una_epoca(modelo, cargador, funcion_perdida):
    """TODO 3: igual que la anterior pero SIN actualizar pesos:
        - modelo.eval()
        - dentro de `with torch.no_grad():`
        - sin optimizador, sin backward
    Devuelve (pérdida_promedio, accuracy)."""
    raise NotImplementedError("TODO 3")


def main():
    fijar_semillas()
    indices = cargar_indices()

    # TODO 4: media y desviación de train
    #   - dataset sin normalizar: cargar_eurosat(crear_transformacion())
    #   - Subset(dataset, indices["train"]) -> DataLoader -> calcular_media_desviacion
    media, desviacion = None, None

    # TODO 5: DataLoaders de train (shuffle=True) y validación,
    #         esta vez con la transformación NORMALIZADA: crear_transformacion(media, desviacion)
    cargador_train, cargador_val = None, None

    # TODO 6: modelo = GeoSceneCNN(), funcion_perdida = nn.CrossEntropyLoss(),
    #         optimizador = torch.optim.Adam(...)  (como en el curso)
    modelo, funcion_perdida, optimizador = None, None, None

    # TODO 7: bucle de épocas. En cada una:
    #     - entrenar_una_epoca(...)  y  evaluar_una_epoca(...) con validación
    #     - guardar los números en listas (para las gráficas) y mostrarlos con print
    #     - si el accuracy de VALIDACIÓN es el mejor hasta ahora, guardar el modelo:
    #           guardar_checkpoint(RUTA_MODELO, modelo, media, desviacion, epoca=epoca)
    #       (el umbral se calibra después, en modelo/evaluar.py)
    raise NotImplementedError("TODO 4 a 7")

    # TODO 8: gráficas de pérdida y accuracy (train vs validación) guardadas en outputs/.
    #         Anoten la época elegida y los hiperparámetros: van en la ficha ejecutiva.


if __name__ == "__main__":
    main()
