from html import escape
from string import Template

import streamlit as st

TOKENS = {
    "bg": "#04070c",
    "panel": "#080d14",
    "line": "#14202c",
    "line2": "#1d2f3f",
    "fg": "#d8e6f2",
    "tenue": "#6b8399",
    "ok": "#2ee6a8",
    "warn": "#ffb020",
    "bad": "#ff5c5c",
    "mono": 'ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace',
    "ancho": "1180px",
}

PLANTILLA = """
<style>
:root{
  --gs-bg:${bg}; --gs-panel:${panel}; --gs-line:${line}; --gs-line2:${line2};
  --gs-fg:${fg}; --gs-tenue:${tenue}; --gs-ok:${ok}; --gs-warn:${warn}; --gs-bad:${bad};
  --gs-mono:${mono}; --gs-ancho:${ancho};
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
[data-testid="stHeader"], .stAppHeader, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stAppDeployButton"],
[data-testid="stStatusWidget"], #MainMenu, footer{display:none !important}
[data-testid="stMainBlockContainer"]{max-width:var(--gs-ancho);padding-top:22px !important;
  padding-bottom:40px !important}
[data-testid="stMain"]{padding-top:0 !important}
[data-testid="stSidebar"]{background:var(--gs-panel);border-right:1px solid var(--gs-line2);
  color:var(--gs-fg)}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] label{color:var(--gs-fg)}
[data-testid="stSidebarHeader"]{padding:12px 14px}
[data-testid="stSidebarContent"]{padding-top:0}
[data-testid="stSidebarCollapseButton"] button{color:var(--gs-tenue) !important}
[data-testid="stCaptionContainer"]{color:var(--gs-tenue)}
h1,h2,h3{font-family:var(--gs-mono) !important;font-weight:600 !important;letter-spacing:.14em}
h1{font-size:19px !important}
h2{font-size:13px !important;letter-spacing:.18em !important;color:var(--gs-tenue) !important}
h3{font-size:15px !important}
p,li,label,span{font-size:13px}
a{color:var(--gs-ok)}
.gs-head{display:flex;flex-wrap:wrap;gap:14px;justify-content:space-between;align-items:center;
  border:1px solid var(--gs-line2);background:rgba(8,13,20,.82);padding:14px 18px;margin:0 0 18px}
.gs-marca{display:flex;align-items:center;gap:12px}
.gs-led{width:10px;height:10px;border-radius:50%;background:var(--gs-ok);
  box-shadow:0 0 12px var(--gs-ok)}
.gs-marca b{display:block;font-size:15px;letter-spacing:.22em}
.gs-marca small{display:block;color:var(--gs-tenue);font-size:9px;letter-spacing:.18em;margin-top:2px}
.gs-meta{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.gs-chip{display:inline-block;border:1px solid var(--gs-line2);padding:3px 8px;font-size:9px;
  letter-spacing:.12em;color:var(--gs-tenue);white-space:nowrap}
.gs-chip.ok{color:var(--gs-ok);border-color:rgba(46,230,168,.45);background:rgba(46,230,168,.08)}
.gs-chip.warn{color:var(--gs-warn);border-color:rgba(255,176,32,.45);
  background:rgba(255,176,32,.08)}
.gs-link{display:inline-block;color:var(--gs-ok);text-decoration:none;font-size:9px;
  letter-spacing:.14em;border:1px solid rgba(46,230,168,.45);padding:4px 9px}
.gs-link:hover{border-color:var(--gs-ok)}
.gs-flow{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px;margin:16px 0 6px}
.gs-box{border:1px solid var(--gs-line2);padding:9px 12px;min-width:130px;background:rgba(20,32,44,.25)}
.gs-box.on{border-color:rgba(46,230,168,.5);background:rgba(46,230,168,.06)}
.gs-box b{display:block;font-size:10px;letter-spacing:.1em;font-weight:600}
.gs-box small{color:var(--gs-tenue);font-size:9px}
.gs-arrow{align-self:center;color:var(--gs-ok)}
.gs-card{border:1px solid var(--gs-line2);
  background:linear-gradient(180deg,rgba(20,32,44,.35),transparent);padding:16px 18px;min-width:0}
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
.gs-alerta{border-left:2px solid var(--gs-line2);padding:8px 12px;margin-top:12px;
  font-size:11px;line-height:1.6}
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
  text-transform:uppercase;border-radius:0;border:1px solid var(--gs-line2);
  background:transparent;color:var(--gs-fg)}
.stButton > button:hover{border-color:var(--gs-ok);color:var(--gs-ok)}
.stButton > button[kind="primary"]{background:rgba(46,230,168,.12);
  border-color:rgba(46,230,168,.6);color:var(--gs-ok)}
[data-testid="stFileUploader"] section{border:1px dashed var(--gs-line2) !important;
  background:rgba(8,13,20,.6) !important;border-radius:0 !important}
[data-testid="stImage"] img{border:1px solid var(--gs-line2);image-rendering:pixelated}
[data-testid="stRadio"] [role="radiogroup"] label{border:1px solid var(--gs-line2);
  padding:6px 10px;margin-right:6px}
[data-baseweb="select"] > div{border-radius:0 !important;border-color:var(--gs-line2) !important;
  background:rgba(8,13,20,.6) !important}
[data-testid="stMetric"]{border:1px solid var(--gs-line2);
  background:linear-gradient(180deg,rgba(20,32,44,.35),transparent);padding:12px 14px}
[data-testid="stMetricLabel"]{color:var(--gs-tenue);font-size:9px;letter-spacing:.16em;
  text-transform:uppercase}
[data-testid="stMetricValue"]{font-size:22px;font-family:var(--gs-mono)}
[data-testid="stAlert"]{border-radius:0}
hr{border-color:var(--gs-line2) !important}
.gs-side-row{display:flex;justify-content:space-between;gap:12px;padding:7px 0;
  border-bottom:1px solid rgba(29,47,63,.45);font-size:11px}
.gs-side-row span{color:var(--gs-tenue)}
.gs-side-row b{font-weight:500}
</style>
"""


