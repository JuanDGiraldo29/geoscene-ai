# GeoScene AI

Clasificador de imágenes satelitales EuroSAT (10 categorías, RGB 32×32) con
revisión humana: el modelo sugiere una categoría y una persona la acepta o la
corrige. Proyecto final de Deep Learning 2026, Reto A.

El repositorio está **estructurado pero no resuelto**: cada archivo tiene
comentarios `TODO` numerados que explican qué escribir. Solo está hecho lo que
permite que las tres capas avancen a la vez (la carpeta `compartido/`).

## Cómo encajan las piezas

```
 modelo/  (integrantes 1 y 2)          api/  (capa de consumo)          interfaz/  (interfaz)
 datos → red → entrenar → evaluar      clasificador.py → main.py        app.py
        │                                    ▲      │                     ▲   │
        └──── models/geoscene_cnn.pt ────────┘      └──── HTTP + JSON ────┘
                       compartido/  ← lo usan las tres capas
```

La interfaz solo habla con la API; la API solo conoce el modelo a través del
archivo `.pt`. Por eso nadie necesita esperar a nadie: mientras no exista el
modelo, la API responde con un clasificador de prueba (mock).

## Qué hay en cada archivo

| Archivo | Para qué sirve | Quién |
|---|---|---|
| `compartido/constantes.py` | Las 10 clases, tamaño 32×32, semilla 42, rutas y aviso de alcance | Hecho. Se cambia solo si lo acordamos |
| `compartido/preprocesamiento.py` | La transformación de imágenes que usan entrenamiento y app | Hecho |
| `compartido/contrato.py` | Formato de la respuesta, del checkpoint y el mock | Hecho |
| `modelo/datos.py` | Descargar EuroSAT y crear las particiones 500/100/100 | Integrante 1 |
| `modelo/red.py` | La CNN de dos bloques | Integrantes 1 y 2 |
| `modelo/entrenar.py` | Entrenar, validar y guardar el mejor modelo | Integrante 1 |
| `modelo/evaluar.py` | Umbral de revisión (validación) y métricas finales (test) | Integrante 2 |
| `api/clasificador.py` | El wrapper: carga el modelo y predice | Capa de consumo |
| `api/main.py` | Los endpoints de FastAPI | Capa de consumo |
| `interfaz/app.py` | La pantalla de Streamlit | Interfaz |
| `tests/test_contrato.py` | Pruebas del contrato | Todos pueden añadir |
| `docs/CONTRATO.md` | El acuerdo entre capas, con ejemplos de JSON | Todos lo leen |
| `requirements.txt` | Librerías (las mismas versiones para todos) | |
| `.gitignore` | Indica a Git qué NO subir (datos, salidas, cachés) | |

Las carpetas `data/`, `outputs/`, `models/` y `splits/` no están en el
repositorio: el código las crea al ejecutarse. `models/geoscene_cnn.pt` y
`splits/indices.json` se suben a GitHub cuando estén listos.

## Instalación

```bash
git clone <url-del-repo>
cd geoscene-ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest                 # deben pasar las 6 pruebas
```

## Cómo probar cada capa

Siempre desde la carpeta raíz del proyecto (por eso se usa `python -m`).

```bash
# Modelo (integrantes 1 y 2), en este orden
python -m modelo.datos
python -m modelo.entrenar
python -m modelo.evaluar --split val
python -m modelo.evaluar --split test      # solo al final, una vez

# API (ya funciona con el mock). Documentación: http://localhost:8000/docs
uvicorn api.main:app --reload --port 8000

# Interfaz (con la API encendida en otra terminal)
streamlit run interfaz/app.py
```

## Reglas del taller

- Entrada RGB 32×32, CNN propia de dos bloques, sin pesos preentrenados.
- Particiones balanceadas y disjuntas (500/100/100 por clase), semilla 42, índices guardados.
- Train para aprender, **validación para elegir** (época y umbral), **test solo al final**.
- La predicción del modelo y la decisión humana se guardan por separado; corregir no reentrena.
- Declarar los recursos externos (incluidos asistentes de IA) en la ficha ejecutiva.

## Cómo trabajar con Git

1. `main` siempre debe funcionar. Cada persona trabaja en su rama:
   `feature/modelo`, `feature/evaluacion`, `feature/api`, `feature/interfaz`.
2. Antes de subir: `python -m pytest`. Se sube con un pull request que revisa otra persona.
3. Los cambios en `compartido/` o en `docs/CONTRATO.md` se avisan al grupo antes.
4. No se suben `data/` ni `outputs/` (ya están en `.gitignore`).

## Entregables de la guía

- [ ] Aplicación que corre y se puede probar en vivo
- [ ] Modelo entrenado (`models/geoscene_cnn.pt`) y particiones (`splits/indices.json`)
- [ ] Accuracy, macro F1, matriz de confusión, resultados por clase y tres errores
- [ ] Regla de revisión justificada con validación
- [ ] Ficha ejecutiva de máximo 3 páginas (incluye limitación, riesgo con mitigación, mejora y fuentes)

## Reproducir
El proyecto se reproduce con seis pasos desde la carpeta raíz
Cómo reproducirlo.
1.	pip install -r requirements.txt y python -m pytest.
2.	python -m modelo.datos: crea las particiones, una sola vez.
3.	python -m modelo.entrenar, con EPOCAS = 20.
4.	python -m modelo.evaluar --split val: calibra el umbral.
5.	python -m modelo.evaluar --split test: evaluación final, una sola vez.
6.	uvicorn api.main:app --port 8000 y, en otra terminal, streamlit run interfaz/app.py.

