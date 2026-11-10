"""PASO 2 · La red neuronal.   Responsable: integrantes 1 y 2 (la deciden juntos).

Esta es la clase que el wrapper (carpeta api/) importa para reconstruir el
modelo, así que se llama GeoSceneCNN y su constructor NO debe pedir argumentos
obligatorios (si agregan hiperparámetros, que tengan valor por defecto).

Es la CNN base del curso: dos bloques convolucionales y una parte final que
clasifica. En el curso usaron nn.Linear sobre 28x28; aquí la entrada es
3 canales (RGB) de 32x32 y la salida son 10 valores (uno por clase).
"""
from torch import nn

from compartido.constantes import CLASES


class GeoSceneCNN(nn.Module):

    def __init__(self):
        super().__init__()

        # TODO 1: bloques convolucionales. Cada bloque suele ser:
        #     nn.Conv2d(canales_entrada, canales_salida, kernel_size=3, padding=1),
        #     nn.ReLU(),
        #     nn.MaxPool2d(2)
        #   Bloque 1: entra con 3 canales (RGB).   32x32 -> 16x16
        #   Bloque 2: entra con los canales del bloque 1.   16x16 -> 8x8
        self.convolucionales = None

        # TODO 2: parte final: nn.Flatten() y una o más nn.Linear.
        #   Ojo: el tamaño de entrada de la primera Linear es
        #   (canales del bloque 2) * 8 * 8. Debe terminar con len(CLASES) salidas.
        self.clasificador = None

    def forward(self, x):
        # TODO 3: pasar x por las convolucionales y luego por el clasificador.
        #   Devuelve los valores crudos (logits). NO apliques softmax aquí:
        #   CrossEntropyLoss ya lo incluye.
        raise NotImplementedError("TODO 3")