def css(tokens=None):
    return Template(PLANTILLA).substitute(**(tokens or TOKENS))


def inyectar(tokens=None):
    st.markdown(css(tokens), unsafe_allow_html=True)


def _nombre(clase, etiquetas):
    return f"{escape(etiquetas.get(clase, clase))} ({escape(clase)})"


def cabecera(modo, n_clases, api_url):
    return f"""
<div class="gs-head">
  <div class="gs-marca">
    <span class="gs-led"></span>
    <div><b>GEOSCENE AI</b><small>CLASIFICACIÓN SATELITAL · REVISIÓN HUMANA</small></div>
  </div>
  <div class="gs-meta">
    <span class="gs-chip ok">API CONECTADA</span>
    <span class="gs-chip">{escape(modo)}</span>
    <span class="gs-chip">{int(n_clases)} CLASES</span>
    <a class="gs-link" href="{escape(api_url)}/panel" target="_blank">PANEL OPERATIVO ↗</a>
    <a class="gs-link" href="{escape(api_url)}/panel#procedencia" target="_blank">AUDITORÍA ↗</a>
  </div>
</div>
"""


def panel_lateral(api_url, modo, n_clases):
    host = escape(api_url.replace("http://", "").replace("https://", ""))
    return f"""
<div class="gs-marca" style="margin-bottom:14px">
  <span class="gs-led"></span>
  <div><b>GEOSCENE AI</b><small>OPS · v1.4</small></div>
</div>
<div class="gs-side-row"><span>API</span><b>{host}</b></div>
<div class="gs-side-row"><span>MODO</span><b>{escape(modo)}</b></div>
<div class="gs-side-row"><span>CLASES</span><b>{int(n_clases)}</b></div>
<div class="gs-side-row"><span>UMBRAL</span><b>calibrado en validación</b></div>
<div style="margin-top:14px;display:flex;flex-direction:column;gap:8px">
  <a class="gs-link" href="{escape(api_url)}/panel" target="_blank">PANEL OPERATIVO ↗</a>
  <a class="gs-link" href="{escape(api_url)}/docs" target="_blank">SWAGGER UI ↗</a>
  <a class="gs-link" href="{escape(api_url)}/panel#procedencia" target="_blank">AUDITORÍA ↗</a>
</div>
"""


def aviso(texto):
    return f'<div class="gs-alerta">{escape(texto)}</div>'


def franja(paso):
    return f"""
<div class="gs-flow">
  <div class="gs-box {'on' if paso == 1 else ''}"><b>01 · SUBIR</b><small>imagen satelital</small></div>
  <span class="gs-arrow">→</span>
  <div class="gs-box {'on' if paso == 2 else ''}"><b>02 · CLASIFICAR</b><small>top-3 + umbral</small></div>
  <span class="gs-arrow">→</span>
  <div class="gs-box {'on' if paso == 3 else ''}"><b>03 · DECIDIR</b><small>aceptar o corregir</small></div>
</div>
"""


