"""Valores que usan TODAS las capas. Si algo cambia aquí, se avisa al grupo.

El orden de CLASES es el mismo que usa torchvision.datasets.EuroSAT
(orden alfabético). Si el entrenamiento y la API usan órdenes distintos,
el modelo acierta pero muestra la etiqueta equivocada.
"""

CLASES = [
    "AnnualCrop", "Forest", "HerbaceousVegetation", "Highway", "Industrial",
    "Pasture", "PermanentCrop", "Residential", "River", "SeaLake",
]

# Solo para mostrar en la interfaz
CLASES_ES = {
    "AnnualCrop": "Cultivo anual",
    "Forest": "Bosque",
    "HerbaceousVegetation": "Vegetación herbácea",
    "Highway": "Autopista",
    "Industrial": "Zona industrial",
    "Pasture": "Pastizal",
    "PermanentCrop": "Cultivo permanente",
    "Residential": "Zona residencial",
    "River": "Río",
    "SeaLake": "Mar o lago",
}

# Condiciones del taller
IMG_SIZE = 32
SEED = 42
POR_CLASE = {"train": 500, "val": 100, "test": 100}

# Rutas (las carpetas se crean al ejecutar el código)
CARPETA_DATOS = "data"
CARPETA_SALIDAS = "outputs"
RUTA_MODELO = "models/geoscene_cnn.pt"
RUTA_INDICES = "splits/indices.json"

AVISO_ALCANCE = (
    "Esta herramienta solo sugiere una de las 10 categorías de EuroSAT. "
    "Es una clasificación visual preliminar y no debe usarse sola para "
    "decisiones de ordenamiento territorial o ambientales. Una imagen fuera "
    "de estas categorías recibirá igualmente una de las 10 clases."
)
