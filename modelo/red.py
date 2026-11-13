"""PASO 2 · La red neuronal.   Responsable: integrantes 1 y 2 (la deciden juntos).

Esta es la clase que el wrapper (carpeta api/) importa para reconstruir el
modelo, así que se llama GeoSceneCNN y su constructor NO debe pedir argumentos
obligatorios (si agregan hiperparámetros, que tengan valor por defecto).

Es la CNN base del curso: dos bloques convolucionales y una parte final que
clasifica. En el curso usaron nn.Linear sobre 28x28; aquí la entrada es
3 canales (RGB) de 32x32 y la salida son 10 valores (uno por clase).
"""
import torch
from torch import nn

from compartido.constantes import CLASES


class GeoSceneCNN(nn.Module):

    def __init__(self, canales=(64, 128), neuronas_ocultas=512, dropout=0.4):
        super().__init__()

        # Bloque 1: 3 canales (RGB).   32x32 -> 16x16
        # Bloque 2: 64 canales.        16x16 ->  8x8
        c1, c2 = canales
        self.convolucionales = nn.Sequential(
            nn.Conv2d(3, c1, kernel_size=3, padding=1),
            nn.BatchNorm2d(c1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(c1, c2, kernel_size=3, padding=1),
            nn.BatchNorm2d(c2),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

        # Parte final: c2 * 8 * 8 -> oculta -> 10 clases
        self.clasificador = nn.Sequential(
            nn.Flatten(),
            nn.Linear(c2 * 8 * 8, neuronas_ocultas),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(neuronas_ocultas, len(CLASES)),
        )

    def forward(self, x):
        # Devuelve los valores crudos (logits). NO se aplica softmax aquí:
        # CrossEntropyLoss ya lo incluye.
        return self.clasificador(self.convolucionales(x))


if __name__ == "__main__":
    modelo = GeoSceneCNN()
    salida = modelo(torch.zeros(4, 3, 32, 32))
    print(salida.shape)  # torch.Size([4, 10])
