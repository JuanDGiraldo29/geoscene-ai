"""PASO 2 · La red neuronal.   Responsable: integrantes 1 y 2 (la deciden juntos).

Esta es la clase que el wrapper (carpeta api/) importa para reconstruir el
modelo, así que se llama GeoSceneCNN y su constructor NO debe pedir argumentos
obligatorios (si agregan hiperparámetros, que tengan valor por defecto).

Es la CNN base del curso: dos bloques convolucionales y una parte final que
clasifica. En el curso usaron nn.Linear sobre 28x28; aquí la entrada es
3 canales (RGB) de 32x32 y la salida son 10 valores (uno por clase).

Esta es la arquitectura de referencia del proyecto (32 y 64 canales, 545.098
parámetros). En `feature/johan` existe una variante experimental con el doble
de canales y BatchNorm2d (64/128, 4,3 M de parámetros); su comparación y la
justificación de BatchNorm están documentadas en el README. El checkpoint
versionado en `models/geoscene_cnn.pt` corresponde a esta clase.
"""
import torch
from torch import nn

from compartido.constantes import CLASES


class GeoSceneCNN(nn.Module):

    def __init__(self):
        super().__init__()

        # Bloques convolucionales: extraen patrones visuales (bordes, texturas, formas)
        self.convolucionales = nn.Sequential(
            # Bloque 1: 3 canales (RGB) -> 32 mapas de características.  32x32 -> 16x16
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),

            # Bloque 2: 32 -> 64 mapas de características.  16x16 -> 8x8
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
        )

        # Parte final: convierte los mapas en 10 valores, uno por clase
        self.clasificador = nn.Sequential(
            nn.Flatten(),                   # 64 x 8 x 8 -> 4096 números
            nn.Linear(64 * 8 * 8, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, len(CLASES)),    # 10 salidas (logits)
        )

    def forward(self, x):
        # Devuelve los valores crudos (logits). NO se aplica softmax aquí:
        # CrossEntropyLoss ya lo incluye.
        x = self.convolucionales(x)
        return self.clasificador(x)


if __name__ == "__main__":
    modelo = GeoSceneCNN()
    salida = modelo(torch.zeros(4, 3, 32, 32))
    print(salida.shape)  # torch.Size([4, 10])
