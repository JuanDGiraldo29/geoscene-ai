"""Genera la presentación PDF de GeoScene AI (una diapositiva por página).

Sigue el lenguaje visual del panel del proyecto: fondo oscuro, retícula,
monoespaciada, verde como acento y bordes finos.

Uso:
    python docs/generar_presentacion.py
    python docs/generar_presentacion.py --preview   # además guarda PNG por página
"""
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

# Tokens del panel (api/panel.py e interfaz/ui.py)
BG = "#04070c"
PANEL = "#080d14"
LINE = "#14202c"
LINE2 = "#1d2f3f"
FG = "#d8e6f2"
MUTED = "#6b8399"
OK = "#2ee6a8"
WARN = "#ffb020"
BAD = "#ff5c5c"
BAR_BG = "#101a24"

W, H = 1600, 900  # unidades de la diapositiva
MARGEN = 64

plt.rcParams.update({
    "font.family": "monospace",
    "font.monospace": ["Menlo", "DejaVu Sans Mono"],
    "pdf.fonttype": 42,
})


class Slide:
    def __init__(self, paginas):
        self.fig = plt.figure(figsize=(13.333, 7.5))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, W)
        self.ax.set_ylim(H, 0)  # y crece hacia abajo
        self.ax.axis("off")
        self.paginas = paginas
        self.ax.add_patch(Rectangle((0, 0), W, H, facecolor=BG, edgecolor="none", zorder=0))
        for x in range(0, W + 1, 48):
            self.ax.plot([x, x], [0, H], color=LINE, lw=0.4, alpha=0.55, zorder=1)
        for y in range(0, H + 1, 48):
            self.ax.plot([0, W], [y, y], color=LINE, lw=0.4, alpha=0.55, zorder=1)

    # ---------- primitivas ----------
    def text(self, x, y, s, size=13, color=FG, weight="normal", ha="left",
             va="top", linespacing=1.5, z=6):
        return self.ax.text(x, y, s, fontsize=size, color=color, fontweight=weight,
                            ha=ha, va=va, linespacing=linespacing, zorder=z)

    def envolver(self, texto, ancho, size):
        """Ajusta el texto al ancho disponible (1 unidad ≈ 1 punto de ancho)."""
        maximo = max(10, int(ancho / (size * 1.06)))
        lineas, actual = [], ""
        for palabra in texto.split():
            candidata = (actual + " " + palabra).strip()
            if len(candidata) <= maximo:
                actual = candidata
            else:
                if actual:
                    lineas.append(actual)
                actual = palabra
        if actual:
            lineas.append(actual)
        return "\n".join(lineas)

    def parrafo(self, x, y, texto, ancho, size=12, color=MUTED, **kwargs):
        return self.text(x, y, self.envolver(texto, ancho, size), size, color, **kwargs)

    def rule(self, x1, y1, x2, y2, color=LINE2, lw=0.8, z=4):
        self.ax.plot([x1, x2], [y1, y2], color=color, lw=lw, zorder=z,
                     solid_capstyle="butt")

    def panel(self, x, y, w, h, label=None, borde=LINE2, relleno=PANEL, z=2):
        self.ax.add_patch(Rectangle((x, y), w, h, facecolor=relleno,
                                    edgecolor=borde, lw=0.9, zorder=z))
        if label:
            self.text(x + 16, y + 13, label.upper(), 9, MUTED)

    def kpi(self, x, y, w, h, label, value, sub=None, color=FG, tam=30):
        self.panel(x, y, w, h)
        self.text(x + 18, y + 14, label.upper(), 9, MUTED)
        self.text(x + 18, y + 42, value, tam, color, weight="bold")
        if sub:
            self.text(x + 18, y + h - 24, sub, 9.5, MUTED)

    def chip(self, x, y, s, color=OK, size=9):
        ancho = len(s) * size * 1.05 + 24
        self.ax.add_patch(Rectangle((x, y), ancho, 24, facecolor="none",
                                    edgecolor=color, lw=0.7, alpha=0.75, zorder=5))
        self.text(x + 11, y + 5, s.upper(), size, color)
        return ancho

    def chips(self, x, y, textos, ancho_max, color=OK, size=9, salto=32):
        for texto in textos:
            ancho = len(texto) * size * 1.05 + 24
            if x + ancho > ancho_max:
                x, y = x, y + salto
            self.chip(x, y, texto, color, size)
            x += ancho + 10

    def barra(self, x, y, w, h, fraccion, color=OK):
        self.ax.add_patch(Rectangle((x, y), w, h, facecolor=BAR_BG,
                                    edgecolor="none", zorder=3))
        self.ax.add_patch(Rectangle((x, y), max(1, w * fraccion), h,
                                    facecolor=color, edgecolor="none", zorder=4))

    def flecha(self, x1, y1, x2, y2, color=OK):
        self.ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                          mutation_scale=11, color=color,
                                          lw=1.1, zorder=5))

    def cabecera(self, kicker, titulo, numero):
        self.ax.add_patch(Circle((52, 56), 5, facecolor=OK, edgecolor="none", zorder=6))
        self.text(68, 46, "GEOSCENE AI", 10, OK, weight="bold")
        self.text(68, 64, kicker.upper(), 9, MUTED)
        self.text(1536, 46, f"{numero:02d} / {self.paginas:02d}", 9, MUTED, ha="right")
        self.rule(MARGEN, 88, 1536, 88)
        self.text(MARGEN, 106, titulo, 25, FG, weight="bold")

    def pie(self, s):
        self.rule(MARGEN, 848, 1536, 848)
        self.text(MARGEN, 862, s.upper(), 8.5, MUTED)

    def guardar(self, pdf, ruta_png=None):
        pdf.savefig(self.fig)
        if ruta_png:
            self.fig.savefig(ruta_png, dpi=100, facecolor=BG)
        plt.close(self.fig)


