"""Observabilidad: métricas calculadas EN EL MOMENTO de la consulta.

No hay valores guardados ni caché: cada llamada carga el checkpoint, recorre la
partición pedida (val o test) y vuelve a medir accuracy, macro F1, top-3, la
regla de revisión, la matriz de confusión, la calibración de la confianza y la
latencia.

Se usa desde `api/main.py` (GET /reporte). Si falta el modelo, las particiones
o el dataset, lanza SinRecursoError y la API responde 503 con el motivo.
"""
from __future__ import annotations

import csv
import os
import platform
import time
from datetime import datetime

import numpy as np
import torch
from torch import nn
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Subset

from compartido.constantes import (
    CARPETA_DATOS,
    CARPETA_SALIDAS,
    CLASES,
    IMG_SIZE,
    RUTA_INDICES,
    RUTA_MODELO,
)
from compartido.contrato import leer_checkpoint
from compartido.preprocesamiento import crear_transformacion
from modelo.datos import cargar_eurosat, cargar_indices
from modelo.red import GeoSceneCNN

VERSION_REPORTE = "1.3.0"
MUESTRA_LATENCIA = 100      # imágenes que se cronometran una por una (modelo)
MUESTRA_COMPLETA = 50       # imágenes que se cronometran con decodificación incluida
MIN_ACEPTADAS = 30          # menos que esto y un porcentaje no es fiable
ARTEFACTOS = [
    "metricas_test.json",
    "matriz_confusion.png",
    "tres_errores.png",
    "umbral_validacion.png",
    "curvas_entrenamiento.png",
]
_INICIO = time.monotonic()


class SinRecursoError(RuntimeError):
    """Falta el checkpoint, las particiones o el dataset. La API responde 503."""


def _r4(valor) -> float:
    return round(float(valor), 4)


def _leer_csv(ruta: str) -> list[dict]:
    if not os.path.exists(ruta):
        return []
    with open(ruta, newline="", encoding="utf-8") as archivo:
        return list(csv.DictReader(archivo))


def _verificar_recursos() -> None:
    if not os.path.exists(RUTA_MODELO):
        raise SinRecursoError(
            f"Falta el checkpoint {RUTA_MODELO}. Entrena el modelo antes de pedir el reporte."
        )
    if not os.path.exists(RUTA_INDICES):
        raise SinRecursoError(
            f"Faltan las particiones {RUTA_INDICES}. Ejecuta: python -m modelo.datos"
        )
    if not os.path.isdir(CARPETA_DATOS):
        raise SinRecursoError(
            f"Falta el dataset en {CARPETA_DATOS}/eurosat. Ejecuta: python -m modelo.datos"
        )


def _cargar_modelo():
    ckpt = leer_checkpoint(RUTA_MODELO)
    modelo = GeoSceneCNN()
    modelo.load_state_dict(ckpt["state_dict"])
    modelo.eval()  # sin esto el dropout daría métricas distintas en cada consulta
    return modelo, ckpt


def _decisiones_humanas() -> dict:
    decisiones = _leer_csv(os.path.join(CARPETA_SALIDAS, "decisiones.csv"))
    predicciones = _leer_csv(os.path.join(CARPETA_SALIDAS, "predicciones.csv"))
    aceptadas = sum(1 for fila in decisiones if fila.get("estado") == "aceptada")
    corregidas = sum(1 for fila in decisiones if fila.get("estado") == "corregida")
    total = len(decisiones)
    return {
        "predicciones_registradas": len(predicciones),
        "decisiones_registradas": total,
        "aceptadas": aceptadas,
        "corregidas": corregidas,
        "tasa_correccion": _r4(corregidas / total) if total else 0.0,
        "ultima_decision": decisiones[-1]["fecha"] if decisiones else None,
    }


