"""Swagger UI servido con archivos locales (sin CDN).

Se sirve en GET /docs. El contrato lo genera FastAPI en /openapi.json y esta
página solo lo dibuja: no hay documentación escrita a mano que se pueda
desincronizar del código.
"""

PAGINA_DOCS = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GeoScene AI · Swagger UI</title>
<link rel="stylesheet" href="/estaticos/swagger-ui.css">
<style>
  body{margin:0;background:#fafafa;font-family:system-ui,-apple-system,Segoe UI,sans-serif}
  .barra{display:flex;gap:18px;align-items:center;padding:10px 18px;background:#04070c;
         color:#d8e6f2;font:12px ui-monospace,SFMono-Regular,Menlo,monospace;letter-spacing:.1em}
  .barra b{letter-spacing:.2em}
  .barra a{color:#2ee6a8;text-decoration:none}
  .barra .sep{color:#33475b}
</style>
</head>
<body>
<div class="barra">
  <b>GEOSCENE AI · API 1.4.0</b>
  <span class="sep">|</span>
  <a href="/openapi.json">openapi.json</a>
  <span class="sep">|</span>
  <a href="/panel">Panel en vivo</a>
  <span class="sep">|</span>
  <a href="/panel#procedencia">Auditoría</a>
</div>
<div id="swagger-ui"></div>
<script src="/estaticos/swagger-ui-bundle.js"></script>
<script>
  window.ui = SwaggerUIBundle({
    url: '/openapi.json',
    dom_id: '#swagger-ui',
    deepLinking: true,
    presets: [SwaggerUIBundle.presets.apis],
    layout: 'BaseLayout',
    docExpansion: 'list',
    defaultModelsExpandDepth: 1,
    displayRequestDuration: true,
    filter: true,
    tryItOutEnabled: true,
    persistAuthorization: true,
  });
</script>
</body>
</html>
"""
