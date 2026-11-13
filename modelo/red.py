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
        x = self.convolucionales(x)
        return self.clasificador(x)