def _calibracion(prob, real, predicha, confianza) -> dict:
    """¿La confianza coincide con el acierto? ECE, Brier, NLL y bins de fiabilidad."""
    aciertos = predicha == real
    unico = np.eye(len(CLASES))[real]
    brier = np.mean(np.sum((prob - unico) ** 2, axis=1))
    probabilidad_real = np.clip(prob[np.arange(len(real)), real], 1e-12, 1.0)
    nll = -np.mean(np.log(probabilidad_real))
    entropia = -(prob * np.log(np.clip(prob, 1e-12, None))).sum(axis=1)

    bordes = np.linspace(0.0, 1.0, 11)
    ece = 0.0
    fiabilidad = []
    for i in range(10):
        bajo, alto = float(bordes[i]), float(bordes[i + 1])
        if i == 0:
            mascara = (confianza >= bajo) & (confianza <= alto)
        else:
            mascara = (confianza > bajo) & (confianza <= alto)
        n = int(mascara.sum())
        if n == 0:
            continue
        acierto_bin = float(aciertos[mascara].mean())
        confianza_bin = float(confianza[mascara].mean())
        ece += (n / len(real)) * abs(acierto_bin - confianza_bin)
        fiabilidad.append({
            "rango": f"{bajo:.1f}–{alto:.1f}",
            "n": n,
            "confianza": _r4(confianza_bin),
            "accuracy": _r4(acierto_bin),
        })

    return {
        "ece": _r4(ece),
        "brier": _r4(brier),
        "nll": _r4(nll),
        "confianza_media": _r4(confianza.mean()),
        "confianza_mediana": _r4(np.median(confianza)),
        "confianza_p10": _r4(np.percentile(confianza, 10)),
        "confianza_p90": _r4(np.percentile(confianza, 90)),
        "entropia_media": _r4(entropia.mean()),
        "fiabilidad": fiabilidad,
    }


def _barrido_umbral(confianza, aciertos) -> list[dict]:
    """Qué pasaría con la regla de revisión en otros umbrales (en esta partición)."""
    tabla = []
    for umbral in np.round(np.arange(0.50, 0.96, 0.05), 2):
        aceptadas = confianza >= umbral
        if int(aceptadas.sum()) < MIN_ACEPTADAS:
            continue
        tabla.append({
            "umbral": round(float(umbral), 2),
            "cobertura": _r4(aceptadas.mean()),
            "accuracy_no_marcadas": _r4(aciertos[aceptadas].mean()),
        })
    return tabla


def _artefactos() -> list[dict]:
    """Evidencia que deja `modelo.evaluar` en outputs/. Solo se informa, no se lee."""
    salida = []
    for nombre in ARTEFACTOS:
        ruta = os.path.join(CARPETA_SALIDAS, nombre)
        existe = os.path.exists(ruta)
        salida.append({
            "nombre": nombre,
            "ruta": ruta,
            "existe": existe,
            "bytes": os.path.getsize(ruta) if existe else 0,
            "modificado": (
                datetime.fromtimestamp(os.path.getmtime(ruta)).isoformat(timespec="seconds")
                if existe else None
            ),
        })
    return salida


def _contar_macs(modelo) -> int:
    """Multiplicaciones-acumulaciones de una inferencia 1×3×32×32 (MACs).

    Se cuentan con ganchos sobre las capas que hacen aritmética (convolución y
    lineal); no se guarda nada, se mide una vez por consulta sobre ceros.
    """
    total = 0
    ganchos = []

    def convolucion(capa, _entrada, salida):
        nonlocal total
        kernel = capa.kernel_size[0] * capa.kernel_size[1]
        total += capa.in_channels * capa.out_channels * kernel * salida.shape[2] * salida.shape[3]

    def lineal(capa, _entrada, _salida):
        nonlocal total
        total += capa.in_features * capa.out_features

    for capa in modelo.modules():
        if isinstance(capa, nn.Conv2d):
            ganchos.append(capa.register_forward_hook(convolucion))
        elif isinstance(capa, nn.Linear):
            ganchos.append(capa.register_forward_hook(lineal))

    with torch.no_grad():
        modelo(torch.zeros(1, 3, IMG_SIZE, IMG_SIZE))

    for gancho in ganchos:
        gancho.remove()
    return int(total)