# ---------------------------------------------------------------- diapositivas
def d01_portada(pdf, png):
    s = Slide(14)
    s.ax.add_patch(Circle((MARGEN + 5, 58), 6, facecolor=OK, edgecolor="none", zorder=6))
    s.text(MARGEN + 22, 44, "GEOSCENE AI", 13, OK, weight="bold")
    s.text(MARGEN + 22, 64, "CLASIFICACIÓN DE COBERTURAS · EUROSAT RGB", 9, MUTED)

    s.text(MARGEN, 178, "Lectura preliminar de\nimágenes satelitales", 40, FG,
           weight="bold", linespacing=1.2)
    s.parrafo(MARGEN, 360,
              "Una CNN propia propone una de 10 categorías, señala los casos dudosos "
              "y deja la decisión final a la persona analista.", 760, 13.5, MUTED)

    s.chips(MARGEN, 490, ["RAMA integracion/completa", "CHECKPOINT CERTIFICADO SHA-256",
                          "38 PRUEBAS", "SIN GPU"], 940, OK, 9)

    s.panel(1010, 160, 526, 310)
    s.text(1036, 178, "RENDIMIENTO EN TEST", 9, MUTED)
    s.text(1036, 202, "82,70 %", 54, OK, weight="bold")
    s.text(1036, 300, "accuracy sobre 1.000 imágenes", 11, MUTED)
    s.rule(1036, 330, 1500, 330, LINE)
    s.text(1036, 346, "82,44 %", 27, FG, weight="bold")
    s.text(1250, 354, "macro F1", 10.5, MUTED)
    s.text(1036, 398, "97,50 %", 27, FG, weight="bold")
    s.text(1250, 406, "top-3", 10.5, MUTED)
    s.text(1036, 446, "173 errores · 53 sin marcar", 10, MUTED)

    s.panel(1010, 496, 526, 150)
    s.text(1036, 512, "MODELO ENTREGADO", 9, MUTED)
    s.text(1036, 536, "CNN 32 / 64 canales", 16, FG, weight="bold")
    s.text(1036, 570, "545.098 parámetros · 2,1 MB · época 20", 11, MUTED)
    s.text(1036, 594, "umbral de revisión 0,73 · sin BatchNorm", 11, MUTED)

    s.rule(MARGEN, 700, 1536, 700)
    s.text(MARGEN, 720, "FICHA EJECUTIVA", 9, MUTED)
    s.text(MARGEN, 742, "Noviembre de 2026", 13, FG)
    s.text(1536, 720, "API · PANEL · SWAGGER LOCALES", 9, MUTED, ha="right")
    s.text(1536, 742, "127.0.0.1:8000", 13, FG, ha="right")
    s.guardar(pdf, png)


def d02_problema(pdf, png):
    s = Slide(14)
    s.cabecera("Problema y usuario", "Qué resuelve y para quién", 2)

    s.parrafo(MARGEN, 176,
              "Un equipo de análisis territorial recibe imágenes satelitales y tiene que "
              "organizarlas por tipo de superficie. Hacerlo una por una es lento y "
              "propenso a errores.", 690, 13.5, FG)

    s.panel(MARGEN, 316, 700, 200, "LA HERRAMIENTA")
    s.parrafo(MARGEN + 18, 348,
              "Hace una primera lectura de cada imagen, propone una categoría y marca "
              "los casos que no son claros para que el analista los revise con calma.",
              660, 12.5)

    s.panel(MARGEN, 540, 700, 180, "PARA QUIÉN")
    s.parrafo(MARGEN + 18, 572,
              "Analista de imágenes que necesita cargar una imagen, ver la categoría "
              "propuesta y confirmarla o corregirla antes de registrarla.", 660, 12.5)

    s.panel(820, 176, 716, 330, "LO QUE NO ES")
    for i, (titulo, detalle) in enumerate([
        ("No es cartografía", "no produce mapas ni geometrías"),
        ("No decide por su cuenta", "la última palabra es humana"),
        ("No conoce fuera de EuroSAT", "siempre responde una de 10 clases"),
    ]):
        y = 226 + i * 78
        s.text(842, y, "×", 14, BAD, weight="bold")
        s.text(866, y, titulo, 14, FG, weight="bold")
        s.text(866, y + 24, detalle, 11.5, MUTED)

    s.panel(820, 540, 716, 180, "FLUJO DE DECISIÓN")
    for i, (titulo, detalle) in enumerate([
        ("SUGIERE", "categoría + confianza + top-3"),
        ("MARCA", "confianza < 0,73 → revisión"),
        ("DECIDE", "la persona acepta o corrige"),
    ]):
        y = 574 + i * 44
        s.text(842, y, titulo, 10.5, OK, weight="bold")
        s.text(980, y, detalle, 11.5, MUTED)

    s.pie("Herramienta de apoyo · no sustituye la evaluación territorial")
    s.guardar(pdf, png)


