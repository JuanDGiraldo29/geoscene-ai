"""Panel operativo (estilo centro de control). Sin dependencias ni CDN: un HTML.

Se sirve en GET /panel y consulta GET /reporte cada 20 s. Todo lo que muestra
se calcula en el servidor en el momento de la consulta.
"""

PAGINA = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GeoScene AI · Centro de operaciones</title>
<style>
  :root{
    --bg:#04070c; --panel:#080d14; --line:#14202c; --line2:#1d2f3f;
    --fg:#d8e6f2; --tenue:#6b8399; --ok:#2ee6a8; --warn:#ffb020; --bad:#ff5c5c;
    --mono:ui-monospace,SFMono-Regular,"JetBrains Mono",Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0;background:
      radial-gradient(1200px 600px at 80% -10%,rgba(46,230,168,.07),transparent 60%),
      linear-gradient(var(--line) 1px,transparent 1px) 0 0/100% 48px,
      linear-gradient(90deg,var(--line) 1px,transparent 1px) 0 0/48px 100%,
      var(--bg);
    color:var(--fg);font-family:var(--mono);font-size:13px;min-height:100vh}
  header{display:flex;flex-wrap:wrap;gap:16px;justify-content:space-between;align-items:center;
    padding:18px 26px;border-bottom:1px solid var(--line2);background:rgba(4,7,12,.88);
    position:sticky;top:0;z-index:10;backdrop-filter:blur(10px)}
  .carga{position:fixed;top:0;left:0;height:2px;width:0;background:var(--ok);z-index:20;
    box-shadow:0 0 10px var(--ok);opacity:0;transition:opacity .2s}
  .carga.on{opacity:1;animation:cargando 1.2s ease-in-out infinite}
  @keyframes cargando{0%{width:0}65%{width:88%}100%{width:100%}}
  .revelar{opacity:0;transform:translateY(16px);position:relative;overflow:hidden;
    transition:opacity .62s cubic-bezier(.2,.7,.2,1),transform .62s cubic-bezier(.2,.7,.2,1)}
  .revelar::after{content:"";position:absolute;inset:0;pointer-events:none;opacity:0;
    background:linear-gradient(90deg,transparent,rgba(46,230,168,.06),transparent);
    transform:translateX(-100%)}
  .revelar.visible{opacity:1;transform:none}
  .revelar.visible::after{animation:barrido-revelado .75s ease-out}
  @keyframes barrido-revelado{0%{opacity:.65;transform:translateX(-100%)}
    55%{opacity:.18}100%{opacity:0;transform:translateX(100%)}}
  .fresco{animation:aparecer .5s ease-out}
  @keyframes aparecer{from{opacity:.55}to{opacity:1}}
  section{scroll-margin-top:78px}
  .marca{display:flex;align-items:center;gap:12px}
  .led{width:10px;height:10px;border-radius:50%;background:var(--bad);box-shadow:0 0 12px var(--bad)}
  .led.ok{background:var(--ok);box-shadow:0 0 12px var(--ok)}
  .led.bad{background:var(--bad);box-shadow:0 0 12px var(--bad);animation:pulso 1s infinite}
  @keyframes pulso{50%{opacity:.3}}
  .esqueleto{background:linear-gradient(90deg,#0a121a 25%,#17252f 37%,#0a121a 63%);
    background-size:400% 100%;animation:barrido 1.3s ease-in-out infinite;display:block}
  @keyframes barrido{0%{background-position:100% 0}100%{background-position:0 0}}
  .esq-lin{height:10px;margin:9px 0;width:60%}
  .esq-valor{height:30px;width:76%}
  .esq-sub{height:9px;width:56%;margin-top:10px}
  .esq-matriz{height:300px}
  .lr{width:100%;height:54px;display:block;margin-top:8px}
  .etiqueta{display:block;color:var(--tenue);font-size:9px;letter-spacing:.16em;margin-bottom:4px}
  .split button:disabled{opacity:.4;cursor:progress}
  @media (prefers-reduced-motion:reduce){
    .esqueleto{animation:none;background:#0e1721}
    .revelar{opacity:1;transform:none;transition:none}
    .revelar::after{display:none}
    .carga.on,.fresco{animation:none}
    html{scroll-behavior:auto}
  }
  h1{margin:0;font-size:16px;letter-spacing:.22em;font-weight:600}
  .marca p{margin:3px 0 0;color:var(--tenue);font-size:10px;letter-spacing:.18em}
  .controles{display:flex;align-items:center;gap:18px;flex-wrap:wrap}
  .split{display:flex;border:1px solid var(--line2)}
  .split button{background:transparent;border:0;color:var(--tenue);font-family:var(--mono);
    font-size:10px;letter-spacing:.14em;padding:9px 14px;cursor:pointer}
  .split button.on{background:rgba(46,230,168,.12);color:var(--ok)}
  .enlace{color:var(--ok);text-decoration:none;font-size:10px;letter-spacing:.14em;
    border:1px solid rgba(46,230,168,.45);padding:9px 12px}
  .sello{font-size:9px;letter-spacing:.12em;color:var(--tenue);border:1px solid var(--line2);
    padding:6px 9px;white-space:nowrap}
  .sello.ok{color:var(--ok);border-color:rgba(46,230,168,.45);background:rgba(46,230,168,.08)}
  .sello.bad{color:var(--bad);border-color:rgba(255,92,92,.45);background:rgba(255,92,92,.08)}
  .reloj{text-align:right}
  .reloj span{font-size:18px;letter-spacing:.08em}
  .reloj small{display:block;color:var(--tenue);font-size:9px;letter-spacing:.2em}
  main{padding:22px 26px 40px;display:grid;gap:18px;max-width:1500px;margin:0 auto}
  .alerta{border:1px solid var(--bad);background:rgba(255,92,92,.08);color:#ffd7d7;
    padding:12px 16px;font-size:12px;letter-spacing:.04em}
  .oculto{display:none}
  .kpis{display:grid;grid-template-columns:1.5fr repeat(5,1fr);gap:18px}
  .kpi{border:1px solid var(--line2);background:linear-gradient(180deg,rgba(20,32,44,.35),transparent);
    padding:14px 16px;position:relative;min-height:112px}
  .kpi label{display:block;color:var(--tenue);font-size:9px;letter-spacing:.18em;margin-bottom:10px}
  .kpi .valor{font-size:30px;letter-spacing:-.02em;line-height:1}
  .kpi .sub{color:var(--tenue);font-size:10px;margin-top:8px}
  .kpi .medidor{height:3px;background:#101a24;margin-top:12px}
  .kpi .medidor i{display:block;height:100%;width:0;transition:width .5s}
  .grande{grid-row:span 1}
  .grande .valor{font-size:44px}
  svg.aro{position:absolute;right:14px;top:20px;width:104px;height:58px;opacity:.95}
  .dos{display:grid;grid-template-columns:1fr 1fr;gap:18px}
  .panel{border:1px solid var(--line2);background:rgba(8,13,20,.82);padding:16px 18px;min-width:0}
  .panel h2{margin:0 0 14px;font-size:10px;letter-spacing:.2em;color:var(--tenue);font-weight:600}
  .fila{display:grid;grid-template-columns:150px 1fr 52px 44px;gap:10px;align-items:center;
    padding:5px 0;border-bottom:1px solid rgba(29,47,63,.45)}
  .fila:last-child{border-bottom:0}
  .nom{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}
  .barra{height:7px;background:#101a24}
  .barra i{display:block;height:100%}
  .num{text-align:right;font-variant-numeric:tabular-nums;font-size:11px}
  .tenue{color:var(--tenue)}
  .lin{display:flex;justify-content:space-between;gap:12px;padding:8px 0;
    border-bottom:1px solid rgba(29,47,63,.45);font-size:11px}
  .lin:last-child{border-bottom:0}
  .lin b{color:var(--tenue);font-weight:400}
  .vacio{color:var(--tenue);font-size:11px;margin:6px 0}
  .scroll{overflow-x:auto}
  table.mat{border-collapse:collapse;font-size:9px;margin:0 auto}
  table.mat th{color:var(--tenue);font-weight:400;padding:3px 4px;letter-spacing:.06em}
  table.mat td{width:26px;height:22px;text-align:center;border:1px solid rgba(29,47,63,.55);
    color:#e9f5ff;font-variant-numeric:tabular-nums}
  .duo{display:grid;grid-template-columns:1fr 1fr;gap:14px}
  .duo label{display:block;color:var(--tenue);font-size:9px;letter-spacing:.16em;margin-bottom:4px}
  .duo strong{font-size:24px;font-weight:500}
  .nota{color:var(--tenue);font-size:10px;margin:12px 0 0;line-height:1.6}
  table.datos{width:100%;border-collapse:collapse;font-size:11px}
  table.datos td{padding:5px 0;border-bottom:1px solid rgba(29,47,63,.4)}
  table.datos td:last-child{text-align:right;font-variant-numeric:tabular-nums}
  table.proc{width:100%;border-collapse:collapse;font-size:11px}
  table.proc th{text-align:left;color:var(--tenue);font-size:9px;letter-spacing:.12em;
    font-weight:400;padding:6px 8px;border-bottom:1px solid var(--line2)}
  table.proc td{padding:7px 8px;border-bottom:1px solid rgba(29,47,63,.4);vertical-align:top}
  table.proc td:last-child{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
  table.proc code{font-size:10px}
  .flujo{display:flex;flex-wrap:wrap;align-items:stretch;gap:8px;margin-bottom:16px}
  .caja{border:1px solid var(--line2);padding:9px 12px;min-width:120px;background:rgba(20,32,44,.25)}
  .caja b{display:block;font-size:10px;letter-spacing:.08em;font-weight:600}
  .caja small{color:var(--tenue);font-size:9px}
  .flecha{align-self:center;color:var(--ok);font-size:14px}
  table.mapa{width:100%;border-collapse:collapse;font-size:10px}
  table.mapa th{text-align:left;color:var(--tenue);font-weight:400;letter-spacing:.12em;
    padding:6px 8px;border-bottom:1px solid var(--line2);font-size:9px}
  table.mapa td{padding:7px 8px;border-bottom:1px solid rgba(29,47,63,.4);vertical-align:top}
  .verbo{display:inline-block;padding:2px 6px;border:1px solid var(--line2);font-size:9px;letter-spacing:.08em}
  .get{color:var(--ok);border-color:rgba(46,230,168,.45)}
  .post{color:var(--warn);border-color:rgba(255,176,32,.45)}
  code{color:#a8c7dd;font-size:10px}
  footer{border-top:1px solid var(--line2);padding:14px 26px;color:var(--tenue);
    font-size:9px;letter-spacing:.14em;display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
  @media (max-width:1100px){.kpis{grid-template-columns:repeat(3,1fr)}.dos{grid-template-columns:1fr}}
</style>
</head>
<body>
<div id="carga" class="carga"></div>
<header>
  <div class="marca">
    <span class="led" id="led"></span>
    <div>
      <h1>GEOSCENE AI</h1>
      <p>CENTRO DE OPERACIONES · CLASIFICACIÓN SATELITAL · EUROSAT RGB 32×32</p>
    </div>
  </div>
  <div class="controles">
    <span class="sello" id="sello">SIN VERIFICAR</span>
    <a class="enlace" href="/docs">SWAGGER ↗</a>
    <div class="split">
      <button data-split="val">VALIDACIÓN</button>
      <button data-split="test" class="on">TEST</button>
    </div>
    <div class="reloj"><span id="hora">--:--:--</span><small>UTC</small></div>
  </div>
</header>

<div id="alerta" class="alerta oculto"></div>

<main>
  <section class="kpis">
    <div class="kpi grande">
      <label>ACCURACY GLOBAL</label>
      <div class="valor" id="kAcc">--</div>
      <div class="sub" id="kAccSub">midiendo…</div>
      <div class="medidor"><i id="mAcc"></i></div>
      <svg class="aro" viewBox="0 0 210 120" aria-hidden="true">
        <path d="M20 105 A85 85 0 0 1 190 105" fill="none" stroke="#12202c" stroke-width="9"/>
        <path id="accArc" d="M20 105 A85 85 0 0 1 190 105" fill="none" stroke="#2ee6a8"
              stroke-width="9" stroke-dasharray="0 267" stroke-linecap="butt"/>
      </svg>
    </div>
    <div class="kpi"><label>MACRO F1</label><div class="valor" id="kF1">--</div>
      <div class="sub" id="kF1Sub">10 clases balanceadas</div><div class="medidor"><i id="mF1"></i></div></div>
    <div class="kpi"><label>TOP-3</label><div class="valor" id="kTop3">--</div>
      <div class="sub" id="kTop3Sub">acierto en las 3 primeras</div><div class="medidor"><i id="mTop3"></i></div></div>
    <div class="kpi"><label>COBERTURA</label><div class="valor" id="kCob">--</div>
      <div class="sub" id="kCobSub">sin revisión</div><div class="medidor"><i id="mCob"></i></div></div>
    <div class="kpi"><label>ACC. SIN REVISIÓN</label><div class="valor" id="kSel">--</div>
      <div class="sub" id="kSelSub">objetivo 90%</div><div class="medidor"><i id="mSel"></i></div></div>
    <div class="kpi"><label>LATENCIA P95</label><div class="valor" id="kLat">--</div>
      <div class="sub" id="kLatSub">por imagen</div><div class="medidor"><i id="mLat"></i></div></div>
  </section>

  <section class="panel">
    <h2>MÉTRICAS NUCLEARES DE LA CNN</h2>
    <div id="cnn"></div>
  </section>

  <section class="dos">
    <div class="panel">
      <h2>F1 POR CLASE · RECALL A LA DERECHA</h2>
      <div id="clases"><p class="vacio">midiendo…</p></div>
    </div>
    <div class="panel">
      <h2>MATRIZ DE CONFUSIÓN · REAL → PREDICHO</h2>
      <div id="matriz" class="scroll"><p class="vacio">midiendo…</p></div>
    </div>
  </section>

  <section class="dos">
    <div class="panel">
      <h2>CONFUSIONES MÁS FRECUENTES</h2>
      <div id="confusiones"><p class="vacio">midiendo…</p></div>
    </div>
    <div class="panel">
      <h2>ERRORES DE ALTA CONFIANZA</h2>
      <div id="errores"><p class="vacio">midiendo…</p></div>
    </div>
  </section>

  <section class="dos">
    <div class="panel">
      <h2>REVISIÓN HUMANA · ARCHIVOS SEPARADOS</h2>
      <div id="decisiones"><p class="vacio">leyendo outputs/…</p></div>
    </div>
    <div class="panel">
      <h2>SISTEMA Y MODELO</h2>
      <div id="sistema"><p class="vacio">midiendo…</p></div>
    </div>
  </section>

  <section class="dos">
    <div class="panel">
      <h2>CALIBRACIÓN · ¿LA CONFIANZA DICE LA VERDAD?</h2>
      <div id="calibracion"><p class="vacio">midiendo…</p></div>
    </div>
    <div class="panel">
      <h2>LATENCIA Y RENDIMIENTO</h2>
      <div id="rendimiento"><p class="vacio">midiendo…</p></div>
    </div>
  </section>

  <section class="dos">
    <div class="panel">
      <h2>PARTICIÓN Y BALANCE</h2>
      <div id="particion"><p class="vacio">midiendo…</p></div>
    </div>
    <div class="panel">
      <h2>EVIDENCIA EN DISCO · outputs/</h2>
      <div id="artefactos"><p class="vacio">buscando…</p></div>
    </div>
  </section>

  <section class="panel" id="procedencia">
    <h2>PROCEDENCIA · CERTIFICACIÓN DE DATOS</h2>
    <div id="procedenciaContenido"><p class="vacio">verificando huellas…</p></div>
  </section>

  <section class="panel">
    <h2>MAPA DE CONEXIONES · QUIÉN HABLA CON QUIÉN</h2>
    <div class="flujo">
      <div class="caja"><b>NAVEGADOR / DOCENTE</b><small>:8501 · Streamlit</small></div>
      <span class="flecha">→</span>
      <div class="caja"><b>API FASTAPI</b><small>:8000 · /predict /decision</small></div>
      <span class="flecha">→</span>
      <div class="caja"><b>CHECKPOINT</b><small>models/geoscene_cnn.pt</small></div>
      <span class="flecha">+</span>
      <div class="caja"><b>DATASET</b><small>splits/indices.json + data/</small></div>
    </div>
    <div class="scroll">
    <table class="mapa">
      <thead><tr><th>ORIGEN</th><th>VERBO</th><th>RUTA</th><th>DESTINO / EFECTO</th><th>CUÁNDO</th></tr></thead>
      <tbody>
        <tr><td>Streamlit</td><td><span class="verbo get">GET</span></td><td><code>/health</code></td><td>modo real o mock · LED de conexión</td><td>al abrir la app</td></tr>
        <tr><td>Streamlit</td><td><span class="verbo get">GET</span></td><td><code>/clases</code>, <code>/alcance</code></td><td>catálogo de 10 clases + aviso de alcance</td><td>al abrir la app (caché 30 s)</td></tr>
        <tr><td>Streamlit</td><td><span class="verbo post">POST</span></td><td><code>/predict</code></td><td>imagen → top-3 + umbral · escribe <code>predicciones.csv</code></td><td>al clasificar</td></tr>
        <tr><td>Streamlit</td><td><span class="verbo post">POST</span></td><td><code>/decision</code></td><td>aceptar/corregir · escribe <code>decisiones.csv</code></td><td>al decidir</td></tr>
        <tr><td>Navegador</td><td><span class="verbo get">GET</span></td><td><code>/reporte</code></td><td>recorre la partición y mide todo ahora</td><td>panel, cada consulta</td></tr>
        <tr><td>Navegador</td><td><span class="verbo get">GET</span></td><td><code>/panel</code></td><td>este tablero · refresco 20 s</td><td>al abrirlo</td></tr>
        <tr><td>Docente</td><td><span class="verbo get">GET</span></td><td><code>/docs</code>, <code>/openapi.json</code></td><td>contrato navegable y ejecutable</td><td>al revisar</td></tr>
      </tbody>
    </table>
    </div>
    <p class="nota">La interfaz nunca importa el modelo: solo HTTP + JSON. El checkpoint y el dataset solo los tocan la API y el panel (lectura). El test se mide, no se usa para ajustar hiperparámetros.</p>
  </section>
</main>

<footer>
  <span id="medido">ESPERANDO MEDICIÓN…</span>
  <span id="fuente">FUENTE: —</span>
  <span id="version">REPORTE v— · SIN CACHÉ · CACHE-CONTROL: NO-STORE</span>
  <span id="estadoModo">—</span>
</footer>

<script>
const $ = (id) => document.getElementById(id);
const pct = (v, d = 1) => (v * 100).toFixed(d) + '%';
const color = (v, bueno, medio) => v >= bueno ? 'var(--ok)' : (v >= medio ? 'var(--warn)' : 'var(--bad)');
const LARGO_ARCO = 267;
let split = 'test';

function kpi(id, valor, detalle, tono) {
  const el = $(id);
  el.textContent = valor;
  el.style.color = tono || 'var(--fg)';
  const sub = $('k' + id.slice(1) + 'Sub');  // puede no existir: no romper el resto del panel
  if (detalle !== undefined && sub) sub.textContent = detalle;
}

function medidor(id, v, tono) {
  const el = $(id);
  el.style.width = Math.max(0, Math.min(1, v)) * 100 + '%';
  el.style.background = tono;
}

function filaTabla(pares) {
  return '<table class="datos">' + pares.map(([k, v]) =>
    '<tr><td>' + k + '</td><td>' + v + '</td></tr>').join('') + '</table>';
}

function pintarProcedencia(d) {
  const p = d.procedencia;
  const contenedor = $('procedenciaContenido');
  if (!p) { contenedor.innerHTML = '<p class="vacio">sin datos de procedencia</p>'; return; }
  const corto = (h) => h ? h.slice(0, 18) + '…' : '—';
  const filas = [
    ['MÉTRICAS', d.meta.fuente + ' · ' + d.meta.split.toUpperCase() + ' · ' +
      d.meta.n_imagenes + ' imágenes', d.meta.duracion_ms.toFixed(0) + ' ms'],
    ['CHECKPOINT', p.checkpoint.ruta + ' · ' + p.checkpoint.bytes.toLocaleString('es-CO') +
      ' B · ' + (p.checkpoint.modificado || '—'), corto(p.checkpoint.sha256)],
    ['PARTICIONES', p.indices.ruta + ' · ' + p.indices.bytes.toLocaleString('es-CO') +
      ' B · ' + (p.indices.modificado || '—'), corto(p.indices.sha256)],
    ['DATASET', p.dataset.ruta + ' · ' + p.dataset.imagenes.toLocaleString('es-CO') +
      ' imágenes', 'lectura'],
    ['SALIDAS', p.salidas.predicciones + ' · ' + p.salidas.decisiones, 'CSV'],
    ['SISTEMA', 'Python ' + d.sistema.python + ' · Torch ' + d.sistema.torch + ' · ' +
      d.sistema.device, d.sistema.uptime_s + ' s'],
    ['CÁLCULO', p.calculo, 'en vivo'],
  ];
  const fuentes = Object.entries(p.fuentes || {}).map(([k, v]) =>
    '<div class="lin"><span>' + k + '</span><span class="num tenue">' + v + '</span></div>').join('');
  contenedor.innerHTML =
    '<table class="proc"><thead><tr><th>BLOQUE</th><th>ORIGEN EXACTO</th><th>HUELLA</th></tr></thead><tbody>' +
    filas.map(([k, v, h]) => '<tr><td>' + k + '</td><td>' + v + '</td><td><code>' + h +
      '</code></td></tr>').join('') + '</tbody></table>' +
    '<p class="nota">SHA-256 calculado sobre el contenido exacto. Si el checkpoint o las particiones cambian, ' +
    'la huella cambia. Las métricas no se leen de outputs/: se vuelven a inferir en cada consulta. ' +
    '<a href="/reporte?split=' + d.meta.split + '" target="_blank" style="color:var(--ok)">' +
    '/reporte?split=' + d.meta.split + ' ↗</a></p>' +
    '<div style="margin-top:12px">' + fuentes + '</div>';
}

function pintar(d, animar) {
  const m = d.metricas, r = d.regla_revision, mod = d.modelo, meta = d.meta;

  kpi('kAcc', pct(m.accuracy), m.errores + ' errores / ' + meta.n_imagenes + ' imágenes',
      color(m.accuracy, .85, .78));
  medidor('mAcc', m.accuracy, color(m.accuracy, .85, .78));
  $('accArc').setAttribute('stroke-dasharray', (m.accuracy * LARGO_ARCO).toFixed(1) + ' ' + LARGO_ARCO);
  $('accArc').setAttribute('stroke', color(m.accuracy, .85, .78));

  kpi('kF1', pct(m.macro_f1, 2), (mod.clases || 10) + ' clases · media no ponderada',
      color(m.macro_f1, .82, .75));
  medidor('mF1', m.macro_f1, color(m.macro_f1, .82, .75));

  kpi('kTop3', pct(m.top3), 'acierto en las 3 primeras', color(m.top3, .95, .90));
  medidor('mTop3', m.top3, color(m.top3, .95, .90));

  kpi('kCob', pct(r.cobertura), pct(r.porcentaje_marcadas) + ' marcadas', 'var(--fg)');
  medidor('mCob', r.cobertura, 'var(--ok)');

  const tonoSelectiva = color(r.accuracy_no_marcadas, .90, .85);
  kpi('kSel', pct(r.accuracy_no_marcadas), 'umbral ' + r.umbral.toFixed(2) +
      (mod.objetivo_precision != null ? ' · objetivo ' + pct(mod.objetivo_precision, 0) : ''),
      tonoSelectiva);
  medidor('mSel', r.accuracy_no_marcadas, tonoSelectiva);

  kpi('kLat', d.latencia.ms_por_imagen_p95.toFixed(2) + ' ms', 'media ' + d.latencia.ms_por_imagen_media.toFixed(2) + ' ms');
  medidor('mLat', Math.min(1, 20 / Math.max(20, d.latencia.ms_por_imagen_p95)), 'var(--ok)');

  const clases = Object.entries(d.por_clase).sort((a, b) => b[1].f1 - a[1].f1);
  $('clases').innerHTML = clases.map(([nombre, v]) => {
    const tono = color(v.f1, .85, .75);
    return '<div class="fila">' +
      '<span class="nom" title="' + nombre + '">' + nombre + '</span>' +
      '<span class="barra"><i style="width:' + (v.f1 * 100).toFixed(1) + '%;background:' + tono + '"></i></span>' +
      '<span class="num">' + pct(v.f1, 1) + '</span>' +
      '<span class="num tenue">' + pct(v.recall, 1) + '</span></div>';
  }).join('');

  const matriz = d.confusion.matriz, etiquetas = d.confusion.clases;
  const maximo = Math.max(1, ...matriz.flat());
  let html = '<table class="mat"><thead><tr><th></th>' +
    etiquetas.map((c) => '<th title="' + c + '">' + c.slice(0, 4) + '</th>').join('') + '</tr></thead><tbody>';
  matriz.forEach((fila, i) => {
    html += '<tr><th title="' + etiquetas[i] + '">' + etiquetas[i].slice(0, 4) + '</th>';
    fila.forEach((v, j) => {
      const alfa = 0.06 + 0.5 * (v / maximo);
      const fondo = i === j ? 'rgba(46,230,168,' + alfa + ')' : (v ? 'rgba(255,92,92,' + alfa + ')' : 'transparent');
      html += '<td style="background:' + fondo + '" title="' + etiquetas[i] + ' → ' + etiquetas[j] + ': ' + v + '">' + (v || '') + '</td>';
    });
    html += '</tr>';
  });
  $('matriz').innerHTML = html + '</tbody></table>';

  $('confusiones').innerHTML = d.top_confusiones.length
    ? d.top_confusiones.map((x) => '<div class="lin"><span>' + x.real + ' <b>→</b> ' + x.predicho +
        '</span><span class="num">' + x.veces + '</span></div>').join('')
    : '<p class="vacio">Sin confusiones fuera de la diagonal.</p>';

  $('errores').innerHTML = d.errores_alta_confianza.length
    ? d.errores_alta_confianza.map((e) => '<div class="lin"><span>' + e.real + ' <b>→</b> ' + e.predicho +
        '</span><span class="num" style="color:' + (e.confianza >= .95 ? 'var(--bad)' : 'var(--warn)') + '">' +
        pct(e.confianza) + '</span></div>').join('')
    : '<p class="vacio">Sin errores en esta partición.</p>';

  const dec = d.decisiones;
  $('decisiones').innerHTML = '<div class="duo">' +
    '<div><label>ACEPTADAS</label><strong>' + dec.aceptadas + '</strong></div>' +
    '<div><label>CORREGIDAS</label><strong style="color:var(--warn)">' + dec.corregidas + '</strong></div>' +
    '<div><label>TASA DE CORRECCIÓN</label><strong>' + pct(dec.tasa_correccion) + '</strong></div>' +
    '<div><label>PREDICCIONES</label><strong>' + dec.predicciones_registradas + '</strong></div></div>' +
    '<p class="nota">Última decisión: ' + (dec.ultima_decision || '—') +
    '. La predicción original nunca se sobrescribe: corregir no reentrena.</p>';

  $('sistema').innerHTML = filaTabla([
    ['Checkpoint', mod.checkpoint],
    ['Época · val acc', (mod.epoca ?? '—') + ' · ' + (mod.val_accuracy != null ? pct(mod.val_accuracy) : '—')],
    ['Parámetros', mod.parametros.toLocaleString('es-CO') + ' en ' + mod.arquitectura.length + ' tensores'],
    ['Entrenables', mod.parametros_entrenables.toLocaleString('es-CO')],
    ['Cómputo', (mod.macs / 1e6).toFixed(2) + ' M MACs · ' + (mod.flops / 1e6).toFixed(2) + ' MFLOPs'],
    ['Entrada · clases', mod.entrada.join('×') + ' · ' + mod.clases],
    ['Optimización', (mod.funcion_perdida || 'no declarado') + ' · ' +
      (mod.optimizador || 'no declarado') + ' · ' + (mod.plan_lr || 'no declarado')],
    ['Hiperparámetros', mod.hiperparametros
      ? Object.entries(mod.hiperparametros).map(([k, v]) => k + '=' + v).join(' · ') : '—'],
    ['Dispositivo', mod.device + ' · ' + d.sistema.hilos_torch + ' hilos'],
    ['Torch', d.sistema.torch + ' · Python ' + d.sistema.python],
    ['Umbral', mod.umbral.toFixed(2) + (mod.umbral_calibrado ? ' calibrado' : ' sin calibrar') +
      (mod.objetivo_precision != null ? ' · objetivo ' + pct(mod.objetivo_precision, 0) : '')],
    ['Tamaño checkpoint', d.sistema.tamano_checkpoint_mb + ' MB'],
    ['Uptime API', d.sistema.uptime_s + ' s'],
  ]);

  const hp = mod.hiperparametros || {};
  $('cnn').innerHTML =
    '<div class="dos">' +
      filaTabla([
        ['Pérdida · ' + (mod.funcion_perdida || 'no declarada'), m.perdida.toFixed(4)],
        ['Accuracy (top-1)', pct(m.accuracy, 2)],
        ['Top-3 · top-5', pct(m.top3, 2) + ' · ' + pct(m.top5, 2)],
        ['Errores', m.errores + ' / ' + meta.n_imagenes],
        ['Confianza media', pct(m.confianza_media)],
      ]) +
      filaTabla([
        ['Precisión macro', pct(m.precision_macro, 2)],
        ['Recall macro', pct(m.recall_macro, 2)],
        ['F1 macro', pct(m.macro_f1, 2)],
        ['F1 ponderado', pct(m.f1_weighted, 2)],
        ['Parámetros', mod.parametros.toLocaleString('es-CO')],
      ]) +
    '</div>' +
    '<div class="dos" style="margin-top:14px">' +
      '<div><label class="etiqueta">TASA DE APRENDIZAJE POR ÉPOCA</label>' +
        '<svg class="lr" viewBox="0 0 300 54" preserveAspectRatio="none" aria-label="Tasa de aprendizaje constante">' +
          '<line x1="0" y1="30" x2="300" y2="30" stroke="#12202c" stroke-width="1"/>' +
          '<line x1="0" y1="30" x2="300" y2="30" stroke="#2ee6a8" stroke-width="2"/>' +
          '<text x="6" y="22" fill="#6b8399" font-size="9">lr ' + (mod.tasa_aprendizaje ?? '—') + '</text>' +
        '</svg>' +
        '<p class="nota">' + (mod.plan_lr || 'no declarado') + ' · ' +
          (hp.epocas_max ?? hp.epocas ?? '—') + ' épocas · ' +
          (mod.optimizador || 'no declarado') + '</p></div>' +
      '<p class="nota">Plan declarado: ' + (mod.plan_lr || 'no declarado') +
        '. Si el plan describe un cambio, aquí se vería la curva real.</p>' +
    '</div>' +
    '<p class="nota">Acierto, precisión, recall y F1 se muestran en %; la pérdida queda en escala 0–1.</p>';

  if (d.calibracion) {
    const cal = d.calibracion;
    $('calibracion').innerHTML = filaTabla([
      ['ECE · 10 bins', cal.ece.toFixed(4) + (cal.ece <= 0.05 ? ' · fiable' : ' · sobreconfiado')],
      ['Brier multiclase', cal.brier.toFixed(4)],
      ['Log-loss (NLL)', cal.nll.toFixed(4)],
      ['Confianza media · mediana', pct(cal.confianza_media) + ' · ' + pct(cal.confianza_mediana)],
      ['p10 · p90', pct(cal.confianza_p10) + ' · ' + pct(cal.confianza_p90)],
      ['Entropía media', cal.entropia_media.toFixed(3) + ' nats'],
    ]) + cal.fiabilidad.map((b) =>
      '<div class="lin"><span>' + b.rango + ' · ' + b.n + ' imgs</span>' +
      '<span class="num tenue">acc ' + pct(b.accuracy) + ' · conf ' + pct(b.confianza) + '</span></div>').join('');
  }

  if (d.latencia) {
    const lat = d.latencia;
    $('rendimiento').innerHTML = filaTabla([
      ['Media · p50', lat.ms_por_imagen_media.toFixed(2) + ' · ' + lat.ms_por_imagen_p50.toFixed(2) + ' ms'],
      ['p95 · p99', lat.ms_por_imagen_p95.toFixed(2) + ' · ' + lat.ms_por_imagen_p99.toFixed(2) + ' ms'],
      ['Camino completo (JPEG + modelo)', lat.ms_camino_completo_media.toFixed(2) + ' ms'],
      ['Lote', lat.ms_por_imagen_lote.toFixed(2) + ' ms/img'],
      ['Rendimiento', lat.imagenes_por_segundo.toFixed(0) + ' img/s'],
      ['Muestra cronometrada', lat.muestra + ' imágenes'],
    ]) + '<div class="nota">Media, p50, p95 y p99 miden transformación + CNN + softmax. ' +
      'El camino completo añade abrir y decodificar el archivo.</div>';
  }

  if (d.particion) {
    const par = d.particion;
    $('particion').innerHTML = '<div class="duo">' + Object.entries(par.tamanos).map(([nombre, n]) =>
      '<div><label>' + nombre.toUpperCase() + '</label><strong>' + n + '</strong></div>').join('') +
      '</div><div class="nota">' + par.split.toUpperCase() + ' · ' + par.n + ' imágenes · ' +
      Object.entries(par.por_clase).map(([c, n]) => c.slice(0, 4) + '=' + n).join(' · ') + '</div>';
  }

  if (d.artefactos) {
    $('artefactos').innerHTML = d.artefactos.map((a) =>
      '<div class="lin"><span>' + (a.existe ? '✓ ' : '· ') + a.nombre + '</span><span class="num tenue">' +
      (a.existe ? a.bytes.toLocaleString('es-CO') + ' B · ' + (a.modificado || '—') : 'sin generar') +
      '</span></div>').join('') +
      '<div class="nota">Los genera <code>python -m modelo.evaluar</code>. ' +
      'El reporte no los lee: vuelve a medir sobre las imágenes.</div>';
  }

  pintarProcedencia(d);
  $('sello').className = 'sello ok';
  $('sello').textContent = 'PROCEDENCIA OK';

  $('medido').textContent = 'MEDIDO EN VIVO · ' + meta.medido_en.replace('T', ' ') +
    ' · ' + meta.duracion_ms.toFixed(0) + ' ms';
  $('fuente').textContent = 'FUENTE: ' + meta.fuente + ' · ' + meta.split.toUpperCase() +
    ' · ' + meta.n_imagenes + ' IMÁGENES' + (meta.parcial ? ' · MUESTRA PARCIAL' : '');
  $('version').textContent = 'REPORTE v' + meta.version +
    ' · SIN CACHÉ · CACHE-CONTROL: NO-STORE';
  $('estadoModo').textContent = mod.umbral_calibrado ? 'UMBRAL CALIBRADO' : 'UMBRAL SIN CALIBRAR';
  if (animar) {
    const principal = document.querySelector('main');
    principal.classList.remove('fresco');
    void principal.offsetWidth;
    principal.classList.add('fresco');
  }
}

function esqueletoFilas(n, anchoBase) {
  return Array.from({length: n}, (_, i) =>
    '<div class="lin"><span class="esqueleto esq-lin" style="width:' +
      (anchoBase + (i * 11) % 30) + '%"></span>' +
      '<span class="esqueleto esq-lin" style="width:16%"></span></div>').join('');
}

function esqueletos() {
  ['clases', 'confusiones', 'errores', 'decisiones', 'sistema', 'calibracion',
   'rendimiento', 'particion', 'artefactos', 'procedenciaContenido', 'cnn'].forEach((id) => {
    const contenedor = $(id);
    if (contenedor) contenedor.innerHTML = esqueletoFilas(id === 'sistema' ? 6 : 5, 46);
  });
  $('matriz').innerHTML = '<span class="esqueleto esq-matriz"></span>';
  [['kAcc', 'kAccSub'], ['kF1', 'kF1Sub'], ['kTop3', 'kTop3Sub'],
   ['kCob', 'kCobSub'], ['kSel', 'kSelSub'], ['kLat', 'kLatSub']].forEach(([valor, sub]) => {
    const v = $(valor), s = $(sub);
    if (v) { v.textContent = ''; v.innerHTML = '<span class="esqueleto esq-valor"></span>'; v.style.color = ''; }
    if (s) s.innerHTML = '<span class="esqueleto esq-sub"></span>';
  });
  $('accArc').setAttribute('stroke-dasharray', '0 ' + LARGO_ARCO);
  $('sello').className = 'sello';
  $('sello').textContent = 'VERIFICANDO…';
  $('medido').textContent = 'MIDIENDO…';
  $('fuente').textContent = 'FUENTE: —';
  $('version').textContent = 'REPORTE v— · MIDIENDO… · SIN CACHÉ';
  $('estadoModo').textContent = 'MIDIENDO';
}

function sinDatos() {
  ['clases', 'confusiones', 'errores', 'decisiones', 'sistema', 'calibracion',
   'rendimiento', 'particion', 'artefactos', 'procedenciaContenido', 'cnn', 'matriz'].forEach((id) => {
    if ($(id)) $(id).innerHTML = '<p class="vacio">sin datos</p>';
  });
  [['kAcc', 'kAccSub'], ['kF1', 'kF1Sub'], ['kTop3', 'kTop3Sub'],
   ['kCob', 'kCobSub'], ['kSel', 'kSelSub'], ['kLat', 'kLatSub']].forEach(([valor, sub]) => {
    if ($(valor)) { $(valor).textContent = '--'; $(valor).style.color = 'var(--tenue)'; }
    if ($(sub)) $(sub).textContent = 'sin datos';
  });
  $('medido').textContent = 'SIN DATOS';
  $('fuente').textContent = 'FUENTE: —';
  $('sello').className = 'sello bad';
  $('sello').textContent = 'SIN PROCEDENCIA';
  $('version').textContent = 'REPORTE v— · SIN CACHÉ · CACHE-CONTROL: NO-STORE';
  $('estadoModo').textContent = 'SIN DATOS';
}

const MINIMO_ESQUELETO = 520;
const esperar = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
let primeraCarga = true;

async function cargar(conEsqueleto) {
  const principal = document.querySelector('main');
  const botones = document.querySelectorAll('[data-split]');
  const inicio = performance.now();
  botones.forEach((b) => b.disabled = true);
  if (conEsqueleto) {
    esqueletos();
    $('carga').classList.add('on');
    principal.setAttribute('aria-busy', 'true');
  }
  try {
    const respuesta = await fetch('/reporte?split=' + split, {cache: 'no-store'});
    if (!respuesta.ok) {
      const error = await respuesta.json().catch(() => ({detail: respuesta.statusText}));
      throw new Error(error.detail || 'error ' + respuesta.status);
    }
    const datos = await respuesta.json();
    if (conEsqueleto) {
      const resto = MINIMO_ESQUELETO - (performance.now() - inicio);
      if (resto > 0) await esperar(resto);
    }
    pintar(datos, conEsqueleto || primeraCarga);
    primeraCarga = false;
    $('led').className = 'led ok';
    $('alerta').classList.add('oculto');
  } catch (error) {
    $('led').className = 'led bad';
    $('alerta').classList.remove('oculto');
    $('alerta').textContent = 'SIN DATOS · ' + error.message;
    sinDatos();
  } finally {
    $('carga').classList.remove('on');
    principal.setAttribute('aria-busy', 'false');
    botones.forEach((b) => b.disabled = false);
  }
}

document.querySelectorAll('[data-split]').forEach((boton) => {
  boton.addEventListener('click', () => {
    split = boton.dataset.split;
    document.querySelectorAll('[data-split]').forEach((b) => b.classList.toggle('on', b === boton));
    cargar(true);
  });
});

setInterval(() => { $('hora').textContent = new Date().toISOString().slice(11, 19); }, 1000);
$('hora').textContent = new Date().toISOString().slice(11, 19);

if ('IntersectionObserver' in window) {
  const observador = new IntersectionObserver((entradas) => {
    entradas.forEach((entrada) => {
      if (entrada.isIntersecting) {
        entrada.target.classList.add('visible');
        observador.unobserve(entrada.target);
      }
    });
  }, {threshold: 0.08, rootMargin: '0px 0px -36px 0px'});
  document.querySelectorAll('main > section, .kpi').forEach((elemento, indice) => {
    elemento.classList.add('revelar');
    elemento.style.transitionDelay = ((indice % 6) * 55) + 'ms';
    observador.observe(elemento);
  });
}

cargar(true);
setInterval(() => cargar(false), 20000);
</script>
</body>
</html>
"""