def medir(split: str = "test", limite: int | None = None) -> dict:
    """Recorre la partición y devuelve el reporte completo, medido ahora mismo."""
    _verificar_recursos()
    if split not in ("val", "test"):
        raise ValueError("split debe ser 'val' o 'test'")

    modelo, ckpt = _cargar_modelo()
    particiones = cargar_indices()
    indices = list(particiones[split])
    if limite:
        indices = indices[:limite]
    if not indices:
        raise SinRecursoError(f"La partición '{split}' está vacía.")

    transformacion = crear_transformacion(ckpt["media"], ckpt["desviacion"])
    dataset = cargar_eurosat(transformacion)
    cargador = DataLoader(Subset(dataset, indices), batch_size=128)

    probabilidades, reales = [], []
    inicio = time.perf_counter()
    with torch.no_grad():
        for X, y in cargador:
            probabilidades.append(torch.softmax(modelo(X), dim=1))
            reales.append(y)
    duracion_ms = (time.perf_counter() - inicio) * 1000

    prob = torch.cat(probabilidades).numpy()
    real = torch.cat(reales).numpy()
    predicha = prob.argmax(axis=1)
    confianza = prob.max(axis=1)

    aciertos = predicha == real
    ordenadas = np.argsort(-prob, axis=1)
    top3 = (ordenadas[:, :3] == real[:, None]).any(axis=1).mean()
    top5 = (ordenadas[:, :5] == real[:, None]).any(axis=1).mean()
    perdida = -np.mean(np.log(np.clip(prob[np.arange(len(real)), real], 1e-12, None)))

    informe = classification_report(
        real, predicha, labels=range(len(CLASES)), target_names=CLASES,
        output_dict=True, zero_division=0,
    )
    por_clase = {
        clase: {
            "precision": _r4(informe[clase]["precision"]),
            "recall": _r4(informe[clase]["recall"]),
            "f1": _r4(informe[clase]["f1-score"]),
            "soporte": int(informe[clase]["support"]),
        }
        for clase in CLASES
    }

    matriz = confusion_matrix(real, predicha, labels=range(len(CLASES)))
    fuera_diagonal = matriz.astype(int).copy()
    np.fill_diagonal(fuera_diagonal, 0)
    pares = sorted(
        (
            (int(fuera_diagonal[i, j]), i, j)
            for i in range(len(CLASES))
            for j in range(len(CLASES))
            if fuera_diagonal[i, j] > 0
        ),
        reverse=True,
    )[:5]
    top_confusiones = [
        {"real": CLASES[i], "predicho": CLASES[j], "veces": veces}
        for veces, i, j in pares
    ]

    errores = np.flatnonzero(~aciertos)
    errores = errores[np.argsort(-confianza[errores])][:3]
    errores_alta_confianza = [
        {
            "real": CLASES[real[i]],
            "predicho": CLASES[predicha[i]],
            "confianza": _r4(confianza[i]),
        }
        for i in errores
    ]

    umbral = float(ckpt["umbral"])
    aceptadas = confianza >= umbral
    marcadas = ~aceptadas
    regla_revision = {
        "umbral": umbral,
        "cobertura": _r4(aceptadas.mean()),
        "porcentaje_marcadas": _r4(marcadas.mean()),
        "accuracy_no_marcadas": _r4(aciertos[aceptadas].mean()) if aceptadas.any() else 0.0,
        "accuracy_marcadas": _r4(aciertos[marcadas].mean()) if marcadas.any() else 0.0,
    }

    # Latencia: (a) transformación + modelo sobre tensor ya decodificado,
    # (b) camino completo, incluyendo abrir y decodificar el archivo.
    crudo = cargar_eurosat()
    tiempos = []
    with torch.no_grad():
        for indice in indices[:MUESTRA_LATENCIA]:
            imagen, _ = crudo[indice]
            instante = time.perf_counter()
            torch.softmax(modelo(transformacion(imagen).unsqueeze(0)), dim=1)
            tiempos.append((time.perf_counter() - instante) * 1000)

        tiempos_completos = []
        for indice in indices[:MUESTRA_COMPLETA]:
            instante = time.perf_counter()
            imagen, _ = crudo[indice]  # incluye decodificar el JPEG
            torch.softmax(modelo(transformacion(imagen).unsqueeze(0)), dim=1)
            tiempos_completos.append((time.perf_counter() - instante) * 1000)

    latencia = {
        "ms_por_imagen_media": _r4(np.mean(tiempos)),
        "ms_por_imagen_p50": _r4(np.percentile(tiempos, 50)),
        "ms_por_imagen_p95": _r4(np.percentile(tiempos, 95)),
        "ms_por_imagen_p99": _r4(np.percentile(tiempos, 99)),
        "ms_por_imagen_lote": _r4(duracion_ms / len(real)),
        "ms_camino_completo_media": _r4(np.mean(tiempos_completos)),
        "imagenes_por_segundo": _r4(1000 / np.mean(tiempos)),
        "muestra": len(tiempos),
    }

    arquitectura = [
        {"capa": nombre, "parametros": int(peso.numel()), "forma": list(peso.shape)}
        for nombre, peso in modelo.named_parameters()
    ]
    macs = _contar_macs(modelo)
    hiperparametros = ckpt.get("hiperparametros") or {}

    return {
        "meta": {
            "split": split,
            "n_imagenes": int(len(real)),
            "medido_en": datetime.now().isoformat(timespec="milliseconds"),
            "duracion_ms": round(duracion_ms, 1),
            "fuente": "calculado_en_vivo_sin_cache",
            "parcial": bool(limite),
            "version": VERSION_REPORTE,
        },
        "modelo": {
            "checkpoint": RUTA_MODELO,
            "bytes": os.path.getsize(RUTA_MODELO),
            "epoca": ckpt.get("epoca"),
            "val_accuracy": ckpt.get("val_accuracy"),
            "parametros": int(sum(p.numel() for p in modelo.parameters())),
            "parametros_entrenables": int(sum(p.numel() for p in modelo.parameters() if p.requires_grad)),
            "macs": macs,
            "flops": macs * 2,
            "entrada": [1, 3, IMG_SIZE, IMG_SIZE],
            "canales": 3,
            "capas": len(arquitectura),
            "arquitectura": arquitectura,
            "hiperparametros": ckpt.get("hiperparametros"),
            "funcion_perdida": "CrossEntropyLoss",
            "optimizador": "Adam",
            "plan_lr": "constante (sin scheduler)",
            "tasa_aprendizaje": hiperparametros.get("lr"),
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "torch": torch.__version__,
            "umbral": umbral,
            "umbral_calibrado": bool(ckpt.get("umbral_calibrado")),
            "objetivo_precision": ckpt.get("objetivo_precision"),
            "img_size": IMG_SIZE,
            "clases": len(CLASES),
            "normalizacion": {
                "media": [_r4(v) for v in ckpt["media"]],
                "desviacion": [_r4(v) for v in ckpt["desviacion"]],
            },
        },
        "metricas": {
            "accuracy": _r4(accuracy_score(real, predicha)),
            "top3": _r4(top3),
            "top5": _r4(top5),
            "perdida": _r4(perdida),
            "precision_macro": _r4(informe["macro avg"]["precision"]),
            "recall_macro": _r4(informe["macro avg"]["recall"]),
            "macro_f1": _r4(f1_score(real, predicha, average="macro")),
            "f1_weighted": _r4(f1_score(real, predicha, average="weighted")),
            "confianza_media": _r4(confianza.mean()),
            "errores": int((~aciertos).sum()),
        },
        "por_clase": por_clase,
        "confusion": {
            "clases": list(CLASES),
            "matriz": matriz.astype(int).tolist(),
        },
        "top_confusiones": top_confusiones,
        "errores_alta_confianza": errores_alta_confianza,
        "regla_revision": regla_revision,
        "calibracion": _calibracion(prob, real, predicha, confianza),
        "barrido_umbral": _barrido_umbral(confianza, aciertos),
        "latencia": latencia,
        "particion": {
            "split": split,
            "n": int(len(real)),
            "por_clase": {
                CLASES[i]: int((real == i).sum()) for i in range(len(CLASES))
            },
            "tamanos": {nombre: len(lista) for nombre, lista in particiones.items()},
        },
        "artefactos": _artefactos(),
        "decisiones": _decisiones_humanas(),
        "sistema": {
            "uptime_s": round(time.monotonic() - _INICIO, 1),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "device": "cuda" if torch.cuda.is_available() else "cpu",
            "hilos_torch": torch.get_num_threads(),
            "tamano_checkpoint_mb": round(os.path.getsize(RUTA_MODELO) / 1e6, 2),
        },
    }
