"""La INTERFAZ.   Responsable: capa de interfaz.

Cómo se ejecuta (desde la carpeta raíz, con la API encendida en otra terminal):
    uvicorn api.main:app --port 8000
    streamlit run interfaz/app.py

La interfaz solo habla con la API por HTTP; no necesita saber nada del modelo.
Formato exacto de cada respuesta: docs/CONTRATO.md
"""
import html
import os

import requests
import streamlit as st

API_URL = os.getenv("GEOSCENE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="GeoScene AI", page_icon="🛰️", layout="wide",
                   initial_sidebar_state="expanded")

# ------------------------------------------------------------------ Sistema visual
# Mismo lenguaje que el panel operativo: fondo oscuro con retícula, tipografía mono,
# etiquetas en mayúsculas y esqueletos de carga con barrido.

CSS = """
<style>
:root{
  --gs-bg:#04070c; --gs-panel:#080d14; --gs-line:#14202c; --gs-line2:#1d2f3f;
  --gs-fg:#d8e6f2; --gs-tenue:#6b8399; --gs-ok:#2ee6a8; --gs-warn:#ffb020; --gs-bad:#ff5c5c;
  --gs-mono:ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace;
}
html, body, .stApp, [data-testid="stSidebar"], [data-testid="stMarkdownContainer"],
[data-testid="stWidgetLabel"], .stButton > button, input, textarea, select {
  font-family: var(--gs-mono) !important;
}
.stApp{
  background:
    radial-gradient(1200px 600px at 80% -10%,rgba(46,230,168,.07),transparent 60%),
    linear-gradient(var(--gs-line) 1px,transparent 1px) 0 0/100% 48px,
    linear-gradient(90deg,var(--gs-line) 1px,transparent 1px) 0 0/48px 100%,
    var(--gs-bg);
  color:var(--gs-fg);
}
[data-testid="stAppViewContainer"]{background:transparent}
[data-testid="stHeader"]{background:rgba(4,7,12,.82);border-bottom:1px solid var(--gs-line2)}
[data-testid="stSidebar"]{background:#060b11;border-right:1px solid var(--gs-line2)}
[data-testid="stSidebar"] *{color:var(--gs-fg)}
[data-testid="stMainBlockContainer"]{max-width:1180px;padding-top:18px}
#MainMenu, footer, [data-testid="stToolbar"]{visibility:hidden}
h1,h2,h3{font-family:var(--gs-mono) !important;font-weight:600 !important;letter-spacing:.14em}
h1{font-size:19px !important}
h2{font-size:13px !important;letter-spacing:.18em !important;color:var(--gs-tenue) !important}
h3{font-size:15px !important}
p,li,label,span{font-size:13px}
a{color:var(--gs-ok)}
.gs-head{display:flex;flex-wrap:wrap;gap:14px;justify-content:space-between;align-items:center;
  border:1px solid var(--gs-line2);background:rgba(8,13,20,.82);padding:14px 18px;margin-bottom:18px}
.gs-marca{display:flex;align-items:center;gap:12px}
.gs-led{width:10px;height:10px;border-radius:50%;background:var(--gs-ok);box-shadow:0 0 12px var(--gs-ok)}
.gs-marca b{display:block;font-size:15px;letter-spacing:.22em}
.gs-marca small{display:block;color:var(--gs-tenue);font-size:9px;letter-spacing:.18em;margin-top:2px}
.gs-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.gs-chip{display:inline-block;border:1px solid var(--gs-line2);padding:3px 8px;font-size:9px;
  letter-spacing:.12em;color:var(--gs-tenue);white-space:nowrap}
.gs-chip.ok{color:var(--gs-ok);border-color:rgba(46,230,168,.45);background:rgba(46,230,168,.08)}
.gs-chip.warn{color:var(--gs-warn);border-color:rgba(255,176,32,.45);background:rgba(255,176,32,.08)}
.gs-link{display:inline-block;color:var(--gs-ok);text-decoration:none;font-size:9px;letter-spacing:.14em;
  border:1px solid rgba(46,230,168,.45);padding:4px 9px}
.gs-link:hover{border-color:var(--gs-ok)}
.gs-flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px;margin:16px 0 6px}
.gs-box{border:1px solid var(--gs-line2);padding:9px 12px;min-width:130px;background:rgba(20,32,44,.25)}
.gs-box.on{border-color:rgba(46,230,168,.5);background:rgba(46,230,168,.06)}
.gs-box b{display:block;font-size:10px;letter-spacing:.1em;font-weight:600}
.gs-box small{color:var(--gs-tenue);font-size:9px}
.gs-arrow{align-self:center;color:var(--gs-ok)}
.gs-card{border:1px solid var(--gs-line2);background:linear-gradient(180deg,rgba(20,32,44,.35),transparent);
  padding:16px 18px;min-width:0}
.gs-label{display:block;color:var(--gs-tenue);font-size:9px;letter-spacing:.18em;margin-bottom:8px}
.gs-big{font-size:34px;letter-spacing:-.01em;line-height:1.1;font-weight:500}
.gs-code{font-size:13px;color:var(--gs-tenue);letter-spacing:.02em}
.gs-sub{color:var(--gs-tenue);font-size:11px;margin-top:8px;line-height:1.6}
.gs-nota{color:var(--gs-tenue);font-size:10px;margin-top:12px;line-height:1.6}
.gs-top3{margin-top:14px}
.gs-row{display:grid;grid-template-columns:190px 1fr 58px;gap:10px;align-items:center;
  padding:6px 0;border-bottom:1px solid rgba(29,47,63,.45)}
.gs-row:last-child{border-bottom:0}
.gs-nom{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}
.gs-bar{height:8px;background:#101a24;display:block}
.gs-bar i{display:block;height:100%}
.gs-num{text-align:right;font-variant-numeric:tabular-nums;font-size:11px}
.gs-alerta{border-left:2px solid var(--gs-line2);padding:8px 12px;margin-top:12px;font-size:11px;line-height:1.6}
.gs-alerta.warn{border-left-color:var(--gs-warn);color:#ffe2b0}
.gs-alerta.ok{border-left-color:var(--gs-ok);color:#bff5e2}
.gs-duo{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.gs-skel{background:linear-gradient(90deg,#0a121a 25%,#17252f 37%,#0a121a 63%);
  background-size:400% 100%;animation:gs-barrido 1.3s ease-in-out infinite;display:block}
@keyframes gs-barrido{0%{background-position:100% 0}100%{background-position:0 0}}
.gs-skel-value{height:34px;width:76%}
.gs-skel-sub{height:9px;width:56%;margin-top:10px}
.gs-skel-bar{height:8px;margin:10px 0;width:100%}
@media (prefers-reduced-motion:reduce){.gs-skel{animation:none;background:#0e1721}}
.stButton > button{font-family:var(--gs-mono) !important;font-size:11px;letter-spacing:.1em;
  text-transform:uppercase;border-radius:0;border:1px solid var(--gs-line2);background:transparent;color:var(--gs-fg)}
.stButton > button:hover{border-color:var(--gs-ok);color:var(--gs-ok)}
.stButton > button[kind="primary"]{background:rgba(46,230,168,.12);border-color:rgba(46,230,168,.6);color:var(--gs-ok)}
[data-testid="stFileUploader"] section{border:1px dashed var(--gs-line2) !important;
  background:rgba(8,13,20,.6) !important;border-radius:0 !important}
[data-testid="stMetric"]{border:1px solid var(--gs-line2);
  background:linear-gradient(180deg,rgba(20,32,44,.35),transparent);padding:12px 14px}
[data-testid="stMetricLabel"]{color:var(--gs-tenue);font-size:9px;letter-spacing:.16em;text-transform:uppercase}
[data-testid="stMetricValue"]{font-size:22px;font-family:var(--gs-mono)}
[data-testid="stAlert"]{border-radius:0}
hr{border-color:var(--gs-line2) !important}
.gs-side-row{display:flex;justify-content:space-between;gap:12px;padding:7px 0;
  border-bottom:1px solid rgba(29,47,63,.45);font-size:11px}
.gs-side-row span{color:var(--gs-tenue)}
.gs-side-row b{font-weight:500}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)

ESQUELETO_PREDICCION = """
<div class="gs-card">
  <span class="gs-label">SUGERENCIA DEL MODELO</span>
  <span class="gs-skel gs-skel-value"></span>
  <span class="gs-skel gs-skel-sub"></span>
  <div style="margin-top:18px">
    <span class="gs-skel gs-skel-bar"></span>
    <span class="gs-skel gs-skel-bar" style="width:72%"></span>
    <span class="gs-skel gs-skel-bar" style="width:48%"></span>
  </div>
