# Contrato entre las capas

Es el acuerdo que permite trabajar en paralelo. Si algo de aquí cambia, se
avisa al grupo y se actualiza este archivo en el mismo cambio.

## 1. El checkpoint (entrenamiento → wrapper)

Archivo `models/geoscene_cnn.pt`, creado SIEMPRE con `guardar_checkpoint` de
`compartido/contrato.py`. Contiene:

| Clave | Qué es |
|---|---|
| `state_dict` | Pesos de la red `GeoSceneCNN` (de `modelo/red.py`) |
| `clases` | Lista de las 10 clases, en el orden del entrenamiento |
| `media`, `desviacion` | Normalización por canal, calculada solo con train |
| `umbral` | Confianza por debajo de la cual se recomienda revisar (se define con validación) |

## 2. La respuesta del clasificador (wrapper → API)

`Clasificador.predecir(imagen)` devuelve exactamente:

```json
{
  "categoria": "Forest",
  "confianza": 0.91,
  "top3": [
    {"categoria": "Forest", "confianza": 0.91},
    {"categoria": "HerbaceousVegetation", "confianza": 0.06},
    {"categoria": "Pasture", "confianza": 0.02}
  ],
  "requiere_revision": false,
  "umbral": 0.76,
  "tiempo_inferencia_ms": 1.4
}
```

- `top3` va de mayor a menor y su primer elemento es `categoria`.
- Las confianzas están entre 0 y 1 (salida softmax del modelo).
- `requiere_revision` es `confianza < umbral`.
- Se verifica con `comprobar_respuesta` (en `compartido/contrato.py`).

## 3. Los endpoints (API → interfaz)

| Método y ruta | Entrada | Respuesta |
|---|---|---|
| `GET /health` | | `{"status": "ok", "modo": "mock"}` (`modo` es `mock` o `real`) |
| `GET /clases` | | `{"clases": [...10 clases...], "nombres_es": {...}}` |
| `GET /alcance` | | `{"aviso": "texto del aviso de alcance"}` |
| `POST /predict` | archivo en el campo `file` | la respuesta del punto 2 más `"id_prediccion"` |
| `POST /decision` | `{"id_prediccion": "...", "categoria_humana": "Pasture"}` | ver abajo |

Respuesta de `POST /decision`:

```json
{
  "id_prediccion": "5e9089961a4d",
  "categoria_modelo": "Forest",
  "decision_humana": "Pasture",
  "estado": "corregida"
}
```
`estado` es `aceptada` si la persona eligió la misma clase que el modelo y
`corregida` si eligió otra. La predicción original nunca se modifica.

Códigos de error (el cuerpo es `{"detail": "mensaje para mostrar"}`):

| Código | Cuándo |
|---|---|
| 400 | Archivo vacío, corrupto o que no es una imagen; o categoría que no es una de las 10 |
| 404 | No existe ese `id_prediccion` |
| 409 | Esa predicción ya tiene una decisión registrada |
| 422 | No se envió el archivo (lo genera FastAPI) |
