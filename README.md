# GeoScene AI

Clasificador de imágenes satelitales con revisión humana. El modelo mira una
imagen de 32×32 píxeles y sugiere una de las 10 categorías de EuroSAT; una
persona acepta o corrige esa sugerencia. Ambas cosas quedan registradas por
separado.

Es el proyecto final de Deep Learning 2026, Reto A. La aplicación ya está
completa y se puede ejecutar de punta a punta: interfaz, API, modelo entrenado,
métricas medidas en vivo y trazabilidad de los archivos que producen esas
métricas.

> **En una frase:** subes una imagen, el modelo propone, tú decides y todo queda
> auditable.

## La idea en 30 segundos

1. **Subes** una imagen satelital desde la interfaz.
2. **El modelo clasifica** y muestra la categoría sugerida, su confianza y el
   top-3. Si la confianza queda por debajo del umbral de revisión, la interfaz
   lo advierte.
3. **Tú decides**: aceptas la sugerencia o eliges la categoría correcta.
4. **La API guarda** la predicción y la decisión en archivos distintos. Corregir
   no reentrena ni sobrescribe la predicción original.

La interfaz nunca importa el modelo: habla con la API por HTTP y JSON. La API es
la única que carga el checkpoint. Esa separación permite reemplazar el modelo o
la pantalla sin tocar la otra pieza.

```
interfaz/ (Streamlit)  ──HTTP/JSON──►  api/ (FastAPI)  ──►  models/geoscene_cnn.pt
                                              │
                                              ├──►  outputs/predicciones.csv
                                              ├──►  outputs/decisiones.csv
                                              └──►  /reporte, /panel, /docs
```

## Ficha técnica (resumen)

| Campo | Valor |
|---|---|
| Proyecto | GeoScene AI · clasificación de cobertura del suelo |
| Reto | Deep Learning 2026, Reto A |
| Tarea | Clasificación multiclase de imágenes satelitales |
| Dataset | EuroSAT RGB, 27.000 imágenes, 10 clases |
| Entrada del modelo | RGB 32×32, normalizada con media y desviación de train |
| Arquitectura | CNN propia de dos bloques convolucionales (32 y 64 canales), sin pesos preentrenados |
| Salida | 10 logits → softmax; categoría, confianza y top-3 |
| Particiones | 5.000 train / 1.000 validación / 1.000 test (500/100/100 por clase) |
| Semilla | 42 |
| Checkpoint | `models/geoscene_cnn.pt` (época 20, 545.098 parámetros) |
| Umbral de revisión | 0,73, calibrado solo con validación |
| Métricas finales | Accuracy 82,7 % · macro F1 82,44 % · top-3 97,5 % |
| Stack | PyTorch, FastAPI, Streamlit, Swagger UI local |
| Artefactos versionados | Checkpoint, índices de particiones y código; `data/` y `outputs/` no se suben |

## Cómo se usa

La pantalla principal tiene tres pasos visibles: **subir → clasificar →
decidir**.

- Al subir una imagen, se muestra de inmediato. El resultado aparece con un
  esqueleto de carga mientras la API responde, para que la interfaz no parezca
  congelada.
- La tarjeta de predicción muestra la categoría, la confianza, el umbral, el
  top-3 con barras y una advertencia cuando hace falta revisar.
- La tarjeta de decisión separa visualmente **predicción del modelo** y
  **decisión humana**, y confirma si fue aceptada o corregida.
- El botón **Clasificar otra imagen** limpia el estado y permite empezar de
  nuevo sin recargar la página.

Si la API arranca sin checkpoint, funciona en **modo mock**: sirve para probar
la interfaz y el contrato, pero las predicciones no son reales. La cabecera y la
barra lateral siempre indican el modo activo.

## Cómo correrlo

Esta guía asume que ya descargaste el repositorio y que estás en la rama
**`integracion/completa`**, que es la que contiene el modelo de referencia
(CNN 32/64 canales, 545.098 parámetros, sin `BatchNorm2d`) y su checkpoint
versionado. Todos los comandos se ejecutan **desde la raíz del repositorio**, la
carpeta que contiene `api/`, `modelo/`, `interfaz/` y `requirements.txt`.

### 0. Ubicarse en la rama correcta

Si clonas desde GitHub:

```bash
git clone https://github.com/JuanDGiraldo29/geoscene-ai.git
cd geoscene-ai
git checkout integracion/completa
```

