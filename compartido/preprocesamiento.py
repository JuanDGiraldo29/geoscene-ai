"""Transformación de imágenes COMPARTIDA entre entrenamiento y la app.

Si el entrenamiento y la app transforman distinto las imágenes, el modelo da
malas predicciones sin lanzar ningún error. Por eso hay una sola función.
"""
import torch
from torchvision.transforms import v2

from compartido.constantes import IMG_SIZE


def crear_transformacion(media=None, desviacion=None, augmentar=False):
    """Imagen (PIL) -> tensor 3 x 32 x 32. Normaliza solo si se dan media y desviación.

    augmentar=True agrega volteos y rotación. SOLO se usa en el entrenamiento;
    la validación, el test y la app siempre usan augmentar=False (porque una
    imagen de entrada nunca debe modificarse al predecir).
    """
    pasos = [
        v2.ToImage(),
        v2.Resize((IMG_SIZE, IMG_SIZE)),
        v2.ToDtype(torch.float32, scale=True),
    ]
    if augmentar:
        pasos += [
            v2.RandomHorizontalFlip(),
            v2.RandomVerticalFlip(),
            v2.RandomRotation(15, fill=0.5),
        ]
    if media is not None:
        pasos.append(v2.Normalize(mean=media, std=desviacion))
    return v2.Compose(pasos)
