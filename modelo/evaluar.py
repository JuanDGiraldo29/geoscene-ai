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
from datetime import datetime

import matplotlib
matplotlib.use("Agg")  # guarda las figuras en archivos, sin abrir ventanas
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

# Regla de revisión: de las imágenes que NO se marcan, queremos que al menos
# este porcentaje esté bien clasificado. Es una decisión del equipo: justifíquenla en la ficha.
OBJETIVO_PRECISION = 0.90
MIN_IMAGENES = 30  # con menos imágenes aceptadas, el porcentaje no es fiable


def cargar_modelo():
    """Reconstruye la red con los pesos guardados."""
    ckpt = leer_checkpoint(RUTA_MODELO)
    modelo = GeoSceneCNN()
    modelo.load_state_dict(ckpt["state_dict"])
    modelo.eval()  # desactiva el dropout: imprescindible para evaluar
    return modelo, ckpt


def obtener_probabilidades(modelo, ckpt, nombre_particion):
    """Devuelve (probabilidades, etiquetas_reales) de una partición ("val" o "test")."""
    dataset = cargar_eurosat(crear_transformacion(ckpt["media"], ckpt["desviacion"]))
    cargador = DataLoader(Subset(dataset, cargar_indices()[nombre_particion]), batch_size=256)

    probabilidades, reales = [], []
    with torch.no_grad():
        for X, y in cargador:
            probabilidades.append(torch.softmax(modelo(X), dim=1))  # logits -> probabilidades
            reales.append(y)
    return torch.cat(probabilidades).numpy(), torch.cat(reales).numpy()


def guardar_figura(figura, nombre):
    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    ruta = os.path.join(CARPETA_SALIDAS, nombre)
    figura.tight_layout()
    figura.savefig(ruta, dpi=120)
    plt.close(figura)
    print(f"Guardado: {ruta}")


def calibrar_umbral(confianzas, aciertos):
    """Decide con VALIDACIÓN a partir de qué confianza conviene revisar una predicción.

    Para cada umbral t entre 0.30 y 0.99:
      - cobertura: fracción de imágenes con confianza >= t (las que NO se marcan)
      - precisión: accuracy de esas imágenes
    Se elige el umbral más bajo que alcance OBJETIVO_PRECISION.
    """
    tabla = []
    for umbral in np.round(np.arange(0.30, 0.991, 0.01), 2):
        aceptadas = confianzas >= umbral
        cantidad = int(aceptadas.sum())
        if cantidad < MIN_IMAGENES:
            break
        tabla.append({
            "umbral": float(umbral),
            "cobertura": cantidad / len(confianzas),
            "precision": float(aciertos[aceptadas].mean()),
        })

    cumplen = [fila for fila in tabla if fila["precision"] >= OBJETIVO_PRECISION]
    if cumplen:
        elegido = cumplen[0]
    else:
        elegido = max(tabla, key=lambda fila: fila["precision"])
        print(f"AVISO: ningún umbral llega a {OBJETIVO_PRECISION:.0%}. "
              "Se usa el de mayor precisión; reconsideren el objetivo.")

    print(f"Accuracy de validación (sin regla de revisión): {aciertos.mean()*100:.2f}%")
    print(f"Umbral elegido: {elegido['umbral']:.2f}")
    print(f"  - Se marcan para revisión: {(1 - elegido['cobertura'])*100:.1f}% de las imágenes")
    print(f"  - Las que NO se marcan tienen accuracy: {elegido['precision']*100:.1f}%")

    # Gráfica: es la evidencia que pide la guía
    figura, eje = plt.subplots(figsize=(7, 4))
    umbrales = [fila["umbral"] for fila in tabla]
    eje.plot(umbrales, [fila["cobertura"] for fila in tabla], label="cobertura (imágenes sin revisión)")
    eje.plot(umbrales, [fila["precision"] for fila in tabla], label="accuracy de las no marcadas")
    eje.axvline(elegido["umbral"], linestyle="--", color="gray", label=f"umbral elegido ({elegido['umbral']:.2f})")
    eje.axhline(OBJETIVO_PRECISION, linestyle=":", color="gray")
    eje.set_xlabel("Umbral de confianza")
    eje.set_title("Regla de revisión (validación)")
    eje.legend()
    guardar_figura(figura, "umbral_validacion.png")

    # Escribe el umbral en el checkpoint: lo leerá el wrapper de la API
    ckpt = leer_checkpoint(RUTA_MODELO)
    ckpt["umbral"] = elegido["umbral"]
    ckpt["umbral_calibrado"] = True
    ckpt["objetivo_precision"] = OBJETIVO_PRECISION
    torch.save(ckpt, RUTA_MODELO)
    print(f"Umbral guardado en {RUTA_MODELO}")