def esqueleto_prediccion():
    return """
<div class="gs-card" role="status" aria-live="polite" aria-busy="true">
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


def esqueleto_decision():
    return """
<div class="gs-card" role="status" aria-live="polite" aria-busy="true">
  <span class="gs-label">REGISTRANDO DECISIÓN</span>
  <span class="gs-skel gs-skel-sub" style="width:40%"></span>
  <div class="gs-duo" style="margin-top:14px">
    <span class="gs-skel gs-skel-value" style="width:90%"></span>
    <span class="gs-skel gs-skel-value" style="width:90%"></span>
  </div>
</div>
"""


def tarjeta_espera():
    return """
<div class="gs-card">
  <span class="gs-label">LISTO PARA CLASIFICAR</span>
  <div class="gs-sub">Pulsa <b>Clasificar imagen</b> para obtener el top-3 y el umbral de revisión.</div>
  <div class="gs-nota">La imagen ya está cargada. La inferencia se ejecuta en la API, no en el navegador.</div>
</div>
"""


def tarjeta_prediccion(pred, etiquetas):
    filas = ""
    for i, puntuacion in enumerate(pred["top3"]):
        ancho = max(0.5, min(100.0, puntuacion["confianza"] * 100))
        color = "var(--gs-ok)" if i == 0 else "var(--gs-tenue)"
        filas += (
            '<div class="gs-row">'
            f'<span class="gs-nom">{_nombre(puntuacion["categoria"], etiquetas)}</span>'
            f'<span class="gs-bar"><i style="width:{ancho:.1f}%;background:{color}"></i></span>'
            f'<span class="gs-num">{puntuacion["confianza"] * 100:.1f}%</span>'
            "</div>"
        )

    if pred["requiere_revision"]:
        chip = '<span class="gs-chip warn">REVISIÓN RECOMENDADA</span>'
        tono = "warn"
        mensaje = (
            f"Revisión recomendada: la puntuación principal ({pred['confianza']:.1%}) "
            f"está por debajo del umbral de {pred['umbral']:.0%}."
        )
    else:
        chip = '<span class="gs-chip ok">SOBRE EL UMBRAL</span>'
        tono = "ok"
        mensaje = (
            "La puntuación supera el umbral de revisión. Aun así, revisa el resultado: "
            "el modelo también se equivoca con puntuaciones altas."
        )

    return f"""
<div class="gs-card">
  <span class="gs-label">SUGERENCIA DEL MODELO</span>
  <div class="gs-big">{escape(etiquetas.get(pred["categoria"], pred["categoria"]))}
    <span class="gs-code">({escape(pred["categoria"])})</span></div>
  <div class="gs-sub">Confianza principal {pred["confianza"]:.1%} ·
    umbral de revisión {pred["umbral"]:.0%} &nbsp;{chip}</div>
  <div class="gs-top3">{filas}</div>
  <div class="gs-alerta {tono}">{mensaje}</div>
  <div class="gs-nota">La puntuación indica la preferencia del modelo entre las 10 categorías,
    no una certeza.</div>
</div>
"""


def tarjeta_decision(decision, etiquetas):
    estado = "ACEPTADA" if decision["estado"] == "aceptada" else "CORREGIDA"
    tono = "ok" if decision["estado"] == "aceptada" else "warn"
    return f"""
<div class="gs-card">
  <span class="gs-label">REGISTRO · PREDICCIÓN Y DECISIÓN SEPARADAS</span>
  <div class="gs-duo">
    <div>
      <span class="gs-label">PREDICCIÓN DEL MODELO</span>
      <div class="gs-big" style="font-size:22px">
        {_nombre(decision["categoria_modelo"], etiquetas)}</div>
    </div>
    <div>
      <span class="gs-label">DECISIÓN HUMANA</span>
      <div class="gs-big" style="font-size:22px">
        {_nombre(decision["decision_humana"], etiquetas)}</div>
    </div>
  </div>
  <div class="gs-sub"><span class="gs-chip {tono}">{estado}</span>
    &nbsp;Ambas quedan registradas por separado. La corrección no reentrena el modelo.</div>
</div>
"""