</div>
"""

ESQUELETO_DECISION = """
<div class="gs-card">
  <span class="gs-label">REGISTRANDO DECISIÓN</span>
  <span class="gs-skel gs-skel-sub" style="width:40%"></span>
  <div class="gs-duo" style="margin-top:14px">
    <span class="gs-skel gs-skel-value" style="width:90%"></span>
    <span class="gs-skel gs-skel-value" style="width:90%"></span>
  </div>
</div>
"""


# ---------------------------------------------------------------- Comunicación con la API

class ErrorAPI(Exception):
    """Error con un mensaje listo para mostrar a la persona usuaria."""


def llamar_api(metodo, ruta, **argumentos):
    try:
        respuesta = requests.request(metodo, f"{API_URL}{ruta}", timeout=15, **argumentos)
    except requests.exceptions.ConnectionError:
        raise ErrorAPI(f"No se pudo conectar con la API en {API_URL}. "
                       "¿Está encendida? (uvicorn api.main:app --port 8000)")
    except requests.exceptions.Timeout:
        raise ErrorAPI("La API tardó demasiado en responder.")

    try:
        contenido = respuesta.json()
    except ValueError:
        raise ErrorAPI("La API respondió algo inesperado.")

    if respuesta.status_code >= 400:
        detalle = contenido.get("detail", "Error desconocido")
        if isinstance(detalle, list):  # 422: FastAPI devuelve una lista de errores de validación
            detalle = "No se recibió el archivo."
        raise ErrorAPI(str(detalle))
    return contenido


@st.cache_data(ttl=30)
def cargar_info():
    """Las clases y el aviso casi no cambian: no hace falta pedirlos en cada clic."""
    return llamar_api("GET", "/clases"), llamar_api("GET", "/alcance")["aviso"]


# ------------------------------------------------------------------------- Estado

for clave, valor in {"prediccion": None, "decision": None, "imagen": None,
                     "huella": None, "clave_subida": 0}.items():
    st.session_state.setdefault(clave, valor)


def limpiar_resultados():
    st.session_state.update(prediccion=None, decision=None, imagen=None, huella=None)


def clasificar_otra():
    limpiar_resultados()
    st.session_state.clave_subida += 1  # cambia la clave: el cargador de archivos queda vacío


# ----------------------------------------------------------------------- Conexión

try:
    salud = llamar_api("GET", "/health")
    info_clases, aviso = cargar_info()
except ErrorAPI as error:
    st.error(str(error))
    st.stop()

clases = info_clases["clases"]
nombres_es = info_clases["nombres_es"]
modo = "CNN REAL" if salud["modo"] == "real" else "MOCK"


def nombre_es(clase):
    return nombres_es.get(clase, clase)


def nombre(clase):
    return f"{nombre_es(clase)} ({clase})"


def franja_flujo(paso):
    activo = "on"
    return f"""
