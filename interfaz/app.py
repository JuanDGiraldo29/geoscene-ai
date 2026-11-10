"""La INTERFAZ.   Responsable: tu compañera.

Cómo se ejecuta (desde la carpeta raíz, con la API encendida):
    streamlit run interfaz/app.py

La interfaz solo habla con la API por HTTP (librería requests); no necesita
saber nada del modelo. Mientras no exista el modelo real, la API responde
con el mock, así que se puede construir todo desde hoy.
Formato exacto de cada respuesta: docs/CONTRATO.md

Lo que pide la guía que la persona pueda hacer:
  1. Cargar una imagen (y ver un error claro si el archivo no es válido).
  2. Ver la categoría sugerida y las tres con mayor puntuación.
  3. Ver una señal de revisión cuando la predicción es incierta.
  4. Aceptar la sugerencia o elegir otra de las 10 clases.
     Siempre se muestran por separado la predicción del modelo y la decisión humana.
  5. Leer el aviso de alcance.
"""
import requests
import streamlit as st

API_URL = "http://localhost:8000"

st.set_page_config(page_title="GeoScene AI")
st.title("GeoScene AI")

# TODO 1: pedir el aviso de alcance a la API (GET /alcance) y mostrarlo con st.info(...)

# TODO 2: comprobar con GET /health que la API responde. Si no, mostrar st.error con un
#         mensaje útil ("¿está encendida la API?") y detener la app con st.stop().
#         Si "modo" es "mock", avisar que las predicciones no son reales.

archivo = st.file_uploader("Imagen satelital")

# TODO 3: cuando haya un archivo, un botón "Clasificar imagen" que lo envíe a POST /predict:
#         requests.post(f"{API_URL}/predict", files={"file": (archivo.name, archivo.getvalue())})
#         Si la API responde 400, mostrar el mensaje de error que viene en ["detail"].
#         Guardar el resultado en st.session_state (Streamlit se re-ejecuta en cada clic).

# TODO 4: mostrar la imagen, la categoría sugerida y las tres mejores con su porcentaje
#         (st.progress sirve para barras). Si "requiere_revision" es True, mostrar una
#         advertencia con st.warning. Aclarar que el porcentaje NO es certeza.

# TODO 5: pantalla de confirmación: st.radio ("Aceptar" / "Corregir") y, si corrige,
#         st.selectbox con las 10 clases (GET /clases). Botón "Registrar decisión" ->
#         POST /decision con {"id_prediccion": ..., "categoria_humana": ...}.

# TODO 6: tras registrar, mostrar lado a lado "Predicción del modelo" y "Decisión humana",
#         e indicar que corregir NO reentrena el modelo. Botón para clasificar otra imagen.