def d03_flujo(pdf, png):
    s = Slide(14)
    s.cabecera("Cómo funciona", "Del archivo a la decisión humana", 3)

    cajas = [
        ("01", "IMAGEN", "JPG o PNG\nmáx. 10 MB"),
        ("02", "API", "32×32 + normalización\nmedia y desviación"),
        ("03", "CNN", "logits de 10 clases\n545.098 parámetros"),
        ("04", "SOFTMAX", "probabilidades\ntop-3"),
        ("05", "UMBRAL", "0,73\ncalibrado en validación"),
    ]
    ancho, alto, sep = 262, 150, 36
    x0 = MARGEN
    for i, (num, titulo, detalle) in enumerate(cajas):
        x = x0 + i * (ancho + sep)
        s.panel(x, 200, ancho, alto)
        s.text(x + 16, 214, num, 10, OK, weight="bold")
        s.text(x + 16, 240, titulo, 16, FG, weight="bold")
        s.text(x + 16, 276, detalle, 10, MUTED)
        if i < 4:
            s.flecha(x + ancho + 6, 275, x + ancho + sep - 8, 275)

    # bifurcación del umbral
    s.rule(1432, 350, 1432, 400, OK, 1.0)
    s.rule(414, 400, 1178, 400, OK, 1.0)
    s.flecha(414, 400, 414, 424, OK)
    s.flecha(1178, 400, 1178, 424, WARN)

    s.panel(MARGEN, 430, 700, 150, "CONFIANZA ≥ 0,73")
    s.text(MARGEN + 18, 464, "Sugerencia directa", 17, OK, weight="bold")
    s.text(MARGEN + 18, 500, "La interfaz muestra categoría, confianza y top-3.", 11.5, MUTED)
    s.text(MARGEN + 18, 524, "La persona puede aceptarla o corregirla.", 11.5, MUTED)

    s.panel(820, 430, 716, 150, "CONFIANZA < 0,73")
    s.text(838, 464, "Revisión humana", 17, WARN, weight="bold")
    s.text(838, 500, "La interfaz avisa que conviene revisar.", 11.5, MUTED)
    s.text(838, 524, "26,9 % de las imágenes de test caen aquí.", 11.5, MUTED)

    s.panel(MARGEN, 620, 1472, 160)
    s.text(MARGEN + 18, 638, "CONTRATO ENTRE CAPAS", 9, MUTED)
    s.text(MARGEN + 18, 664,
           "Streamlit solo habla HTTP con FastAPI; nunca importa el modelo.", 13, FG)
    s.text(MARGEN + 18, 694,
           "Predicción y decisión van a outputs/predicciones.csv y outputs/decisiones.csv.", 11.5, MUTED)
    s.text(MARGEN + 18, 718,
           "Corregir no borra lo que dijo el modelo: todo queda auditable.", 11.5, MUTED)
    s.text(MARGEN + 18, 750,
           "El límite de subida es 10 MB, idéntico en la interfaz y en la API.", 11.5, MUTED)

    s.pie("Sin GPU · panel de métricas y Swagger viajan con el proyecto")
    s.guardar(pdf, png)


def d04_dataset(pdf, png):
    s = Slide(14)
    s.cabecera("Datos", "EuroSAT RGB: 27.000 imágenes, 10 clases", 4)

    s.kpi(MARGEN, 170, 340, 130, "Imágenes totales", "27.000", "Sentinel-2 · 64×64 px", tam=30)
    s.kpi(MARGEN + 364, 170, 340, 130, "Clases", "10", "mismo peso en macro F1", tam=30)
    s.kpi(MARGEN + 728, 170, 340, 130, "Semilla", "42", "particiones reproducibles", tam=30)
    s.kpi(MARGEN + 1092, 170, 380, 130, "Resolución", "64×64", "se reduce a 32×32", tam=30)

    total = 7000
    tramos = [("TRAIN", 5000, OK, "500 por clase"),
              ("VALIDACIÓN", 1000, WARN, "100 por clase"),
              ("TEST", 1000, BAD, "100 por clase")]
    x = MARGEN
    for nombre, n, color, detalle in tramos:
        w = 1472 * n / total
        s.ax.add_patch(Rectangle((x, 372), w, 38, facecolor=color, alpha=0.20,
                                 edgecolor=color, lw=0.9, zorder=3))
        s.text(x + 12, 348, nombre, 10, color, weight="bold")
        s.text(x + w - 12, 348, f"{n:,}".replace(",", "."), 12, FG, ha="right", weight="bold")
        s.text(x + 12, 426, detalle, 10, MUTED)
        x += w

    s.panel(MARGEN, 490, 700, 250, "REGLAS DE LA MUESTRA")
    for i, linea in enumerate([
        "500 imágenes por clase para entrenar (5.000).",
        "100 por clase para validación y 100 para test.",
        "Sin imágenes repetidas entre particiones.",
        "La partición se crea una vez y se versiona.",
    ]):
        s.text(MARGEN + 18, 528 + i * 44, "·", 14, OK)
        s.text(MARGEN + 36, 528 + i * 44, linea, 11.5, MUTED)

    s.panel(820, 490, 716, 250, "LAS 10 CLASES")
    clases = ["Cultivo anual", "Bosque", "Vegetación herbácea", "Autopista", "Zona industrial",
              "Pastizal", "Cultivo permanente", "Zona residencial", "Río", "Mar o lago"]
    for i, clase in enumerate(clases):
        col, fila = divmod(i, 5)
        s.text(842 + col * 350, 528 + fila * 40, f"{i + 1:02d}", 9, MUTED)
        s.text(872 + col * 350, 526 + fila * 40, clase, 12, FG)

    s.pie("Particiones idénticas para todos · evaluación honesta")
    s.guardar(pdf, png)