<div class="gs-flow">
  <div class="gs-box {activo if paso == 1 else ''}"><b>01 · SUBIR</b><small>imagen satelital</small></div>
  <span class="gs-arrow">→</span>
  <div class="gs-box {activo if paso == 2 else ''}"><b>02 · CLASIFICAR</b><small>top-3 + umbral</small></div>
  <span class="gs-arrow">→</span>
  <div class="gs-box {activo if paso == 3 else ''}"><b>03 · DECIDIR</b><small>aceptar o corregir</small></div>
</div>
"""


def tarjeta_prediccion(pred):
    filas = ""
    for i, puntuacion in enumerate(pred["top3"]):
        ancho = max(0.5, min(100.0, puntuacion["confianza"] * 100))
        color = "var(--gs-ok)" if i == 0 else "var(--gs-tenue)"
        filas += (
            '<div class="gs-row">'
            f'<span class="gs-nom">{html.escape(nombre(puntuacion["categoria"]))}</span>'
            f'<span class="gs-bar"><i style="width:{ancho:.1f}%;background:{color}"></i></span>'
            f'<span class="gs-num">{puntuacion["confianza"] * 100:.1f}%</span>'
            "</div>"
        )

    if pred["requiere_revision"]:
        estado = ('<span class="gs-chip warn">REVISIÓN RECOMENDADA</span>', "warn",
                  f"Revisión recomendada: la puntuación principal ({pred['confianza']:.1%}) "
                  f"está por debajo del umbral de {pred['umbral']:.0%}.")
    else:
        estado = ('<span class="gs-chip ok">SOBRE EL UMBRAL</span>', "ok",
                  "La puntuación supera el umbral de revisión. Aun así, revisa el resultado: "
                  "el modelo también se equivoca con puntuaciones altas.")
    chip, tono, mensaje = estado

    return f"""
