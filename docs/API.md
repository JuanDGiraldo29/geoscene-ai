# API, documentación y centro de operaciones

La fuente de verdad del contrato es OpenAPI, generado por FastAPI desde el
código: no hay un documento escrito a mano que se pueda desincronizar.

| Recurso | URL | Para qué |
|---|---|---|
| Swagger UI | `/docs` | contrato navegable y **ejecutable** (assets locales, sin internet) |
| OpenAPI crudo | `/openapi.json` | importar a Postman, generar clientes, validar |
| Panel operativo | `/panel` | tablero en vivo, no es documentación |

`/docs` viaja con el proyecto (`api/estaticos/swagger-ui-bundle.js` y
`swagger-ui.css`, versión 5.17.14), así que se abre igual sin conexión.

## Mapa de conexiones

```
 Navegador / docente            Streamlit (:8501)                API (:8000)
        │                            │                              │
        │  GET /docs /panel          │  GET /health /clases         │
        ├──────────────────────────► │  GET /alcance                │
                                     │  POST /predict  ─────────────┤──► modelo (.pt)
                                     │  POST /decision ─────────────┤──► outputs/*.csv
                                     │                              │
        GET /reporte ────────────────────────────────────────────────┤──► checkpoint
        GET /panel                                                   │──► indices + data/
                                                                     └──► outputs/*.csv
```

La interfaz nunca importa el modelo: solo HTTP + JSON. El checkpoint lo leen la
API y el reporte; nadie lo escribe durante una consulta.

## Endpoints

| Verbo | Ruta | Consumidor | Qué hace | Errores |
|---|---|---|---|---|
| GET | `/health` | Streamlit | modo `real` o `mock` | — |
| GET | `/clases` | Streamlit | 10 clases + nombres en español | — |
| GET | `/alcance` | Streamlit | aviso de alcance del modelo | — |
| POST | `/predict` | Streamlit | imagen → categoría, confianza, top-3, umbral; escribe `outputs/predicciones.csv` | 400 archivo inválido, 422 sin archivo |
| POST | `/decision` | Streamlit | acepta o corrige; escribe `outputs/decisiones.csv` | 400 clase inválida, 404 id desconocido, 409 ya decidida |
| GET | `/reporte` | panel, docente | recorre `val` o `test` y mide **en ese momento** todo lo de la tabla de abajo | 503 sin checkpoint, particiones o dataset; 422 parámetros inválidos |
| GET | `/panel` | navegador | tablero operativo (refresco 20 s) | — |
| GET | `/docs`, `/openapi.json` | docente | contrato navegable y ejecutable | — |

### `/reporte`

Parámetros: `split=val|test` (por defecto `test`) y `limite=1..5000`.

| Bloque | Contenido |
|---|---|
| `meta` | partición, nº de imágenes, hora con milisegundos, duración del cálculo, `fuente: calculado_en_vivo_sin_cache`, `parcial` si se usó `limite` |
| `modelo` | checkpoint, bytes, época, `val_accuracy`, parámetros totales y entrenables, MACs y FLOPs de una inferencia 32×32, forma de entrada, nº de capas y arquitectura por tensor, función de pérdida, optimizador, `plan_lr`, `tasa_aprendizaje`, hiperparámetros, dispositivo, torch, umbral, `objetivo_precision`, normalización |
| `metricas` | pérdida (CrossEntropyLoss), accuracy (top-1), top-3, top-5, precisión/recall macro, F1 macro y ponderado, confianza media, nº de errores |
| `por_clase` | precisión, recall, F1 y soporte de las 10 clases |
| `confusion` | matriz 10×10 y etiquetas |
| `top_confusiones` | pares real → predicho más frecuentes |
| `errores_alta_confianza` | los 3 errores con mayor confianza (los que más engañan) |
| `regla_revision` | umbral, cobertura, % marcadas, accuracy de marcadas y no marcadas |
| `calibracion` | ECE (10 bins), Brier multiclase, log-loss, confianza media/mediana/p10/p90, entropía y tabla de fiabilidad por bin |
| `barrido_umbral` | qué pasaría con la regla en umbrales 0.50–0.95 |
| `latencia` | media, p50, p95, p99, ms/imagen en lote, throughput y camino completo (decodificar JPEG + modelo) |
| `particion` | tamaños de train/val/test y balance por clase |
| `artefactos` | `outputs/*.png` y `metricas_test.json`: si existen, bytes y fecha |
| `decisiones` | aceptadas, corregidas, tasa de corrección y última decisión |
| `sistema` | uptime, Python, torch, device, hilos, tamaño del checkpoint |

Los MACs/FLOPs se cuentan con ganchos sobre cada convolución y capa lineal durante
una inferencia de prueba, no son un valor escrito a mano. La tasa de aprendizaje
es constante (`Adam`, `lr = 1e-3`, 20 épocas) y no hay scheduler: el panel muestra
una línea plana en lugar de una curva de decaimiento inventada.

Envía `Cache-Control: no-store`. **No lee `outputs/metricas_test.json`**: ese
archivo es evidencia histórica; aquí se vuelve a inferir sobre las imágenes.

```bash
curl -s "http://localhost:8000/reporte?split=test" | python -m json.tool
curl -s "http://localhost:8000/reporte?split=val&limite=200" | python -m json.tool
```

## Orígenes y puertos

| Origen | Puerto | Destino | Nota |
|---|---|---|---|
| Streamlit | 8501 | API 8000 | `GEOSCENE_API_URL` en `interfaz/app.py` |
| Navegador | cualquiera | API 8000 | CORS limitado a `GEOSCENE_ORIGENES` |

`GEOSCENE_ORIGENES` (coma-separado) por defecto:
`http://localhost:8501,http://127.0.0.1:8501`. Streamlit llama desde el servidor,
así que CORS solo aplica a clientes de navegador; se deja explícito para que no
se abra a cualquier origen.

## Cómo correrlo

```bash
uvicorn api.main:app --reload --port 8000
# otra terminal
streamlit run interfaz/app.py
```

- Swagger: <http://localhost:8000/docs>
- Panel: <http://localhost:8000/panel>

## Límites conocidos

- Sin autenticación: es una demo local, no un servicio público.
- `/reporte` recorre la partición completa (1000 imágenes) y cronometra 100 + 50
  imágenes: menos de un segundo en CPU, pero no es un endpoint de milisegundos.
  Usa `limite` para pruebas rápidas y recuerda que entonces `parcial` es `true`.
- Medir `test` muchas veces no cambia el modelo, pero el test sigue siendo
  evidencia de evaluación, no de ajuste.
- La calibración (ECE) es descriptiva: no se aplica temperature scaling para no
  alterar el umbral ya calibrado con validación.