def d05_arquitectura(pdf, png):
    s = Slide(14)
    s.cabecera("Arquitectura", "CNN propia, desde cero y sin pesos preentrenados", 5)

    cajas = [
        ("ENTRADA", "RGB\n3×32×32"),
        ("BLOQUE 1", "Conv 3×3 · 32\nReLU + MaxPool\n32×16×16"),
        ("BLOQUE 2", "Conv 3×3 · 64\nReLU + MaxPool\n64×8×8"),
        ("FLATTEN", "4096\nnúmeros"),
        ("DENSE", "128\nDropout 0,3"),
        ("SALIDA", "10 logits\nsoftmax en API"),
    ]
    ancho, sep = 214, 44
    x0 = 60
    for i, (titulo, detalle) in enumerate(cajas):
        x = x0 + i * (ancho + sep)
        destacado = i in (1, 2)
        s.panel(x, 190, ancho, 160, borde=OK if destacado else LINE2)
        s.text(x + 14, 204, titulo, 10, OK if destacado else MUTED, weight="bold")
        s.text(x + 14, 232, detalle, 12, FG if destacado else MUTED)
        if i < 5:
            s.flecha(x + ancho + 8, 270, x + ancho + sep - 8, 270)

    s.text(MARGEN, 388, "Conteo de parámetros · sin BatchNorm", 12, MUTED)
    filas = [("Conv 3×3 · 3 → 32", "896"), ("Conv 3×3 · 32 → 64", "18.496"),
             ("Dense 4096 → 128", "524.416"), ("Dense 128 → 10", "1.290")]
    for i, (nombre, valor) in enumerate(filas):
        y = 430 + i * 46
        s.rule(MARGEN, y - 12, 760, y - 12, LINE)
        s.text(MARGEN, y, nombre, 12.5, MUTED)
        s.text(760, y, valor, 12.5, FG, ha="right")
    s.rule(MARGEN, 430 + 4 * 46 - 12, 760, 430 + 4 * 46 - 12, LINE2)
    s.text(MARGEN, 430 + 4 * 46 + 6, "TOTAL", 13, OK, weight="bold")
    s.text(760, 430 + 4 * 46 + 6, "545.098", 15, OK, ha="right", weight="bold")

    s.panel(820, 388, 716, 130, "VARIANTE COMPARADA · feature/johan")
    s.text(838, 422, "64 / 128 canales + BatchNorm2d", 12, FG)
    s.text(838, 448, "4.275.978 parámetros · no es el modelo versionado", 11, MUTED)
    s.text(838, 476, "La referencia entregada es 32 / 64, sin BatchNorm.", 11, MUTED)

    s.panel(820, 548, 716, 180, "POR QUÉ ESTA RED")
    for i, linea in enumerate([
        "Dos bloques alcanzan para texturas de 32×32.",
        "Cada capa se puede explicar y auditar.",
        "Entrena y evalúa en CPU, sin GPU.",
        "La variante con BatchNorm es solo comparación.",
    ]):
        s.text(838, 584 + i * 34, "·", 12, OK)
        s.text(856, 584 + i * 34, linea, 11.5, MUTED)

    s.pie("545.098 parámetros · 6.128.896 MACs · 12.257.792 FLOPs por inferencia")
    s.guardar(pdf, png)


def d06_entrenamiento(pdf, png):
    s = Slide(14)
    s.cabecera("Entrenamiento", "Forward, backward y selección por validación", 6)

    s.panel(MARGEN, 170, 560, 350, "HIPERPARÁMETROS EFECTIVOS")
    datos = [("Optimizador", "Adam"), ("Learning rate", "0,001"),
             ("Weight decay", "0,0001"), ("Lote", "64"),
             ("Pérdida", "CrossEntropyLoss"), ("Épocas", "20 fijas"),
             ("Scheduler", "ninguno"), ("Aumento", "giros H y V")]
    for i, (k, v) in enumerate(datos):
        y = 208 + i * 37
        s.text(MARGEN + 18, y, k.upper(), 9, MUTED)
        s.text(MARGEN + 260, y - 2, v, 12.5, FG)

    s.panel(660, 170, 876, 350, "CICLO DE UNA ÉPOCA")
    pasos = ["forward  →  logits [B, 10]", "loss  →  CrossEntropy", "zero_grad",
             "backward  →  ∂L/∂W", "optimizer.step  →  Adam"]
    for i, paso in enumerate(pasos):
        y = 210 + i * 42
        s.text(682, y, f"{i + 1:02d}", 9, OK, weight="bold")
        s.text(710, y - 2, paso, 13, FG)
    s.rule(682, 400, 1500, 400, LINE)
    s.text(682, 414, "VALIDACIÓN DESPUÉS DE CADA ÉPOCA", 9, MUTED)
    s.text(682, 436, "modelo.eval()  +  torch.no_grad()  →  solo forward", 12, MUTED)
    s.text(682, 460, "Se guarda el checkpoint de la mejor accuracy de validación.", 12, MUTED)
    s.text(682, 484, "Dropout 0,3 activo solo en entrenamiento.", 12, MUTED)

    s.kpi(MARGEN, 556, 340, 140, "Época elegida", "20", "de 20 posibles", color=OK, tam=32)
    s.kpi(MARGEN + 364, 556, 340, 140, "Validación", "80,7 %", "accuracy", color=OK, tam=32)
    s.kpi(MARGEN + 728, 556, 340, 140, "Checkpoint", "2,1 MB", "SHA-256 certificado", tam=28)
    s.kpi(MARGEN + 1092, 556, 380, 140, "Pruebas", "38", "pytest · 0 fallos", color=OK, tam=32)

    s.pie("Test no participa en ninguna decisión de entrenamiento")
    s.guardar(pdf, png)


