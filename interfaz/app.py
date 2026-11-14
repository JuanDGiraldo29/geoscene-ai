import sys
import time
from pathlib import Path

import streamlit as st

# Streamlit ejecuta interfaz/app.py con su propia carpeta en sys.path, no la
# raíz del repositorio. El límite de subida vive en compartido/constantes.py,
# que es el mismo que aplica la API.
RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import cliente
import ui
from compartido.constantes import TAMANO_MAXIMO_BYTES, TAMANO_MAXIMO_MB

st.set_page_config(page_title="GeoScene AI", page_icon="🛰️", layout="wide",
                   initial_sidebar_state="expanded")

ui.inyectar()

MINIMO_ESQUELETO = 0.55


@st.cache_data(ttl=30)
def cargar_info():
    return cliente.cargar_info()


for clave, valor in {"prediccion": None, "decision": None, "imagen": None,
                     "huella": None, "clave_subida": 0}.items():
    st.session_state.setdefault(clave, valor)


def limpiar_resultados():
    st.session_state.update(prediccion=None, decision=None, imagen=None, huella=None)


def clasificar_otra():
    limpiar_resultados()
    st.session_state.clave_subida += 1


def pausa_esqueleto(inicio, minimo=MINIMO_ESQUELETO):
    restante = minimo - (time.monotonic() - inicio)
    if restante > 0:
        time.sleep(restante)


try:
    salud = cliente.llamar_api("GET", "/health")
    info_clases, aviso = cargar_info()
except cliente.ErrorAPI as error:
    st.error(str(error))
    st.stop()

clases = info_clases["clases"]
nombres_es = info_clases["nombres_es"]
modo = "MODO REAL" if salud["modo"] == "real" else "MOCK"


def nombre(clase):
    return f"{nombres_es.get(clase, clase)} ({clase})"


st.markdown(ui.cabecera(modo, len(clases), cliente.API_URL), unsafe_allow_html=True)

with st.sidebar:
    st.markdown(ui.panel_lateral(cliente.API_URL, modo, len(clases)), unsafe_allow_html=True)
    if salud["modo"] == "mock":
        st.warning("Modo de prueba (mock): las predicciones no son reales.")
    st.caption("Los resultados se guardan en outputs/predicciones.csv y outputs/decisiones.csv.")

st.title("Clasificación de imágenes satelitales")
st.caption("Sugiere el tipo de superficie de una imagen satelital. Tú decides si la sugerencia es correcta.")
st.markdown(ui.aviso(aviso), unsafe_allow_html=True)

archivo = st.file_uploader(
    "Sube una imagen satelital",
    key=f"subida_{st.session_state.clave_subida}",
    help=f"Máximo {TAMANO_MAXIMO_MB} MB por imagen (JPG o PNG). La API aplica el mismo límite.",
)

if archivo is not None and archivo.size > TAMANO_MAXIMO_BYTES:
    pesa_mb = archivo.size / (1024 * 1024)
    st.error(
        f"La imagen pesa {pesa_mb:.1f} MB y el máximo es {TAMANO_MAXIMO_MB} MB. "
        "Comprímela o recórtala antes de subirla."
    )
    st.stop()

paso = 3 if st.session_state.prediccion else (2 if archivo is not None else 1)
st.markdown(ui.franja(paso), unsafe_allow_html=True)

if archivo is None:
    limpiar_resultados()
    st.stop()

huella = (archivo.name, archivo.size)
if huella != st.session_state.huella:
    limpiar_resultados()
    st.session_state.huella = huella
st.session_state.imagen = archivo.getvalue()

if st.session_state.prediccion is None:
    columna_imagen, columna_resultado = st.columns([1, 2])

    with columna_imagen:
        st.image(st.session_state.imagen, caption=archivo.name, width=320)

    with columna_resultado:
        if st.button("Clasificar imagen", type="primary"):
            hueco = st.empty()
            inicio = time.monotonic()
            hueco.markdown(ui.esqueleto_prediccion(), unsafe_allow_html=True)
            time.sleep(0.12)
            try:
                prediccion = cliente.llamar_api(
                    "POST", "/predict",
                    files={"file": (archivo.name, st.session_state.imagen)})
            except cliente.ErrorAPI as error:
                hueco.empty()
                st.error(str(error))
                st.stop()
            pausa_esqueleto(inicio)
            st.session_state.prediccion = prediccion
            st.rerun()
        else:
            st.markdown(ui.tarjeta_espera(), unsafe_allow_html=True)

    st.stop()

pred = st.session_state.prediccion

columna_imagen, columna_resultado = st.columns([1, 2])

with columna_imagen:
    st.image(st.session_state.imagen, caption=archivo.name, width=320)

with columna_resultado:
    st.markdown(ui.tarjeta_prediccion(pred, nombres_es), unsafe_allow_html=True)

st.divider()

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
        inicio = time.monotonic()
        hueco.markdown(ui.esqueleto_decision(), unsafe_allow_html=True)
        time.sleep(0.12)
        try:
            decision = cliente.llamar_api("POST", "/decision", json={
                "id_prediccion": pred["id_prediccion"], "categoria_humana": categoria_humana})
        except cliente.ErrorAPI as error:
            hueco.empty()
            st.error(str(error))
            st.stop()
        pausa_esqueleto(inicio)
        st.session_state.decision = decision
        st.rerun()
else:
    decision = st.session_state.decision
    st.markdown(ui.tarjeta_decision(decision, nombres_es), unsafe_allow_html=True)
    st.button("Clasificar otra imagen", on_click=clasificar_otra)