<div class="gs-card">
  <span class="gs-label">SUGERENCIA DEL MODELO</span>
  <div class="gs-big">{html.escape(nombre_es(pred["categoria"]))}
    <span class="gs-code">({html.escape(pred["categoria"])})</span></div>
  <div class="gs-sub">Confianza principal {pred["confianza"]:.1%} ·
    umbral de revisión {pred["umbral"]:.0%} &nbsp;{chip}</div>
  <div class="gs-top3">{filas}</div>
  <div class="gs-alerta {tono}">{mensaje}</div>
  <div class="gs-nota">La puntuación indica la preferencia del modelo entre las 10 categorías,
    no una certeza.</div>
</div>
"""


# ------------------------------------------------------------------------ Cabecera

st.markdown(f"""
<div class="gs-head">
  <div class="gs-marca">
    <span class="gs-led"></span>
    <div><b>GEOSCENE AI</b><small>CLASIFICACIÓN SATELITAL · REVISIÓN HUMANA</small></div>
  </div>
  <div class="gs-meta">
    <span class="gs-chip ok">API CONECTADA</span>
    <span class="gs-chip">{modo}</span>
    <span class="gs-chip">{len(clases)} CLASES</span>
    <a class="gs-link" href="{API_URL}/panel" target="_blank">PANEL OPERATIVO ↗</a>
  </div>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"""
<div class="gs-marca" style="margin-bottom:14px">
  <span class="gs-led"></span>
  <div><b>GEOSCENE AI</b><small>OPS · v1.3</small></div>
</div>
<div class="gs-side-row"><span>API</span><b>{html.escape(API_URL.replace("http://", ""))}</b></div>
<div class="gs-side-row"><span>MODO</span><b>{modo}</b></div>
<div class="gs-side-row"><span>CLASES</span><b>{len(clases)}</b></div>
<div class="gs-side-row"><span>UMBRAL</span><b>calibrado en validación</b></div>
<div style="margin-top:14px;display:flex;flex-direction:column;gap:8px">
  <a class="gs-link" href="{API_URL}/panel" target="_blank">PANEL OPERATIVO ↗</a>
  <a class="gs-link" href="{API_URL}/docs" target="_blank">SWAGGER UI ↗</a>
</div>
""", unsafe_allow_html=True)
    if salud["modo"] == "mock":
        st.warning("Modo de prueba (mock): las predicciones no son reales.")
    st.caption("Los resultados se guardan en outputs/predicciones.csv y outputs/decisiones.csv.")

# ----------------------------------------------------------------------- Pantalla

st.title("Clasificación de imágenes satelitales")
st.caption("Sugiere el tipo de superficie de una imagen satelital. Tú decides si la sugerencia es correcta.")
st.markdown(f'<div class="gs-alerta">{html.escape(aviso)}</div>', unsafe_allow_html=True)