def d07_resultados(pdf, png):
    s = Slide(14)
    s.cabecera("Evaluación", "Resultados en test: 1.000 imágenes, una sola vez", 7)

    s.kpi(MARGEN, 175, 356, 165, "Accuracy top-1", "82,70 %", "827 aciertos de 1.000", color=OK, tam=38)
    s.kpi(MARGEN + 380, 175, 356, 165, "Macro F1", "82,44 %", "10 clases con el mismo peso", tam=38)
    s.kpi(MARGEN + 760, 175, 356, 165, "Top-3", "97,50 %", "top-5 99,60 %", tam=38)
    s.kpi(MARGEN + 1140, 175, 332, 165, "Errores", "173", "53 sin marcar", color=BAD, tam=38)

    s.panel(MARGEN, 385, 1472, 200, "DESAGREGACIÓN")
    filas = [("Pérdida (CrossEntropy)", "0,5055"), ("Precisión macro", "82,71 %"),
             ("Recall macro", "82,70 %"), ("F1 ponderado", "82,44 %"),
             ("Confianza media", "82,53 %")]
    for i, (k, v) in enumerate(filas):
        x = MARGEN + 18 + (i % 3) * 490
        y = 424 + (i // 3) * 76
        s.text(x, y, k.upper(), 9, MUTED)
        s.text(x, y + 18, v, 18, FG, weight="bold")

    s.panel(MARGEN, 618, 1472, 155, "LECTURA")
    s.parrafo(MARGEN + 18, 668,
              "El modelo acierta 8 de cada 10 imágenes y casi siempre pone la clase correcta "
              "entre sus tres primeras opciones. El test se usó una sola vez, con la época y "
              "el umbral ya elegidos en validación.", 1420, 12.5)

    s.pie("Métricas recalculadas en vivo por GET /reporte?split=test")
    s.guardar(pdf, png)


def d08_umbral(pdf, png):
    s = Slide(14)
    s.cabecera("Regla de revisión", "El umbral separa lo seguro de lo dudoso", 8)

    s.panel(MARGEN, 175, 420, 300, "UMBRAL CALIBRADO")
    s.text(MARGEN + 18, 202, "0,73", 58, OK, weight="bold")
    s.text(MARGEN + 18, 322, "confianza < 0,73  →  revisión", 11.5, WARN)
    s.parrafo(MARGEN + 18, 356,
              "Elegido en validación como el valor más bajo con ≥ 90 % de precisión "
              "en las no marcadas.", 380, 11)

    s.kpi(500, 175, 250, 120, "Cobertura", "73,1 %", "sin revisión", tam=24)
    s.kpi(762, 175, 250, 120, "Marcadas", "26,9 %", "1 de cada 3,7", color=WARN, tam=24)
    s.kpi(1024, 175, 250, 120, "Acc. no marcadas", "92,75 %", "cuando confía", color=OK, tam=22)
    s.kpi(1286, 175, 250, 120, "Acc. marcadas", "55,39 %", "cuando duda", color=WARN, tam=22)

    s.panel(MARGEN, 500, 716, 200, "COMPORTAMIENTO")
    s.text(MARGEN + 18, 532, "No marcadas", 11.5, MUTED)
    s.barra(250, 536, 400, 12, 0.9275, OK)
    s.text(670, 532, "92,75 %", 12.5, OK, weight="bold")
    s.text(MARGEN + 18, 578, "Marcadas", 11.5, MUTED)
    s.barra(250, 582, 400, 12, 0.5539, WARN)
    s.text(670, 578, "55,39 %", 12.5, WARN, weight="bold")
    s.text(MARGEN + 18, 636, "La regla reduce el riesgo, pero no lo elimina.", 11.5, MUTED)

    s.panel(820, 500, 716, 200, "LÍMITE DE LA REGLA", borde=BAD)
    s.text(838, 528, "53 de 173 errores", 23, BAD, weight="bold")
    s.text(838, 570, "tenían confianza ≥ 0,73 y no se habrían", 11.5, FG)
    s.text(838, 594, "marcado (30,6 % de todos los errores).", 11.5, FG)
    s.text(838, 634, "Una confianza alta no garantiza acierto.", 11.5, MUTED)

    s.text(MARGEN, 730,
           "Subir el umbral reduce la cobertura y aumenta la fiabilidad; bajarlo hace lo contrario.",
           11, MUTED)

    s.pie("Objetivo de calibración: ≥ 90 % de precisión en las no marcadas")
    s.guardar(pdf, png)


def d09_clases(pdf, png):
    s = Slide(14)
    s.cabecera("Desagregación", "Resultados por clase en test", 9)

    filas = [
        ("Bosque", 0.941, 0.960, 0.951), ("Zona industrial", 0.929, 0.920, 0.925),
        ("Mar o lago", 0.938, 0.900, 0.918), ("Zona residencial", 0.902, 0.920, 0.911),
        ("Pastizal", 0.870, 0.870, 0.870), ("Cultivo anual", 0.837, 0.870, 0.853),
        ("Río", 0.752, 0.790, 0.771), ("Vegetación herbácea", 0.677, 0.860, 0.758),
        ("Cultivo permanente", 0.736, 0.670, 0.702), ("Autopista", 0.689, 0.510, 0.586),
    ]

    s.text(MARGEN, 168, "CLASE", 9, MUTED)
    s.text(520, 168, "PRECISIÓN", 9, MUTED, ha="right")
    s.text(660, 168, "RECALL", 9, MUTED, ha="right")
    s.text(800, 168, "F1", 9, MUTED, ha="right")
    s.text(860, 168, "F1 POR CLASE", 9, MUTED)
    s.rule(MARGEN, 186, 1472, 186, LINE2)

    for i, (clase, p, r, f1) in enumerate(filas):
        y = 206 + i * 52
        color = OK if f1 >= 0.85 else (WARN if f1 >= 0.70 else BAD)
        s.text(MARGEN, y, clase, 13, FG)
        s.text(520, y, f"{p:.3f}".replace(".", ","), 12.5, MUTED, ha="right")
        s.text(660, y, f"{r:.3f}".replace(".", ","), 12.5, MUTED, ha="right")
        s.text(800, y, f"{f1:.3f}".replace(".", ","), 13, color, ha="right", weight="bold")
        s.barra(860, y + 2, 610, 12, f1, color)
        s.rule(MARGEN, y + 34, 1472, y + 34, LINE)

    s.panel(MARGEN, 742, 1472, 88)
    s.text(MARGEN + 16, 758,
           "Bosque e industria son las más fáciles. Autopista es la más débil: encuentra 51 de 100.\n"
           "Vegetación herbácea tiene recall alto (0,86) pero precisión baja (0,677): atrae confusiones.",
           11.5, MUTED)

    s.pie("100 imágenes por clase · soporte balanceado")
    s.guardar(pdf, png)


def d10_matriz(pdf, png):
    s = Slide(14)
    s.cabecera("Matriz de confusión", "Dónde se equivoca el modelo", 10)

    clases = ["Cultivo anual", "Bosque", "Veg. herbácea", "Autopista", "Industrial",
              "Pastizal", "Cultivo perm.", "Residencial", "Río", "Mar o lago"]
    matriz = [
        [87, 0, 2, 1, 0, 2, 4, 0, 3, 1],
        [0, 96, 0, 0, 0, 2, 0, 0, 0, 2],
        [0, 0, 86, 3, 0, 1, 6, 0, 4, 0],
        [7, 0, 13, 51, 3, 1, 10, 3, 12, 0],
        [0, 0, 1, 1, 92, 0, 2, 4, 0, 0],
        [3, 3, 2, 2, 0, 87, 1, 0, 2, 0],
        [1, 0, 19, 5, 0, 3, 67, 3, 2, 0],
        [0, 0, 3, 2, 2, 0, 1, 92, 0, 0],
        [2, 1, 1, 9, 2, 3, 0, 0, 79, 3],
        [4, 2, 0, 0, 0, 1, 0, 0, 3, 90],
    ]

    ax = s.fig.add_axes([MARGEN / W, 1 - 720 / H, 760 / W, 470 / H])
    mapa = LinearSegmentedColormap.from_list("gs", ["#08111a", "#0d3d31", OK])
    ax.imshow(matriz, cmap=mapa, vmin=0, vmax=100)
    ax.set_xticks(range(10))
    ax.set_yticks(range(10))
    ax.set_xticklabels(clases, rotation=45, ha="right", fontsize=6.2, color=MUTED)
    ax.set_yticklabels(clases, fontsize=6.2, color=MUTED)
    ax.tick_params(colors=LINE2, length=0)
    for lado in ax.spines.values():
        lado.set_color(LINE2)
    for i in range(10):
        for j in range(10):
            valor = matriz[i][j]
            if valor:
                ax.text(j, i, valor, ha="center", va="center", fontsize=6.4,
                        color="#04110d" if valor > 45 else FG)
    ax.set_xlabel("predicho", fontsize=7, color=MUTED, labelpad=6)
    ax.set_ylabel("real", fontsize=7, color=MUTED, labelpad=6)

    s.panel(920, 165, 616, 250, "ACIERTOS POR CLASE")
    diagonales = [87, 96, 86, 51, 92, 87, 67, 92, 79, 90]
    for i, (clase, valor) in enumerate(zip(clases, diagonales)):
        col, fila = divmod(i, 5)
        x = 940 + col * 300
        y = 202 + fila * 38
        color = OK if valor >= 85 else (WARN if valor >= 70 else BAD)
        s.text(x, y, clase, 9.5, MUTED)
        s.text(x + 250, y, str(valor), 11, color, ha="right", weight="bold")

    s.panel(920, 450, 616, 315, "AUTOPISTA · 51 ACIERTOS, 49 ERRORES")
    fila = [("Vegetación herbácea", 13), ("Río", 12), ("Cultivo permanente", 10),
            ("Cultivo anual", 7), ("Industrial", 3), ("Residencial", 3), ("Pastizal", 1)]
    for i, (destino, n) in enumerate(fila):
        y = 486 + i * 34
        s.text(940, y, destino, 10.5, MUTED)
        s.barra(1190, y + 2, 200, 10, n / 20, BAD)
        s.text(1400, y, str(n), 11, FG, ha="right", weight="bold")
    s.text(940, 732, "Franja delgada: a 32×32 ocupa pocos píxeles.", 10, MUTED)

    s.pie("827 aciertos de 1.000 · diagonal principal")
    s.guardar(pdf, png)


def d11_errores(pdf, png):
    s = Slide(14)
    s.cabecera("Errores representativos", "Los tres fallos de mayor confianza", 11)

    errores = [
        ("01", "Río  →  Autopista", "99,79 %",
         "Forma de franja y agua grisácea: a 32×32 domina la geometría."),
        ("02", "Río  →  Zona industrial", "97,84 %",
         "El patrón del cauce se confunde con superficies construidas."),
        ("03", "Pastizal  →  Veg. herbácea", "97,29 %",
         "Clases vecinas: la diferencia de textura casi desaparece."),
    ]
    for i, (num, titulo, conf, detalle) in enumerate(errores):
        x = MARGEN + i * 496
        s.panel(x, 170, 470, 300)
        s.text(x + 16, 184, num, 10, MUTED, weight="bold")
        s.text(x + 16, 208, titulo, 13, FG, weight="bold")
        s.text(x + 16, 240, conf, 28, BAD, weight="bold")
        s.text(x + 16, 304, "NO MARCADO", 9, BAD, weight="bold")
        s.parrafo(x + 16, 330, detalle, 436, 10.5)
        s.text(x + 16, 424, "supera el umbral 0,73", 10, MUTED)

    s.panel(MARGEN, 496, 700, 220, "UN CASO QUE SÍ ATRAPÓ EL UMBRAL", borde=OK)
    s.text(MARGEN + 18, 538, "Zona residencial  →  Cultivo permanente", 13, FG, weight="bold")
    s.text(MARGEN + 18, 568, "30,05 %", 28, OK, weight="bold")
    s.text(MARGEN + 18, 630, "MARCADO PARA REVISIÓN", 9, OK, weight="bold")
    s.parrafo(MARGEN + 18, 656,
              "La persona ve el aviso, revisa el top-3 y corrige a residencial.",
              660, 11)

    s.panel(820, 496, 716, 220, "LECTURA")
    s.text(838, 540, "Los tres errores de mayor confianza", 12, FG)
    s.text(838, 564, "superaron el umbral y no se marcaron.", 12, FG)
    s.text(838, 604, "53 de 173 errores (30,6 %) están en esa zona.", 11.5, MUTED)
    s.parrafo(838, 630,
              "Por eso el aviso de alcance y la revisión humana siguen siendo "
              "obligatorios.", 680, 11.5)

    s.pie("Imágenes reales de test · outputs/tres_errores.png")
    s.guardar(pdf, png)


def d12_dominio(pdf, png):
    s = Slide(14)
    s.cabecera("Limitación", "El modelo no sabe decir «no lo conozco»", 12)

    casos = [
        ("BLANCA", "Mar o lago", "91,78 %"),
        ("NEGRA", "Veg. herbácea", "99,98 %"),
        ("RUIDO", "Zona residencial", "100,00 %"),
    ]
    for i, (nombre, pred, conf) in enumerate(casos):
        x = MARGEN + i * 400
        s.panel(x, 180, 376, 200)
        s.text(x + 16, 194, nombre, 9, MUTED)
        s.text(x + 16, 220, "→ " + pred, 15, FG, weight="bold")
        s.text(x + 16, 258, conf, 30, WARN, weight="bold")
        s.text(x + 16, 320, "confianza alta · no se marcó", 9, MUTED)

    s.panel(MARGEN, 410, 700, 260, "QUÉ SIGNIFICA")
    s.parrafo(MARGEN + 18, 446,
              "El modelo solo conoce las 10 clases de EuroSAT. Cualquier imagen recibe "
              "una de ellas, aunque no tenga nada que ver.", 660, 12)
    s.parrafo(MARGEN + 18, 536,
              "La confianza solo tiene sentido dentro de ese dominio: fuera de él puede "
              "ser altísima y estar completamente equivocada.", 660, 12)

    s.panel(820, 410, 716, 260, "CONSECUENCIA PARA EL USO")
    s.text(838, 446, "El aviso de alcance es obligatorio:", 12.5, FG)
    s.parrafo(838, 476,
              "«Es una clasificación visual preliminar y no debe usarse sola para "
              "decisiones de ordenamiento territorial o ambientales.»", 670, 11.5)
    s.text(838, 576, "La interfaz y /alcance lo muestran siempre.", 11.5, OK)

    s.panel(MARGEN, 700, 1472, 120, "MEDIDO CON EL CHECKPOINT ENTREGADO", borde=WARN)
    s.text(MARGEN + 18, 748,
           "Tres imágenes sintéticas fuera de dominio: blanca, negra y ruido uniforme.", 11.5, MUTED)
    s.text(MARGEN + 18, 774,
           "Ninguna quedó marcada para revisión por el umbral.", 11.5, MUTED)

    s.pie("Una clase de rechazo o detección OOD queda como mejora pendiente")
    s.guardar(pdf, png)


def d13_riesgo(pdf, png):
    s = Slide(14)
    s.cabecera("Riesgo y mitigación", "Qué puede salir mal y cómo se controla", 13)

    s.panel(MARGEN, 180, 716, 330, "RIESGO", borde=BAD)
    s.text(MARGEN + 18, 226,
           "Usar una lectura preliminar\ncomo evaluación territorial\nconcluyente.",
           17, FG, weight="bold", linespacing=1.35)
    s.parrafo(MARGEN + 18, 344,
              "El modelo puede acertar el 82,7 % de las veces y aun así equivocarse "
              "con más de 97 % de confianza en una imagen concreta.", 660, 11.5)
    s.text(MARGEN + 18, 436, "53 errores del test no se habrían marcado.", 11.5, BAD)

    s.panel(820, 180, 716, 330, "MITIGACIÓN", borde=OK)
    for i, linea in enumerate([
        "La herramienta solo sugiere; la persona decide.",
        "Umbral 0,73: lo dudoso pasa a revisión.",
        "Top-3 visible para comparar alternativas.",
        "Aviso de alcance siempre en pantalla.",
        "Predicción y decisión registradas por separado.",
    ]):
        y = 216 + i * 44
        s.text(842, y, "✓", 13, OK, weight="bold")
        s.text(866, y - 1, linea, 12, MUTED)

    s.panel(MARGEN, 540, 1472, 230, "DECISIONES TÉCNICAS")
    s.chips(MARGEN + 18, 572, ["CNN propia", "Sin preentrenados", "Sin GPU",
                               "Misma transformación train/app"], 1490, OK, 9)
    s.chips(MARGEN + 18, 612, ["API separada de la interfaz", "Registros separados",
                               "Test usado una vez"], 1490, OK, 9)
    s.text(MARGEN + 18, 690,
           "La época y el umbral se eligieron con validación; el test no se usó para ajustar.",
           11.5, MUTED)

    s.pie("Trazabilidad: SHA-256 del checkpoint y de las particiones")
    s.guardar(pdf, png)


def d14_cierre(pdf, png):
    s = Slide(14)
    s.cabecera("Reproducibilidad", "Cómo verificarlo y qué sigue", 14)

    s.panel(MARGEN, 170, 700, 290, "CERTIFICACIÓN")
    s.text(MARGEN + 18, 208, "SHA-256 DEL CHECKPOINT", 9, MUTED)
    s.text(MARGEN + 18, 234, "e073084a…d58de571", 15, OK, weight="bold")
    s.text(MARGEN + 18, 276, "545.098 parámetros · época 20 · umbral 0,73", 11, MUTED)
    s.text(MARGEN + 18, 302, "2,1 MB · Torch 2.15 · Python 3.15", 11, MUTED)
    s.text(MARGEN + 18, 344, "38 pruebas · 0 fallos", 11, MUTED)
    s.text(MARGEN + 18, 370, "0,21 ms por imagen · 4.819 img/s en CPU", 11, MUTED)
    s.text(MARGEN + 18, 396, "petición HTTP completa: 2–4 ms en local", 11, MUTED)

    s.panel(820, 170, 716, 290, "CÓMO CORRERLO")
    s.text(838, 208, "1  python -m venv .venv && activar", 11, FG)
    s.text(838, 234, "2  pip install -r requirements.txt", 11, FG)
    s.text(838, 260, "3  uvicorn api.main:app --port 8000", 11, FG)
    s.text(838, 286, "4  streamlit run interfaz/app.py", 11, FG)
    s.text(838, 326, "Panel    /panel      Swagger  /docs", 10.5, MUTED)
    s.text(838, 350, "Salud    /health     Reporte  /reporte", 10.5, MUTED)
    s.text(838, 390, "Windows: py -3 y .venv\\Scripts\\activate", 10, MUTED)
    s.text(838, 414, "macOS/Linux: python3 y source .venv/bin/activate", 10, MUTED)

    s.panel(MARGEN, 490, 700, 280, "SIGUIENTE VERSIÓN")
    for i, linea in enumerate([
        "Entrenar a 64×64 (resolución original).",
        "Probar ResNet-18 con fine-tuning.",
        "Añadir clase de rechazo o detección OOD.",
        "Comparar formalmente la variante con BatchNorm.",
    ]):
        s.text(MARGEN + 18, 526 + i * 48, "→", 13, OK)
        s.text(MARGEN + 44, 524 + i * 48, linea, 11.5, MUTED)

    s.panel(820, 490, 716, 280, "FUENTES")
    s.text(838, 522,
           "EuroSAT · Helber et al. (2019)\nIEEE JSTARS · vía torchvision", 10.5, MUTED)
    s.rule(838, 578, 1500, 578, LINE)
    s.text(838, 590,
           "PyTorch · torchvision · scikit-learn · NumPy\nPillow · Matplotlib · FastAPI · Uvicorn\nStreamlit · Swagger UI · pytest", 10.5, MUTED)

    s.rule(MARGEN, 800, 1536, 800, LINE2)
    s.text(MARGEN, 818, "GEOSCENE AI", 12, OK, weight="bold")
    s.text(MARGEN + 180, 820, "Clasificación preliminar de coberturas · la persona decide", 10.5, MUTED)
    s.text(1536, 818, "integracion/completa", 10.5, MUTED, ha="right")

    s.guardar(pdf, png)


def main():
    salida = Path("docs/geoscene_presentacion.pdf")
    previsualizar = "--preview" in sys.argv
    carpeta_png = Path("/private/var/folders/zf/y2xfmrns2gv1b7ys4sr0jq8h0000gn/T/opencode/deck_preview")
    if previsualizar:
        carpeta_png.mkdir(parents=True, exist_ok=True)
    salida.parent.mkdir(parents=True, exist_ok=True)

    diapositivas = [d01_portada, d02_problema, d03_flujo, d04_dataset, d05_arquitectura,
                    d06_entrenamiento, d07_resultados, d08_umbral, d09_clases, d10_matriz,
                    d11_errores, d12_dominio, d13_riesgo, d14_cierre]

    with PdfPages(salida) as pdf:
        for i, funcion in enumerate(diapositivas, start=1):
            png = carpeta_png / f"slide_{i:02d}.png" if previsualizar else None
            funcion(pdf, png)

    print(f"PDF generado: {salida} · {len(diapositivas)} páginas")


if __name__ == "__main__":
    main()
