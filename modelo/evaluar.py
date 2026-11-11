"""PASO 4 · Umbral de revisión y evaluación final.   Responsable: integrante 2.

Cómo se ejecuta:
    python -m modelo.evaluar --split val      # define el umbral (se puede repetir)
    python -m modelo.evaluar --split test     # evaluación final: UNA sola vez

REGLA DE ORO: el test solo se usa al final, con el modelo ya elegido.
No lo usen para comparar configuraciones.

Entregables (carpeta outputs/, para la ficha ejecutiva):
  accuracy global, macro F1, matriz de confusión, resultados por clase,
  tres errores reales, una confusión frecuente y el tiempo de inferencia.
"""
import argparse
import json
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from torch.utils.data import DataLoader, Subset

from compartido.constantes import CARPETA_SALIDAS, CLASES, RUTA_MODELO
from compartido.contrato import leer_checkpoint
from compartido.preprocesamiento import crear_transformacion
from modelo.datos import cargar_eurosat, cargar_indices
from modelo.red import GeoSceneCNN

OBJETIVO_ACC_NO_MARCADAS = 0.90   # meta de accuracy para las imágenes no marcadas


def cargar_modelo():
    """Reconstruye la red con los pesos guardados."""
    ckpt = leer_checkpoint(RUTA_MODELO)
    modelo = GeoSceneCNN(
        canales=tuple(ckpt.get("hiperparametros", {}).get("canales", (32, 64))),
        neuronas_ocultas=ckpt.get("hiperparametros", {}).get("neuronas_ocultas", 256),
        dropout=ckpt.get("hiperparametros", {}).get("dropout", 0.3),
    )
    modelo.load_state_dict(ckpt["state_dict"])
    modelo.eval()
    return modelo, ckpt


def obtener_probabilidades(modelo, ckpt, nombre_particion):
    """Devuelve (probabilidades, etiquetas_reales) de una partición ("val" o "test")."""
    transform = crear_transformacion(ckpt["media"], ckpt["desviacion"])
    dataset = cargar_eurosat(transform)
    indices = cargar_indices()[nombre_particion]
    cargador = DataLoader(Subset(dataset, indices), batch_size=128, shuffle=False)

    todas_probs, todas_etiquetas = [], []
    with torch.no_grad():
        for x, y in cargador:
            logits = modelo(x)
            todas_probs.append(torch.softmax(logits, dim=1).numpy())
            todas_etiquetas.append(y.numpy())
    return np.concatenate(todas_probs), np.concatenate(todas_etiquetas)


def calibrar_umbral(confianzas, aciertos):
    """Decide con VALIDACIÓN a partir de qué confianza conviene revisar.

    Probar umbrales de 0.30 a 0.99 y para cada uno calcular
      - cobertura: fracción de imágenes NO marcadas para revisión
      - accuracy de las imágenes no marcadas
    Elige el umbral más bajo cuyo accuracy llega al objetivo (90 %):
    es decir, la mayor cobertura posible cumpliendo la meta.
    Guarda la gráfica umbral vs cobertura/accuracy y escribe el umbral
    en el checkpoint.
    """
    umbrales = np.arange(0.30, 1.00, 0.01)
    coberturas, accs = [], []
    for u in umbrales:
        no_marcadas = confianzas >= u
        coberturas.append(no_marcadas.mean())
        accs.append(aciertos[no_marcadas].mean() if no_marcadas.any() else np.nan)

    cumple = [i for i, a in enumerate(accs) if not np.isnan(a) and a >= OBJETIVO_ACC_NO_MARCADAS]
    if cumple:
        mejor_i = cumple[0]          # el umbral más bajo que cumple el objetivo
    else:
        mejor_i = int(np.nanargmax(accs))   # si nadie llega, el de mayor accuracy
        print("AVISO: ningún umbral alcanza el objetivo de accuracy.")
    umbral = float(umbrales[mejor_i])

    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    fig, eje = plt.subplots(figsize=(7, 4))
    eje.plot(umbrales, coberturas, label="cobertura (no marcadas)")
    eje.plot(umbrales, accs, label="accuracy de no marcadas")
    eje.axhline(OBJETIVO_ACC_NO_MARCADAS, color="gray", linestyle="--", label="objetivo 90%")
    eje.axvline(umbral, color="red", linestyle=":", label=f"umbral {umbral:.2f}")
    eje.set_xlabel("umbral de confianza")
    eje.legend()
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_SALIDAS, "umbral_vs_cobertura.png"), dpi=120)
    plt.close(fig)

    ckpt = leer_checkpoint(RUTA_MODELO)
    ckpt["umbral"] = umbral
    torch.save(ckpt, RUTA_MODELO)

    i = mejor_i
    print(
        f"Umbral elegido: {umbral:.2f} | "
        f"cobertura {coberturas[i]:.3f} | "
        f"accuracy de las no marcadas {accs[i]:.3f}"
    )
    return umbral


