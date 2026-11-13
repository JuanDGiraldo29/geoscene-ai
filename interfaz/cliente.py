import os

import requests

API_URL = os.getenv("GEOSCENE_API_URL", "http://localhost:8000")


class ErrorAPI(Exception):
    pass


def llamar_api(metodo, ruta, **argumentos):
    try:
        respuesta = requests.request(metodo, f"{API_URL}{ruta}", timeout=15, **argumentos)
    except requests.exceptions.ConnectionError:
        raise ErrorAPI(
            f"No se pudo conectar con la API en {API_URL}. "
            "¿Está encendida? (uvicorn api.main:app --port 8000)"
        )
    except requests.exceptions.Timeout:
        raise ErrorAPI("La API tardó demasiado en responder.")

    try:
        contenido = respuesta.json()
    except ValueError:
        raise ErrorAPI("La API respondió algo inesperado.")

    if respuesta.status_code >= 400:
        detalle = contenido.get("detail", "Error desconocido")
        if isinstance(detalle, list):
            detalle = "No se recibió el archivo."
        raise ErrorAPI(str(detalle))

    return contenido


def cargar_info():
    return llamar_api("GET", "/clases"), llamar_api("GET", "/alcance")["aviso"]