# 1. Subir la imagen (se aceptan todos los archivos: la API explica si alguno no es válido)
archivo = st.file_uploader("Sube una imagen satelital", key=f"subida_{st.session_state.clave_subida}")

paso = 3 if st.session_state.prediccion else (2 if archivo is not None else 1)
st.markdown(franja_flujo(paso), unsafe_allow_html=True)

if archivo is None:
    limpiar_resultados()  # si se quita el archivo, se descarta lo anterior
    st.stop()

huella = (archivo.name, archivo.size)
if huella != st.session_state.huella:  # imagen nueva: se descarta la predicción anterior
    limpiar_resultados()
    st.session_state.huella = huella
st.session_state.imagen = archivo.getvalue()

# 2. Clasificar (con esqueleto de carga mientras responde la API)
if st.session_state.prediccion is None:
    if st.button("Clasificar imagen", type="primary"):
        hueco = st.empty()
        hueco.markdown(ESQUELETO_PREDICCION, unsafe_allow_html=True)
        try:
            st.session_state.prediccion = llamar_api(
                "POST", "/predict", files={"file": (archivo.name, st.session_state.imagen)})
        except ErrorAPI as error:
            st.error(str(error))
            st.stop()
        st.rerun()
    st.stop()

pred = st.session_state.prediccion

# 3. Sugerencia del modelo
columna_imagen, columna_resultado = st.columns([1, 2])

with columna_imagen:
    st.image(st.session_state.imagen, caption=archivo.name, width=250)

with columna_resultado:
    st.markdown(tarjeta_prediccion(pred), unsafe_allow_html=True)

st.divider()

# 4. Aceptar o corregir
st.subheader("Tu decisión")

if st.session_state.decision is None:
    opcion = st.radio("¿La categoría sugerida es correcta?",
                      ["Aceptar la sugerencia", "Corregir la categoría"], horizontal=True)
    categoria_humana = pred["categoria"]
    if opcion == "Corregir la categoría":
        otras = [c for c in clases if c != pred["categoria"]]
        categoria_humana = st.selectbox("Categoría correcta", otras, format_func=nombre)

    if st.button("Registrar decisión", type="primary"):
        hueco = st.empty()
        hueco.markdown(ESQUELETO_DECISION, unsafe_allow_html=True)
        try:
            st.session_state.decision = llamar_api("POST", "/decision", json={
                "id_prediccion": pred["id_prediccion"], "categoria_humana": categoria_humana})
        except ErrorAPI as error:
            st.error(str(error))
            st.stop()
        st.rerun()
else:
    # 5. Predicción del modelo y decisión humana, SIEMPRE por separado
    decision = st.session_state.decision
    estado = "ACEPTADA" if decision["estado"] == "aceptada" else "CORREGIDA"
    tono = "ok" if decision["estado"] == "aceptada" else "warn"
    st.markdown(f"""
<div class="gs-card">
  <span class="gs-label">REGISTRO · PREDICCIÓN Y DECISIÓN SEPARADAS</span>
  <div class="gs-duo">
    <div>
      <span class="gs-label">PREDICCIÓN DEL MODELO</span>
      <div class="gs-big" style="font-size:22px">{html.escape(nombre_es(decision["categoria_modelo"]))}
        <span class="gs-code">({html.escape(decision["categoria_modelo"])})</span></div>
    </div>
    <div>
      <span class="gs-label">DECISIÓN HUMANA</span>
      <div class="gs-big" style="font-size:22px">{html.escape(nombre_es(decision["decision_humana"]))}
        <span class="gs-code">({html.escape(decision["decision_humana"])})</span></div>
    </div>
  </div>
  <div class="gs-sub"><span class="gs-chip {tono}">{estado}</span>
    &nbsp;Ambas quedan registradas por separado. La corrección no reentrena el modelo.</div>
</div>
""", unsafe_allow_html=True)
    st.button("Clasificar otra imagen", on_click=clasificar_otra)