def evaluar_test(modelo, ckpt):
    """Calcula y guarda en outputs/ las métricas finales del modelo elegido."""
    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    umbral = ckpt.get("umbral", 0.5)

    probs, reales = obtener_probabilidades(modelo, ckpt, "test")
    predichas = probs.argmax(axis=1)
    confianzas = probs.max(axis=1)

    acc = accuracy_score(reales, predichas)
    macro_f1 = f1_score(reales, predichas, average="macro")
    informe = classification_report(reales, predichas, target_names=CLASES, digits=4)
    matriz = confusion_matrix(reales, predichas)

    print(f"Accuracy test: {acc:.4f}")
    print(f"Macro F1 test: {macro_f1:.4f}")
    print(informe)

    # Confusión más frecuente (celda más alta fuera de la diagonal)
    sin_diagonal = matriz.copy()
    np.fill_diagonal(sin_diagonal, 0)
    i, j = np.unravel_index(sin_diagonal.argmax(), sin_diagonal.shape)
    confusion_frecuente = {
        "real": CLASES[i], "predicha": CLASES[j], "frecuencia": int(sin_diagonal[i, j])
    }
    print(f"Confusión frecuente: {CLASES[i]} -> {CLASES[j]} ({sin_diagonal[i, j]} casos)")

    # Tres errores reales con su imagen
    errores = np.flatnonzero(predichas != reales)[:3]
    dataset = cargar_eurosat(crear_transformacion(ckpt["media"], ckpt["desviacion"]))
    indices_test = cargar_indices()["test"]
    detalle_errores = []
    if len(errores):
        fig, ejes = plt.subplots(1, len(errores), figsize=(4 * len(errores), 4))
        if len(errores) == 1:
            ejes = [ejes]
        for eje, k in zip(ejes, errores):
            ruta_imagen = dataset.samples[indices_test[k]][0]
            eje.imshow(dataset[indices_test[k]][0].permute(1, 2, 0).numpy() * ckpt["desviacion"] + ckpt["media"])
            eje.set_title(f"real: {CLASES[reales[k]]}\npred: {CLASES[predichas[k]]}")
            eje.axis("off")
            detalle_errores.append({
                "ruta": ruta_imagen,
                "real": CLASES[reales[k]],
                "predicha": CLASES[predichas[k]],
                "confianza": float(confianzas[k]),
            })
        fig.tight_layout()
        fig.savefig(os.path.join(CARPETA_SALIDAS, "tres_errores.png"), dpi=120)
        plt.close(fig)

    # Tiempo de inferencia (solo preprocesamiento + modelo, una imagen a la vez)
    muestra = dataset[indices_test[0]][0].unsqueeze(0)
    with torch.no_grad():
        for _ in range(5):   # calentamiento
            modelo(muestra)
        inicio = time.perf_counter()
        repeticiones = 50
        for _ in range(repeticiones):
            modelo(muestra)
        ms = (time.perf_counter() - inicio) / repeticiones * 1000
    print(f"Tiempo de inferencia promedio: {ms:.2f} ms")

    # Matriz de confusión
    fig, eje = plt.subplots(figsize=(8, 6))
    im = eje.imshow(matriz, cmap="Blues")
    eje.set_xticks(range(len(CLASES)), CLASES, rotation=45, ha="right")
    eje.set_yticks(range(len(CLASES)), CLASES)
    eje.set_xlabel("predicha")
    eje.set_ylabel("real")
    for a in range(len(CLASES)):
        for b in range(len(CLASES)):
            eje.text(b, a, matriz[a, b], ha="center", va="center",
                     color="white" if matriz[a, b] > matriz.max() / 2 else "black", fontsize=7)
    fig.colorbar(im)
    fig.tight_layout()
    fig.savefig(os.path.join(CARPETA_SALIDAS, "matriz_confusion.png"), dpi=120)
    plt.close(fig)

    resultados = {
        "accuracy": float(acc),
        "macro_f1": float(macro_f1),
        "umbral": umbral,
        "confusion_frecuente": confusion_frecuente,
        "errores": detalle_errores,
        "tiempo_inferencia_ms": round(ms, 3),
        "epoca_checkpoint": ckpt.get("epoca"),
        "hiperparametros": ckpt.get("hiperparametros"),
        "por_clase": classification_report(
            reales, predichas, target_names=CLASES, output_dict=True
        ),
    }
    with open(os.path.join(CARPETA_SALIDAS, "resultados_test.json"), "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=2)
    with open(os.path.join(CARPETA_SALIDAS, "informe_test.txt"), "w", encoding="utf-8") as f:
        f.write(f"Accuracy: {acc:.4f}\nMacro F1: {macro_f1:.4f}\n\n{informe}")
    print(f"Resultados guardados en {CARPETA_SALIDAS}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["val", "test"], required=True)
    args = parser.parse_args()

    modelo, ckpt = cargar_modelo()
    if args.split == "val":
        probs, reales = obtener_probabilidades(modelo, ckpt, "val")
        calibrar_umbral(probs.max(axis=1), probs.argmax(axis=1) == reales)
    else:
        evaluar_test(modelo, ckpt)