def evaluar_test(modelo, ckpt):
    """Evaluación final. Se ejecuta UNA vez, con el modelo ya elegido."""
    if not ckpt.get("umbral_calibrado"):
        print("Primero calibra el umbral con validación:  python -m modelo.evaluar --split val")
        print("El test no se ha usado.")
        return

    probabilidades, reales = obtener_probabilidades(modelo, ckpt, "test")
    predichas = probabilidades.argmax(axis=1)
    confianzas = probabilidades.max(axis=1)

    exactitud = accuracy_score(reales, predichas)
    f1_macro = f1_score(reales, predichas, average="macro")
    print(f"\nAccuracy global: {exactitud*100:.2f}%")
    print(f"Macro F1:        {f1_macro:.4f}")

    # Resultados por clase
    reporte = classification_report(reales, predichas, target_names=CLASES, output_dict=True, zero_division=0)
    print(f"\n{'Clase':<22}{'Precisión':>10}{'Recall':>10}{'F1':>10}")
    for clase in CLASES:
        r = reporte[clase]
        print(f"{clase:<22}{r['precision']:>10.3f}{r['recall']:>10.3f}{r['f1-score']:>10.3f}")

    # Matriz de confusión y la confusión más frecuente
    matriz = confusion_matrix(reales, predichas, labels=range(len(CLASES)))
    fuera_diagonal = matriz.copy()
    np.fill_diagonal(fuera_diagonal, 0)
    i, j = np.unravel_index(fuera_diagonal.argmax(), fuera_diagonal.shape)
    print(f"\nConfusión más frecuente: real {CLASES[i]} -> predicho {CLASES[j]} ({fuera_diagonal[i, j]} veces)")

    figura, eje = plt.subplots(figsize=(8, 7))
    eje.imshow(matriz, cmap="Blues")
    eje.set_xticks(range(len(CLASES)), CLASES, rotation=45, ha="right")
    eje.set_yticks(range(len(CLASES)), CLASES)
    for fila in range(len(CLASES)):
        for columna in range(len(CLASES)):
            color = "white" if matriz[fila, columna] > matriz.max() / 2 else "black"
            eje.text(columna, fila, matriz[fila, columna], ha="center", va="center", color=color, fontsize=8)
    eje.set_xlabel("Predicho")
    eje.set_ylabel("Real")
    eje.set_title("Matriz de confusión (test)")
    guardar_figura(figura, "matriz_confusion.png")

    # Tres errores reales: los de mayor confianza (los que más engañaron al modelo)
    dataset_original = cargar_eurosat()  # imágenes sin transformar, solo para mostrarlas
    indices_test = cargar_indices()["test"]
    errores = np.flatnonzero(predichas != reales)
    errores = errores[np.argsort(-confianzas[errores])][:3]

    figura, ejes = plt.subplots(1, 3, figsize=(12, 4.5))
    for eje, posicion in zip(ejes, errores):
        imagen, _ = dataset_original[indices_test[posicion]]
        eje.imshow(imagen)
        eje.set_title(f"Real: {CLASES[reales[posicion]]}\nPredicho: {CLASES[predichas[posicion]]} "
                      f"({confianzas[posicion]*100:.0f}%)", fontsize=10)
        eje.axis("off")
        print(f"Error: real {CLASES[reales[posicion]]} -> predicho {CLASES[predichas[posicion]]} "
              f"con confianza {confianzas[posicion]*100:.0f}%")
    guardar_figura(figura, "tres_errores.png")

    # Cómo se comporta la regla de revisión en test
    umbral = ckpt["umbral"]
    marcadas = confianzas < umbral
    acierto = predichas == reales
    print(f"\nRegla de revisión (umbral {umbral:.2f}):")
    print(f"  - Se marcan para revisión: {marcadas.mean()*100:.1f}% de las imágenes")
    print(f"  - Accuracy de las NO marcadas: {acierto[~marcadas].mean()*100:.1f}%")
    print(f"  - Accuracy de las marcadas:    {acierto[marcadas].mean()*100:.1f}%")

    # Tiempo de inferencia por imagen: transformación + modelo + softmax (el camino de la app)
    transformacion = crear_transformacion(ckpt["media"], ckpt["desviacion"])
    tiempos = []
    with torch.no_grad():
        for indice in indices_test[:200]:
            imagen, _ = dataset_original[indice]
            inicio = time.perf_counter()
            torch.softmax(modelo(transformacion(imagen).unsqueeze(0)), dim=1)
            tiempos.append((time.perf_counter() - inicio) * 1000)
    print(f"\nTiempo de inferencia por imagen (CPU, {len(tiempos)} imágenes): "
          f"media {np.mean(tiempos):.2f} ms, p95 {np.percentile(tiempos, 95):.2f} ms")

    # Guarda todo en un JSON y anota la ejecución (el test se usa una sola vez)
    os.makedirs(CARPETA_SALIDAS, exist_ok=True)
    resultados = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "epoca_del_checkpoint": ckpt.get("epoca"),
        "accuracy": round(float(exactitud), 4),
        "macro_f1": round(float(f1_macro), 4),
        "por_clase": {c: {k: round(float(v), 4) for k, v in reporte[c].items()} for c in CLASES},
        "confusion_mas_frecuente": {"real": CLASES[i], "predicho": CLASES[j], "veces": int(fuera_diagonal[i, j])},
        "regla_revision": {
            "umbral": umbral,
            "porcentaje_marcadas": round(float(marcadas.mean()), 4),
            "accuracy_no_marcadas": round(float(acierto[~marcadas].mean()), 4),
            "accuracy_marcadas": round(float(acierto[marcadas].mean()), 4),
        },
        "tiempo_inferencia_ms": {"media": round(float(np.mean(tiempos)), 2),
                                 "p95": round(float(np.percentile(tiempos, 95)), 2)},
    }
    with open(os.path.join(CARPETA_SALIDAS, "metricas_test.json"), "w", encoding="utf-8") as archivo:
        json.dump(resultados, archivo, indent=2, ensure_ascii=False)
    with open(os.path.join(CARPETA_SALIDAS, "ejecuciones_test.log"), "a", encoding="utf-8") as registro:
        registro.write(f"{resultados['fecha']} accuracy={exactitud:.4f} macro_f1={f1_macro:.4f} "
                       f"epoca={ckpt.get('epoca')}\n")
    print(f"\nResultados guardados en {CARPETA_SALIDAS}/metricas_test.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["val", "test"], required=True)
    argumentos = parser.parse_args()

    modelo, ckpt = cargar_modelo()
    if argumentos.split == "val":
        probabilidades, reales = obtener_probabilidades(modelo, ckpt, "val")
        calibrar_umbral(probabilidades.max(axis=1), probabilidades.argmax(axis=1) == reales)
    else:
        evaluar_test(modelo, ckpt)