Si descargas un ZIP, selecciona la rama `integracion/completa` antes de
descargarlo. Requisitos: **Python 3.10 o superior**. Comprueba la versión con
`python3 --version` en macOS/Linux o `python --version` en Windows. En Windows,
si `python` no existe, usa `py -3` en los comandos.

### 1. Crear y activar el entorno virtual

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Windows · PowerShell**

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Windows · CMD**

```bat
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si PowerShell bloquea `Activate.ps1`, ejecuta una vez
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. En Git Bash también
funciona `source .venv/Scripts/activate`.

> **Importante:** con el venv activo usa `python`, no `python3`. Si aparece
> `No module named uvicorn`, el entorno no está activo. Sin activarlo puedes
> invocar el intérprete directamente:
>
> - macOS/Linux: `.venv/bin/python -m uvicorn api.main:app --host 127.0.0.1 --port 8000`
> - Windows: `.venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8000`

### 2. (Opcional) Descargar el dataset para métricas en vivo

El checkpoint y `splits/indices.json` ya vienen en el repositorio, así que la
interfaz y `/predict` funcionan sin descargar el dataset. Solo si quieres que
`/reporte` y `/panel` calculen las métricas en vivo necesitas EuroSAT:

```bash
python -m modelo.datos
```

La primera vez torchvision descarga el dataset en `data/`. Si
`splits/indices.json` ya existe, no se rehace.

### 3. Levantar la aplicación (dos terminales)

En **ambas** terminales activa el venv y ubícate en la raíz del repositorio.

**Terminal 1 · API**

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 · Interfaz**

```bash
python -m streamlit run interfaz/app.py --server.port 8501 --server.address 127.0.0.1
```

Comprueba que la API está en modo real:

```bash
curl http://127.0.0.1:8000/health
# {"status":"ok","modo":"real"}
```

En Windows PowerShell `curl` es un alias de `Invoke-WebRequest`; usa
`curl.exe` o abre la URL en el navegador.

Luego abre:

| Recurso | URL |
|---|---|
| Interfaz | <http://127.0.0.1:8501> |
| Panel operativo | <http://127.0.0.1:8000/panel> |
| Swagger UI | <http://127.0.0.1:8000/docs> |
| OpenAPI crudo | <http://127.0.0.1:8000/openapi.json> |
| Health check | <http://127.0.0.1:8000/health> |

El límite de subida es de **10 MB por imagen**, el mismo en la interfaz y en la
API. Streamlit lo lee de `.streamlit/config.toml` (`server.maxUploadSize = 10`)
y la API de `TAMANO_MAXIMO_MB` en `compartido/constantes.py`; las pruebas
comprueban que no se desincronicen. Las imágenes de EuroSAT pesan unos pocos
kilobytes, así que el límite solo protege contra archivos enormes por error.

Si la API vive en otro puerto, la interfaz lo acepta con `GEOSCENE_API_URL`:

**macOS / Linux**

```bash
GEOSCENE_API_URL=http://127.0.0.1:9000 python -m streamlit run interfaz/app.py
```

**Windows · PowerShell**

```powershell
$env:GEOSCENE_API_URL = "http://127.0.0.1:9000"
python -m streamlit run interfaz/app.py
```

**Windows · CMD**

```bat
set GEOSCENE_API_URL=http://127.0.0.1:9000
python -m streamlit run interfaz/app.py
```

Los orígenes permitidos para clientes de navegador se configuran con
`GEOSCENE_ORIGENES`, usando la misma sintaxis de variable de entorno de cada
sistema.

### 4. Verificación rápida

```bash
python -m pytest -q
```

Deben pasar **38 pruebas**. `tests/test_modelo_referencia.py` certifica que el
checkpoint versionado sigue siendo el modelo de referencia (SHA-256,
arquitectura, época, umbral y número de parámetros). `tests/test_limite_subida.py`
certifica que la interfaz y la API anuncian y aplican el mismo límite de subida.

### Si quieres reproducir el entrenamiento

El dataset se descarga con torchvision la primera vez. Los pasos son:

```bash
python -m modelo.datos                 # descarga data/ y conserva splits/indices.json
python -m modelo.entrenar              # entrena y guarda models/geoscene_cnn.pt
python -m modelo.evaluar --split val   # calibra el umbral de revisión
python -m modelo.evaluar --split test  # evaluación final, una sola vez
```

La validación elige época y umbral; test solo se usa al final. El reporte lee
los hiperparámetros efectivos del checkpoint, no de valores escritos a mano. Si
un campo no está en el checkpoint, se toma de `compartido/constantes.py` y la
procedencia indica exactamente cuál fue la fuente.

> Al reentrenar se sobrescribe `models/geoscene_cnn.pt`. Eso es esperado, pero
> invalida la huella certificada: actualiza el SHA-256 del README y ejecuta de
> nuevo las pruebas antes de volver a commitear el checkpoint.

## Lo que se añadió en esta versión

La base del proyecto tenía cinco endpoints: `/health`, `/clases`, `/alcance`,
`/predict` y `/decision`. Esta integración mantiene ese contrato y agrega una
capa de documentación y observabilidad:

| Nuevo recurso | Qué aporta |
|---|---|
| `GET /docs` | Swagger UI **local y ejecutable**. Los assets viajan en `api/estaticos/`, así que funciona sin internet. |
| `GET /openapi.json` | Contrato OpenAPI generado desde el código, con esquemas de procedencia y huellas. |
| `GET /reporte` | Métricas recalculadas en cada consulta sobre `val` o `test`, sin caché. |
| `GET /panel` | Centro de operaciones autocontenido: KPIs, F1 por clase, matriz de confusión, errores de alta confianza, decisiones y certificación. |
| `GET /` | Redirige al panel operativo. |
| `docs/API.md` | Mapa de conexiones, endpoints, reporte y límites conocidos. |
| `tests/test_reporte.py` | Pruebas del panel, Swagger, OpenAPI, procedencia y huellas SHA-256. |

Además, la interfaz incorpora el flujo con esqueletos de carga, revelado
progresivo en el panel, refresco silencioso cada 20 segundos, soporte para
`prefers-reduced-motion` y enlaces directos a Swagger y auditoría.

### Endpoints completos

| Verbo | Ruta | Para qué |
|---|---|---|
| GET | `/health` | Estado de la API y modo (`real` o `mock`). |
| GET | `/clases` | Las 10 clases en orden y sus nombres en español. |
| GET | `/alcance` | Aviso de alcance que muestra la interfaz. |
| POST | `/predict` | Imagen → categoría, confianza, top-3 y umbral. Registra la predicción. |
| POST | `/decision` | Acepta o corrige una predicción. Registra la decisión aparte. |
| GET | `/reporte?split=test` | Métricas completas medidas en vivo. Acepta `split=val` y `limite=N`. |
| GET | `/panel` | Tablero operativo en HTML. |
| GET | `/docs` | Swagger UI local. |
| GET | `/openapi.json` | Esquema OpenAPI. |

Prueba rápida del reporte:

```bash
curl -s "http://127.0.0.1:8000/reporte?split=test" | python -m json.tool
curl -s "http://127.0.0.1:8000/reporte?split=val&limite=200" | python -m json.tool
```

## Métricas del modelo

Los valores siguientes salen de la partición de test (1.000 imágenes) y se
recalculan en vivo con `/reporte`. No se leen de un archivo histórico.

| Métrica | Valor |
|---|---|
| Accuracy (top-1) | **82,7 %** |
| Macro F1 | **82,44 %** |
| F1 ponderado | 82,44 % |
| Top-3 | 97,5 % |
| Top-5 | 99,6 % |
| Precisión macro | 82,71 % |
| Recall macro | 82,70 % |
| Pérdida (CrossEntropy) | 0,5055 |
| Confianza media | 82,53 % |
| Errores | 173 de 1.000 |

**Regla de revisión.** Con umbral 0,73, el 26,9 % de las imágenes se marcan para
revisión. En las no marcadas la accuracy sube a 92,75 %; en las marcadas baja a
55,39 %. La regla no adivina: justamente separa los casos donde el modelo duda.

**Costo.** Una inferencia 32×32 tarda aproximadamente 0,21 ms en CPU (medida en
vivo, solo preprocesamiento y modelo); el camino completo, incluyendo decodificar
el archivo, ronda 0,26 ms, con un throughput cercano a 4.709 imágenes por
segundo. El modelo tiene 545.098 parámetros, 6,13 M MACs y 12,26 M FLOPs por
imagen.

**Calibración.** El reporte incluye ECE (10 bins), Brier multiclase, log-loss,
entropía y una tabla de fiabilidad. Es información descriptiva: no se aplica
temperature scaling para no alterar el umbral ya calibrado con validación.

## Comparación de arquitecturas y decisión

Durante el proyecto se entrenaron dos variantes de la misma CNN. La que queda
integrada y versionada en esta rama es la **arquitectura de referencia**; la
segunda se conserva en `feature/johan` como experimento para la exposición.

| Rasgo | Referencia (esta rama) | Variante experimental (`feature/johan`) |
|---|---|---|
| Canales convolucionales | 32 → 64 | 64 → 128 |
| Normalización por lotes | No | `BatchNorm2d` tras cada convolución |
| Parámetros | 545.098 | 4.275.978 (≈7,8×) |
| MACs / FLOPs por imagen | 6,13 M / 12,26 M | 24,8 M / 49,7 M |
| Época elegida con validación | 20 · 80,7 % | 27 · 83,7 % |
| Accuracy de test | 82,70 % | 85,50 % |
| Macro F1 de test | 82,44 % | 85,31 % |
| Tamaño del checkpoint | 2,1 MB | 17,1 MB |

**Por qué la integración usa la referencia.** Es la CNN del ejercicio base, se
entrena y evalúa en CPU sin dificultad, el checkpoint pesa 2,1 MB y el resultado
es reproducible con los comandos del README. La variante duplica canales y
multiplica por ~8 los parámetros y por ~4 el cómputo; la mejora de métricas
(≈2,8 puntos de accuracy) es real, pero no cambia la naturaleza del ejercicio.

**Por qué se muestran las dos.** La comparación es parte del análisis: permite
explicar que una red más ancha y con normalización mejora, y a qué costo. Para
la exposición se puede presentar la variante de `feature/johan` como el
resultado con las métricas más altas —los equipos disponibles permitieron
entrenarla— y dejar la referencia como la versión liviana y estrictamente
apegada al taller. Ambas usan las mismas particiones, semilla y umbral
calibrado con validación, así que la comparación es justa.

**Sobre `BatchNorm2d`.** No aparece en los ejercicios de clase, pero el taller
permitía libertad de implementación. Su función es normalizar las activaciones
de cada canal dentro de un mini-lote (media 0, varianza 1) y aplicar después un
escalado y un desplazamiento aprendibles. En la práctica estabiliza y acelera la
convergencia, reduce la sensibilidad a la inicialización y a la tasa de
aprendizaje, y actúa como una regularización suave. En inferencia usa las medias
y varianzas acumuladas durante el entrenamiento (`running_mean`/`running_var`),
por lo que la predicción es determinista. El costo es pequeño en parámetros
(2 por canal) pero obliga a entrenar con lotes suficientemente grandes; aquí se
usó lote 64. En esta rama se mantiene la referencia sin BatchNorm para no
depender de una técnica fuera del material base; su justificación queda
documentada para la variante experimental.

## Panel operativo y Swagger

El **panel** (`/panel`) es el centro de operaciones. Se actualiza solo cada 20
segundos sin parpadeos, tiene un sello **PROCEDENCIA OK** cuando las huellas
coinciden, muestra la tabla de certificación, el mapa de fuentes y un enlace al
reporte crudo. Está pensado para revisar el estado del sistema en una demo o
para que el docente audite sin abrir la interfaz.

**Swagger** (`/docs`) es el contrato navegable y ejecutable. Desde ahí se puede
probar `/predict` con un archivo, consultar `/reporte` y revisar los esquemas
`Procedencia`, `Huella`, `DatasetHuella` y `SalidasHuella`. `/redoc` no existe a
propósito: una sola interfaz evita documentación duplicada. Todas las respuestas
de documentación y reporte envían `Cache-Control: no-store`.

## Procedencia y certificación

Cada consulta a `/reporte` devuelve un bloque `procedencia` con:

- ruta, tamaño, fecha y **SHA-256** del checkpoint y de `splits/indices.json`;
- número de imágenes del dataset y rutas de salida;
- fuente declarada de cada bloque (checkpoint, constantes, CSV o runtime);
- alcance exacto del cálculo, por ejemplo `softmax_sobre_1000_imagenes_test`.

Huellas del estado certificado:

| Archivo | SHA-256 (prefijo) |
|---|---|
| `models/geoscene_cnn.pt` | `e073084ab5c7633b…` |
| `splits/indices.json` | `503829561fe996aa…` |

La API valida que el orden de clases del checkpoint coincida con
`compartido/constantes.py`. Si cambia el checkpoint, las particiones o el orden
de clases, la huella cambia y el reporte falla en vez de mostrar métricas
dudosas. Los hashes completos están en `/reporte` y en el panel.

## Estructura del repositorio

```
geoscene-ai/
├── api/                  FastAPI: clasificador, endpoints, panel, reporte y Swagger
│   ├── main.py           Contrato HTTP, esquemas y rutas
│   ├── clasificador.py   Carga el checkpoint y predice
│   ├── reporte.py        Métricas medidas en vivo y procedencia
│   ├── panel.py          Tablero HTML autocontenido
│   ├── docs.py           Swagger UI local
│   └── estaticos/        Assets de Swagger (sin CDN)
├── compartido/           Constantes, preprocesamiento y contrato entre capas
├── modelo/               Datos, red, entrenamiento y evaluación
├── interfaz/             Streamlit: cliente HTTP, app y estilos
├── models/               Checkpoint certificado
├── splits/               Índices de las particiones
├── demo_images/          Imágenes de ejemplo para la demo
├── docs/                 Contrato y documentación de la API
├── tests/                Pruebas de contrato, API, clasificador y reporte
└── requirements.txt
```

`data/` y `outputs/` se crean al ejecutar y están en `.gitignore`. El dataset
completo no se versiona; el checkpoint y los índices sí, para que cualquiera
pueda correr la demo y auditar las métricas.

## Pruebas

```bash
python -m pytest -q
```

La suite cubre el contrato, el mock, el clasificador, los endpoints de
predicción y decisión, el panel, Swagger, OpenAPI, la procedencia y las huellas
SHA-256. `tests/test_modelo_referencia.py` certifica además que el checkpoint
versionado es exactamente el de la rama base (arquitectura, parámetros, época,
umbral y SHA-256). Estado actual: **33 pruebas aprobadas**.

## Decisiones y límites conocidos

- **Sin autenticación.** Es una demo local, no un servicio público.
- **El modelo siempre responde una de las 10 clases.** Una imagen fuera de
  EuroSAT recibirá igualmente una categoría; el aviso de alcance lo dice en la
  interfaz y en `/alcance`.
- **Test no se usa para ajustar.** El umbral y la época se eligen con validación.
  Medir test varias veces no cambia el modelo, pero sigue siendo evidencia de
  evaluación.
- **`/reporte` prioriza trazabilidad sobre latencia.** Recorre la partición
  completa y vuelve a inferir; usa `limite` para pruebas rápidas y recuerda que
  entonces `parcial` es `true`.
- **La calibración es descriptiva.** No se corrige la probabilidad para no mover
  un umbral ya validado.
- **El modo mock existe para desarrollar.** No debe presentarse como resultado
  del modelo.
- **Límite de subida: 10 MB por imagen.** La interfaz y la API aplican el mismo
  valor (`.streamlit/config.toml` y `compartido/constantes.py`). Antes Streamlit
  anunciaba 200 MB por defecto mientras la API rechazaba a partir de 10 MB.

## Para la ficha ejecutiva

Este README sirve como base técnica. Para el documento de máximo 3 páginas,
los insumos ya están listos:

- **Métricas y matriz de confusión:** `/reporte?split=test` y `/panel`.
- **Regla de revisión justificada:** umbral 0,73 elegido en validación, con
  cobertura y accuracy de marcadas/no marcadas.
- **Tres errores representativos:** bloque `errores_alta_confianza` del reporte.
- **Limitación principal:** el modelo solo conoce 10 categorías y no detecta
  imágenes fuera de dominio.
- **Riesgo y mitigación:** una sugerencia errónea puede afectar una decisión de
  ordenamiento; se mitiga con revisión humana obligatoria, umbral conservador y
  registro separado de predicción y decisión.
- **Mejora propuesta:** ampliar el dominio con clases de rechazo o datos locales,
  y comparar arquitecturas con validación.
- **Reproducibilidad:** semilla 42, particiones versionadas, checkpoint con
  SHA-256 y comando de pruebas.
- **Recursos externos:** declarar en la ficha los asistentes de IA y librerías
  utilizadas, según la regla del taller.
