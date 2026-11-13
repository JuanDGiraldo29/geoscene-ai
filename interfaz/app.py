"""La INTERFAZ.   Responsable: capa de interfaz.

Cómo se ejecuta (desde la carpeta raíz, con la API encendida en otra terminal):
    uvicorn api.main:app --port 8000
    streamlit run interfaz/app.py

La interfaz solo habla con la API por HTTP; no necesita saber nada del modelo.
Formato exacto de cada respuesta: docs/CONTRATO.md
"""
import os

import requests
import streamlit as st

API_URL = os.getenv("GEOSCENE_API_URL", "http://localhost:8000")

st.set_page_config(page_title="GeoScene AI", page_icon="🛰️")


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


def nombre(clase):
    return f"{nombres_es.get(clase, clase)} ({clase})"


with st.sidebar:
    st.success("API conectada")
    if salud["modo"] == "mock":
        st.warning("Modo de prueba (mock): las predicciones no son reales.")
    st.caption("Los resultados se guardan en outputs/predicciones.csv y outputs/decisiones.csv.")

# ----------------------------------------------------------------------- Pantalla

st.title("GeoScene AI")
st.caption("Sugiere el tipo de superficie de una imagen satelital. Tú decides si la sugerencia es correcta.")
st.info(aviso)

# 1. Subir la imagen (se aceptan todos los archivos: la API explica si alguno no es válido)
archivo = st.file_uploader("Sube una imagen satelital", key=f"subida_{st.session_state.clave_subida}")

if archivo is None:
    limpiar_resultados()  # si se quita el archivo, se descarta lo anterior
    st.stop()

huella = (archivo.name, archivo.size)
if huella != st.session_state.huella:  # imagen nueva: se descarta la predicción anterior
    limpiar_resultados()
    st.session_state.huella = huella
st.session_state.imagen = archivo.getvalue()

# 2. Clasificar
if st.session_state.prediccion is None:
    if st.button("Clasificar imagen", type="primary"):
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
    st.subheader("Sugerencia del modelo")
    st.markdown(f"### {nombre(pred['categoria'])}")
    st.write("Las tres categorías con mayor puntuación:")
    for puntuacion in pred["top3"]:
        st.progress(puntuacion["confianza"],
                    text=f"{nombre(puntuacion['categoria'])}: {puntuacion['confianza']:.1%}")

    if pred["requiere_revision"]:
        st.warning(f"Revisión recomendada: la puntuación principal ({pred['confianza']:.1%}) "
                   f"está por debajo del umbral de {pred['umbral']:.0%}.")
    else:
        st.caption("La puntuación supera el umbral de revisión. Aun así, revisa el resultado: "
                   "el modelo también se equivoca con puntuaciones altas.")
    st.caption("La puntuación indica la preferencia del modelo entre las 10 categorías, no una certeza.")

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
    izquierda, derecha = st.columns(2)
    izquierda.metric("Predicción del modelo", nombre(decision["categoria_modelo"]))
    derecha.metric("Decisión humana", nombre(decision["decision_humana"]))
    if decision["estado"] == "aceptada":
        st.success("Aceptaste la sugerencia del modelo.")
    else:
        st.success("Corregiste la sugerencia del modelo.")
    st.caption("Ambas quedan registradas por separado. La corrección no reentrena el modelo.")
    st.button("Clasificar otra imagen", on_click=clasificar_otra)