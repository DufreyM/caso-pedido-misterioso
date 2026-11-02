"""
El caso del pedido misterioso
Juego de misterio con datos para la demostración de Streamlit.
Grupo 6 · CC3084 Data Science · UVG · 2026

Ejecutar:               streamlit run app.py
Vista del presentador:  http://localhost:8501/?modo=presentador
"""

import html
import threading
import time

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# ───────────────────────────── Configuración del juego ─────────────────────────────
# Lo que ve el equipo al resolver el caso. Cámbienlo por su sorpresa real.
SORPRESA = (
    "Acérquense al **Grupo 6** y digan la contraseña **«cacao quetzal»** "
    "para reclamar su premio."
)
# Los datos se generan a partir de esta solución: si la cambian, el pedido se mueve solo.
SOLUCION = {"tienda": "Mazatenango", "mes": "Agosto", "producto": "Bombones"}
PIN_PRESENTADOR = "2366"
PUNTOS_INICIALES = 100
COSTO_PISTA = 15
COSTO_ERROR = 10

# ───────────────────────────── Datos del negocio ─────────────────────────────
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre"]
REGIONES = {
    "Norte": ["Cobán", "Flores", "Salamá"],
    "Centro": ["Zona 10", "Mixco", "Antigua"],
    "Sur": ["Escuintla", "Mazatenango", "Retalhuleu"],
}
TIENDAS = [t for tiendas in REGIONES.values() for t in tiendas]
REGION_DE = {t: r for r, tiendas in REGIONES.items() for t in tiendas}
PRODUCTOS = ["Tabletas", "Bombones", "Trufas", "Bebidas de cacao"]

VENTA_BASE = {  # Q por día en un día normal
    "Zona 10": 14000, "Mixco": 11000, "Antigua": 12000,
    "Cobán": 7000, "Flores": 6000, "Salamá": 5200,
    "Escuintla": 4300, "Mazatenango": 3900, "Retalhuleu": 3700,
}
PARTICIPACION = {"Tabletas": 0.30, "Bombones": 0.28, "Trufas": 0.20, "Bebidas de cacao": 0.22}
TICKET_PROMEDIO = {"Tabletas": 35, "Bombones": 60, "Trufas": 75, "Bebidas de cacao": 25}
# Temporadas (pistas falsas): afectan a TODAS las tiendas a la vez
ESTACIONALIDAD = {
    "Tabletas": {3: 1.12, 4: 1.15},                         # Semana Santa
    "Bombones": {2: 1.70, 5: 1.30},                         # Día del Cariño y de la Madre
    "Trufas": {2: 1.40, 5: 1.15},
    "Bebidas de cacao": {},
}

# ───────────────────────────── Paleta "Grupo 6" ─────────────────────────────
# Misma paleta que .streamlit/config.toml. Las gráficas usan los 4 primeros en este orden fijo
# (validado para daltonismo): el color sigue a la entidad, nunca a su ranking.
TINTA = "#0E1B4D"
AZUL = "#1F4FD8"
CIELO = "#3B82F6"
HIELO = "#EAF0FF"
TURQUESA = "#0E9384"
TURQUESA_CLARO = "#2DD4BF"
CORAL = "#E04A4F"
AMBAR = "#D08300"
GRIS = "#9AA3BD"
PALETA = [AZUL, CORAL, TURQUESA, AMBAR]

# Las tres preguntas del caso: cada tarjeta une su pista de la nota con el filtro que sirve para buscarla
MISION = [
    {"clave": "tienda", "pregunta": "¿Dónde?", "dato": "La tienda",
     "nota": "«No fue en una tienda grande»",
     "como": "Cambien la **Región** en los filtros y miren la pestaña **Tiempo**: "
             "una tienda tiene un pico que sus vecinas no."},
    {"clave": "mes", "pregunta": "¿Cuándo?", "dato": "El mes",
     "nota": "«Ni en una fecha de temporada. Duró un mes entero»",
     "como": "En esa misma gráfica, el mes del pico es la respuesta. "
             "Ojo: febrero sube en todas las tiendas (temporada)."},
    {"clave": "producto", "pregunta": "¿Qué?", "dato": "El producto",
     "nota": "«Siempre pedí lo mismo»",
     "como": "Elijan esa **Tienda**, dejen solo ese mes en **Meses** y abran **Productos**: "
             "uno sube muchísimo."},
]
OPCIONES_MISION = {"tienda": TIENDAS, "mes": MESES, "producto": PRODUCTOS}

PISTAS = [
    "Elijan la región **Sur** y abran **Tiempo**: una de las tres líneas se separa de las demás.",
    "El pedido fue en la **segunda mitad del año** (julio a octubre).",
    "El producto del pedido es de los que también suben el **Día del Cariño** (febrero).",
]

NOTA = """*«Este año hice un pedido muy dulce en una de sus tiendas.
No fue en una tienda grande, ni en una fecha de temporada.
Duró un mes entero y siempre pedí lo mismo.
Cada día pagué con un solo ticket, pero nunca fue poco.
Si descubren **dónde**, **cuándo** y **qué** pedí, les dejé una sorpresa.»*

— Anónimo"""

# Fragmentos que se muestran con el interruptor «Ver el código detrás»
COD_FILTROS = '''region = st.selectbox("Región", ["Todas", "Norte", "Centro", "Sur"])
meses = st.select_slider("Meses", options=MESES, value=("Enero", "Octubre"))
productos = st.multiselect("Productos", PRODUCTOS, default=PRODUCTOS)

# Cada cambio vuelve a ejecutar el script y df_f se recalcula
df_f = df[(df["region"] == region) & df["producto"].isin(productos)]'''

COD_KPI = '''col1, col2 = st.columns(2)
col1.metric("Ventas", f"Q {ventas:,.0f}", delta="+56% vs. mes típico")
col2.metric("Ticket promedio", f"Q {ticket:,.2f}")'''

COD_TIENDAS = '''# Versión de una línea:
st.bar_chart(df_f.groupby("tienda")["ventas"].sum(), horizontal=True)

# Versión con más control (la que ven aquí):
grafica = alt.Chart(por_tienda).mark_bar().encode(x="ventas", y=alt.Y("tienda", sort="-x"))
st.altair_chart(grafica)'''

COD_TIEMPO = '''mensual = df_f.groupby(["mes", "tienda"])["ventas"].sum().reset_index()
st.line_chart(mensual, x="mes", y="ventas", color="tienda")'''

COD_DATOS = '''@st.cache_data            # se genera una sola vez, no en cada ejecución
def cargar_datos(): ...

st.dataframe(df_f, hide_index=True)
st.download_button("Descargar CSV", df_f.to_csv(index=False), "ventas.csv")'''

COD_ESTADO = '''if "intentos" not in st.session_state:
    st.session_state.intentos = []       # sobrevive a las re-ejecuciones

def acusar():                           # callback: corre antes de la re-ejecución
    st.session_state.intentos.append(st.session_state.sos_tienda)

st.selectbox("Su sospecha", TIENDAS, index=None, key="sos_tienda")
listas = st.session_state.sos_tienda is not None
st.button("Acusar", disabled=not listas, on_click=acusar)'''

ESTADO_INICIAL = {
    "etapa": "intro", "equipo": "", "inicio": None, "fin": None,
    "pistas": 0, "errores_previos": 0, "intentos": [], "feedback": None,
    "reejecuciones": 0, "festejado": False, "ver_codigo": False, "confirmar_reinicio": False,
    # El slider de meses usa una clave versionada: subir la versión lo regresa a su valor inicial
    "rango": (MESES[0], MESES[-1]), "v_meses": 0,
}
FILTROS_INICIALES = {"f_region": "Todas", "f_tienda": "Todas", "f_productos": PRODUCTOS}

# ───────────────────────────── Estilos ─────────────────────────────
# Los contenedores con key="..." reciben la clase .st-key-...; así se pintan sin tocar el HTML interno.
ESTILOS = f"""
<style>
:root {{
  --tinta: {TINTA}; --azul: {AZUL}; --cielo: {CIELO}; --hielo: {HIELO};
  --turquesa: {TURQUESA}; --turquesa-claro: {TURQUESA_CLARO}; --coral: {CORAL}; --ambar: {AMBAR};
  --borde: #D6DEF3; --texto-2: #4A5578; --sombra: 0 1px 2px rgba(14,27,77,.06), 0 10px 28px rgba(14,27,77,.07);
}}

/* Portada con degradado, como la diapositiva de título */
.hero {{
  position: relative; overflow: hidden; border-radius: 1.25rem; padding: 1.75rem 2rem;
  margin-bottom: .75rem; color: #fff; box-shadow: var(--sombra);
  background: linear-gradient(120deg, var(--tinta) 0%, var(--azul) 65%, var(--cielo) 100%);
}}
.hero.resuelto {{ background: linear-gradient(120deg, var(--tinta) 0%, var(--turquesa) 60%, var(--turquesa-claro) 100%); }}
.hero .eyebrow {{ text-transform: uppercase; letter-spacing: .14em; font-size: .78rem; font-weight: 800; color: var(--turquesa-claro); }}
.hero.resuelto .eyebrow {{ color: #FFE08A; }}
.hero .titulo {{ font-size: clamp(1.8rem, 4vw, 2.7rem); font-weight: 800; line-height: 1.08; margin: .25rem 0 0; color: #fff; }}
.hero p {{ color: #DCE6FF; margin: .6rem 0 0; max-width: 46rem; font-size: 1.05rem; }}
.hero .flecha {{ position: absolute; right: 1.5rem; top: 1.25rem; width: 84px; height: 84px; opacity: .9; }}
.chips {{ display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }}
.chip {{ background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); color: #fff;
        border-radius: 999px; padding: .25rem .8rem; font-size: .85rem; font-weight: 600; }}
.chip b {{ color: var(--turquesa-claro); }}

/* Encabezados numerados de sección (círculo turquesa + título azul) */
.sec {{ display: flex; align-items: center; gap: .9rem; margin: 1.5rem 0 .75rem; scroll-margin-top: 4rem; }}
.sec .num {{ flex: none; width: 2.6rem; height: 2.6rem; font-size: 1.25rem; }}
.sec-titulo {{ font-size: 1.6rem; font-weight: 800; color: var(--azul); line-height: 1.1; }}
.sec-texto {{ color: var(--texto-2); font-size: .95rem; margin-top: .15rem; }}
.num {{ display: inline-flex; align-items: center; justify-content: center; border-radius: 50%;
       background: var(--turquesa-claro); color: var(--tinta); font-weight: 800; }}

/* Tarjetas blancas genéricas */
[class*="st-key-panel"], [data-testid="stForm"] {{
  background: #fff; border: 1px solid var(--borde); border-radius: 1rem; padding: 1.1rem 1.25rem; box-shadow: var(--sombra);
}}
.etiqueta {{ text-transform: uppercase; letter-spacing: .12em; font-size: .75rem; font-weight: 800; color: var(--azul); }}

/* Tarjetas de las 3 preguntas: cada una con su color */
[class*="st-key-card_"] {{
  background: #fff; border: 1px solid var(--borde); border-top: 6px solid var(--c);
  border-radius: 1rem; padding: 1.1rem 1.15rem 1rem; box-shadow: var(--sombra);
}}
[class*="st-key-card_tienda"] {{ --c: var(--azul); }}
[class*="st-key-card_mes"] {{ --c: var(--turquesa); }}
[class*="st-key-card_producto"] {{ --c: var(--coral); }}
.card-head {{ display: flex; align-items: center; gap: .75rem; }}
.card-head .num {{ width: 2.3rem; height: 2.3rem; background: var(--c); color: #fff; font-size: 1.1rem; }}
.pregunta {{ font-size: 1.3rem; font-weight: 800; color: var(--tinta); line-height: 1.1; }}
.dato {{ font-size: .8rem; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; color: var(--c); }}
.cita {{ border-left: 3px solid var(--c); padding: .15rem 0 .15rem .75rem; margin: .85rem 0 .35rem;
        font-style: italic; color: var(--tinta); }}

/* La nota anónima: papel con borde turquesa */
[class*="st-key-nota"] {{
  background: #FFFDF7; border: 1px solid #EFE6CF; border-left: 6px solid var(--turquesa-claro);
  border-radius: 1rem; padding: 1.1rem 1.4rem; box-shadow: var(--sombra);
}}

/* La sorpresa */
[class*="st-key-sorpresa"] {{
  background: linear-gradient(120deg, #FFF2D9 0%, #FDE6E6 100%); border: 2px dashed var(--ambar);
  border-radius: 1.25rem; padding: 1.4rem 1.6rem;
}}
[class*="st-key-sorpresa"] p {{ font-size: 1.2rem; color: var(--tinta); }}

/* Indicadores: tarjeta blanca con acento de color distinto por posición */
[data-testid="stMain"] [data-testid="stMetric"] {{ background: #fff; box-shadow: var(--sombra); border-top: 4px solid var(--azul); }}
[data-testid="stMain"] [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] {{ border-top-color: var(--turquesa); }}
[data-testid="stMain"] [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {{ border-top-color: var(--coral); }}
[data-testid="stMain"] [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {{ border-top-color: var(--ambar); }}
[data-testid="stMetricValue"] {{ font-weight: 800; }}

/* Pestañas y su contenido sobre blanco */
[data-baseweb="tab"] p {{ font-weight: 700; font-size: 1rem; }}
[data-baseweb="tab-panel"] {{ background: #fff; border: 1px solid var(--borde); border-radius: 0 1rem 1rem 1rem;
                             padding: 1.25rem; box-shadow: var(--sombra); }}
[data-testid="stMain"] [data-testid="stExpander"] details {{ background: #fff; }}

/* Tablero en la barra lateral */
.fila {{ display: flex; align-items: center; gap: .6rem; margin: .35rem 0; }}
.fila .dim {{ margin-left: auto; opacity: .75; font-size: .85rem; white-space: nowrap; }}
.pos {{ flex: none; width: 1.6rem; height: 1.6rem; border-radius: 50%; display: inline-flex; align-items: center;
       justify-content: center; font-weight: 800; font-size: .85rem; background: #31447F; color: #fff; }}
.pos.p1 {{ background: #F5B83D; color: var(--tinta); }}
.pos.p2 {{ background: #C9D3EE; color: var(--tinta); }}
.pos.p3 {{ background: #D9915F; color: var(--tinta); }}
</style>
"""

# Flecha diagonal de las diapositivas
FLECHA = ('<svg class="flecha" viewBox="0 0 100 100" aria-hidden="true">'
          f'<path d="M18 82 L80 20 M38 20 H80 V62" stroke="{TURQUESA_CLARO}" stroke-width="6" '
          'fill="none" stroke-linecap="square"/></svg>')


# ───────────────────────────── Datos ─────────────────────────────
@st.cache_data
def cargar_datos(semilla: int = 6) -> pd.DataFrame:
    """Ventas diarias simuladas de enero a octubre de 2026, con el pedido escondido."""
    rng = np.random.default_rng(semilla)
    fechas = pd.date_range("2026-01-01", "2026-10-31", freq="D")
    df = pd.MultiIndex.from_product(
        [fechas, TIENDAS, PRODUCTOS], names=["fecha", "tienda", "producto"]
    ).to_frame(index=False)
    df["region"] = df["tienda"].map(REGION_DE)
    df["mes_num"] = df["fecha"].dt.month
    df["mes"] = df["mes_num"].map(lambda m: MESES[m - 1])

    base = (df["tienda"].map(VENTA_BASE) * df["producto"].map(PARTICIPACION)).to_numpy()
    fin_de_semana = np.where(df["fecha"].dt.day_of_week >= 5, 1.25, 1.0)
    temporada = np.array([ESTACIONALIDAD[p].get(m, 1.0) for p, m in zip(df["producto"], df["mes_num"])])
    tendencia = 1 + 0.01 * (df["mes_num"].to_numpy() - 1)
    ventas = base * fin_de_semana * temporada * tendencia * rng.lognormal(0, 0.12, len(df))
    ticket = df["producto"].map(TICKET_PROMEDIO).to_numpy() * rng.lognormal(0, 0.08, len(df))
    tickets = np.maximum(1, np.round(ventas / ticket))

    # Pista falsa: Cobán cerró dos semanas por remodelación
    cerrada = ((df["tienda"] == "Cobán") & df["fecha"].between("2026-05-04", "2026-05-17")).to_numpy()
    ventas[cerrada] = 0
    tickets[cerrada] = 0

    # El pedido misterioso: un ticket grande cada día del mes
    pedido = (
        (df["tienda"] == SOLUCION["tienda"])
        & (df["mes"] == SOLUCION["mes"])
        & (df["producto"] == SOLUCION["producto"])
    ).to_numpy()
    ventas[pedido] += rng.normal(4500, 350, pedido.sum())
    tickets[pedido] += 1

    df["ventas"] = ventas.round(2)
    df["tickets"] = tickets.astype(int)
    return df


def filtrar(df: pd.DataFrame, tiendas: list[str] | None = None, con_meses: bool = True) -> pd.DataFrame:
    """Aplica los filtros del panel. `tiendas` reemplaza los filtros de región y tienda."""
    s = st.session_state
    m = df["producto"].isin(s.f_productos)
    if tiendas is not None:
        m &= df["tienda"].isin(tiendas)
    else:
        if s.f_region != "Todas":
            m &= df["region"] == s.f_region
        if s.f_tienda != "Todas":
            m &= df["tienda"] == s.f_tienda
    if con_meses:
        m &= df["mes_num"].between(*rango_meses())
    return df[m]


def rango_meses() -> tuple[int, int]:
    a, b = st.session_state.rango
    return MESES.index(a) + 1, MESES.index(b) + 1


# ───────────────────────────── Estado y tablero compartido ─────────────────────────────
def iniciar_estado():
    for k, v in {**ESTADO_INICIAL, **FILTROS_INICIALES}.items():
        if k not in st.session_state:
            st.session_state[k] = v.copy() if isinstance(v, list) else v


@st.cache_resource
def tablero_compartido() -> dict:
    """Un solo objeto para todas las sesiones del servidor: así los equipos se ven entre sí."""
    return {"candado": threading.Lock(), "equipos": {}}


def registrar(equipo: str, **datos):
    t = tablero_compartido()
    with t["candado"]:
        t["equipos"].setdefault(equipo, {}).update(datos)


def errores() -> int:
    s = st.session_state
    return s.errores_previos + sum(1 for i in s.intentos if i["aciertos"] < 3)


def puntos() -> int:
    return max(0, PUNTOS_INICIALES - COSTO_PISTA * st.session_state.pistas - COSTO_ERROR * errores())


def fmt_tiempo(segundos: float) -> str:
    m, s = divmod(int(segundos), 60)
    return f"{m:02d}:{s:02d}"


def ranking() -> tuple[list[tuple[str, dict]], int]:
    t = tablero_compartido()
    with t["candado"]:
        equipos = {k: dict(v) for k, v in t["equipos"].items()}
    resueltos = sorted(
        ((k, v) for k, v in equipos.items() if v.get("estado") == "resuelto"),
        key=lambda kv: (-kv[1]["puntos"], kv[1]["tiempo"]),
    )
    investigando = sum(1 for v in equipos.values() if v.get("estado") == "investigando")
    return resueltos, investigando


# ───────────────────────────── Callbacks ─────────────────────────────
def _al_cambiar_region():
    st.session_state.f_tienda = "Todas"


def _limpiar_filtros():
    for k, v in FILTROS_INICIALES.items():
        st.session_state[k] = v.copy() if isinstance(v, list) else v
    st.session_state.v_meses += 1
    st.session_state.rango = (MESES[0], MESES[-1])


def _usar_pista():
    s = st.session_state
    s.pistas += 1
    registrar(s.equipo, pistas=s.pistas, puntos=puntos())


def _limpiar_feedback():
    st.session_state.feedback = None


def _acusar():
    s = st.session_state
    tienda, mes, producto = s.sos_tienda, s.sos_mes, s.sos_producto
    if any((i["tienda"], i["mes"], i["producto"]) == (tienda, mes, producto) for i in s.intentos):
        s.feedback = ("info", "Ya probaron esa combinación (está en «Acusaciones anteriores»). "
                              "No se descontaron puntos.")
        return

    elegido = {"tienda": tienda, "mes": mes, "producto": producto}
    ok = {k: v == SOLUCION[k] for k, v in elegido.items()}
    aciertos = sum(ok.values())
    s.intentos.append({**elegido, "ok": ok, "aciertos": aciertos})
    registrar(s.equipo, errores=errores(), puntos=puntos())
    if aciertos == 3:
        s.etapa, s.fin = "resuelto", time.time()
        registrar(s.equipo, estado="resuelto", tiempo=s.fin - s.inicio, intentos=len(s.intentos))
        return

    # Cada tarjeta marca si su dato es correcto: así avanzan de uno en uno
    texto = f"**{aciertos} de 3 correctas.** Cada tarjeta les marca cuál está bien; cambien las que no."
    if errores() >= 3 and s.pistas < len(PISTAS):
        texto += " Una pista puede ahorrarles puntos."
    s.feedback = ("warning" if aciertos else "error", texto)


def _reiniciar():
    for k in list(st.session_state.keys()):
        del st.session_state[k]


# ───────────────────────────── Componentes reutilizables ─────────────────────────────
def hero(eyebrow: str, titulo: str, texto: str = "", chips: tuple[str, ...] = (), variante: str = ""):
    """Portada con degradado. `chips` ya viene escapado (puede llevar <b>)."""
    partes = [f'<div class="hero {variante}">', FLECHA, f'<div class="eyebrow">{eyebrow}</div>',
              f'<div class="titulo">{titulo}</div>']
    if texto:
        partes.append(f"<p>{texto}</p>")
    if chips:
        partes.append('<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>")
    partes.append("</div>")
    st.markdown("".join(partes), unsafe_allow_html=True)


def encabezado(numero: int, titulo: str, texto: str, ancla: str | None = None):
    id_ = f' id="{ancla}"' if ancla else ""
    st.markdown(
        f'<div class="sec"{id_}><span class="num">{numero}</span><div>'
        f'<div class="sec-titulo">{titulo}</div><div class="sec-texto">{texto}</div></div></div>',
        unsafe_allow_html=True,
    )


def cabeza_tarjeta(numero: int, m: dict):
    st.markdown(
        f'<div class="card-head"><span class="num">{numero}</span><div>'
        f'<div class="pregunta">{m["pregunta"]}</div><div class="dato">{m["dato"]}</div></div></div>',
        unsafe_allow_html=True,
    )


def codigo(fragmento: str):
    if st.session_state.ver_codigo:
        with st.expander("El código detrás de esto", icon=":material/code:"):
            st.code(fragmento, language="python")


def grafica(chart: alt.Chart):
    st.altair_chart(chart, width="stretch")


def escala(dominio: list[str], colores: list[str]) -> alt.Scale:
    return alt.Scale(domain=dominio, range=colores[: len(dominio)])


@st.fragment(run_every=1)
def reloj():
    st.metric("Tiempo", fmt_tiempo(time.time() - st.session_state.inicio))


@st.fragment(run_every=5)
def tablero_compacto():
    resueltos, investigando = ranking()
    st.caption(f"{investigando} equipo(s) investigando · {len(resueltos)} resuelto(s)")
    if not resueltos:
        st.caption("Nadie ha resuelto el caso todavía.")
        return
    filas = "".join(
        f'<div class="fila"><span class="pos p{i + 1}">{i + 1}</span><b>{html.escape(e)}</b>'
        f'<span class="dim">{d["puntos"]} pts · {fmt_tiempo(d["tiempo"])}</span></div>'
        for i, (e, d) in enumerate(resueltos[:5])
    )
    st.markdown(filas, unsafe_allow_html=True)


def barra_lateral():
    s = st.session_state
    with st.sidebar:
        st.markdown('<div class="etiqueta" style="color:#2DD4BF">Equipo</div>', unsafe_allow_html=True)
        st.markdown(f"### {html.escape(s.equipo)}")
        if s.etapa == "investigando":
            reloj()
        else:
            st.metric("Tiempo", fmt_tiempo(s.fin - s.inicio))
        c1, c2 = st.columns(2)
        c1.metric("Puntos", puntos())
        c2.metric("Acusaciones", len(s.intentos))

        st.divider()
        st.metric(
            "Ejecuciones del script", s.reejecuciones,
            help="Cada vez que tocan un widget, Streamlit vuelve a correr app.py de arriba a abajo. "
                 "st.session_state es lo que conserva sus puntos entre ejecuciones.",
        )
        st.toggle("Ver el código detrás", key="ver_codigo",
                  help="Muestra el código de Streamlit que genera cada parte del dashboard.")

        st.divider()
        st.markdown("**Tablero**")
        tablero_compacto()

        st.divider()
        if not s.confirmar_reinicio:
            st.button("Reiniciar juego", icon=":material/restart_alt:",
                      on_click=lambda: s.update(confirmar_reinicio=True))
        else:
            st.warning("¿Seguros? Se pierde el progreso de esta sesión.")
            a, b = st.columns(2)
            a.button("Sí, reiniciar", type="primary", on_click=_reiniciar)
            b.button("Cancelar", on_click=lambda: s.update(confirmar_reinicio=False))


# ───────────────────────────── Pantalla 1: introducción ─────────────────────────────
def pantalla_intro(df: pd.DataFrame):
    hero("Grupo 6 · Demostración de Streamlit", "El caso del pedido misterioso",
         "Alguien escondió un pedido en los datos de ventas. Descubran estos <b>3 datos</b> "
         "para desbloquear la sorpresa.")

    for i, (col, m) in enumerate(zip(st.columns(3), MISION), 1):
        with col.container(key=f"card_{m['clave']}_intro"):
            cabeza_tarjeta(i, m)
            st.markdown(f'<div class="cita">{m["nota"]}</div>', unsafe_allow_html=True)

    izq, der = st.columns([3, 2], gap="large")
    with izq:
        encabezado(1, "La historia", "Cacao Quetzal: 9 chocolaterías en 3 regiones de Guatemala.")
        st.markdown("Esta mañana, la gerencia encontró esta nota en su escritorio. **Cada línea es una pista:**")
        with st.container(key="nota"):
            st.markdown(NOTA)
        st.markdown("Ustedes son el equipo de análisis y tienen las ventas diarias de **enero a octubre de 2026**.")
    with der:
        encabezado(2, "Cómo se juega", "Unos 5 minutos.")
        with st.container(key="panel_reglas"):
            st.markdown(
                "1. **Sigan las instrucciones** de cada tarjeta.\n"
                "2. **Anoten su sospecha** y presionen **Acusar**.\n"
                "3. Cada tarjeta les dice si **acertaron**. Corrijan hasta tener las 3."
            )
            st.caption(
                f"Empiezan con {PUNTOS_INICIALES} puntos. Pista: −{COSTO_PISTA}. Acusación fallida: −{COSTO_ERROR}. "
                "Gana quien tenga más puntos; si empatan, el más rápido."
            )
        with st.form("form_inicio", border=False):
            nombre = st.text_input("Nombre del equipo", max_chars=24,
                                   placeholder="Ej. Los Pandas Detectives")
            if st.form_submit_button("Abrir el expediente", type="primary", width="stretch",
                                     icon=":material/arrow_forward:", icon_position="right"):
                empezar(nombre.strip())


def empezar(nombre: str):
    if not nombre:
        st.error("Escriban un nombre de equipo para empezar.")
        return
    t = tablero_compartido()
    with t["candado"]:
        previo = dict(t["equipos"].get(nombre, {}))
    if previo.get("estado") == "resuelto":
        st.error(f"«{nombre}» ya resolvió el caso. Elijan otro nombre para jugar de nuevo.")
        return

    s = st.session_state
    s.equipo = nombre
    if previo:  # recargaron la página: retoman con su tiempo y penalizaciones
        s.inicio = previo["inicio"]
        s.pistas = previo.get("pistas", 0)
        s.errores_previos = previo.get("errores", 0)
        st.toast(f"Retomando la investigación de «{nombre}»", icon=":material/history:")
    else:
        s.inicio = time.time()
        registrar(nombre, inicio=s.inicio, estado="investigando",
                  pistas=0, errores=0, puntos=PUNTOS_INICIALES)
    s.etapa = "investigando"
    st.rerun()


# ───────────────────────────── Pantalla 2: investigación ─────────────────────────────
def pantalla_investigacion(df: pd.DataFrame):
    barra_lateral()
    s = st.session_state
    # Estado visible también en celular, donde la barra lateral está oculta
    hero("Expediente abierto", "El caso del pedido misterioso", chips=(
        f"Equipo <b>{html.escape(s.equipo)}</b>",
        f"<b>{puntos()}</b> puntos",
        f"<b>{len(s.intentos)}</b> acusaciones",
        f"<b>{s.pistas}/{len(PISTAS)}</b> pistas",
    ))
    seccion_mision()

    encabezado(2, "La evidencia: ventas de Cacao Quetzal",
               "Ventas diarias de enero a octubre de 2026. Cambien los filtros y todo se actualiza al instante.")
    panel_filtros()
    df_f = filtrar(df)
    if df_f.empty:
        st.warning("No hay datos con estos filtros. Elijan al menos un producto o usen **Limpiar filtros**.")
    else:
        indicadores(df, df_f)
        t2, t3, t1, t4 = st.tabs([":material/show_chart: Tiempo", ":material/category: Productos",
                                  ":material/storefront: Tiendas", ":material/table_view: Datos"])
        with t2:
            vista_tiempo(df, df_f)
        with t1:
            vista_tiendas(df_f)
        with t3:
            vista_productos(df, df_f)
        with t4:
            vista_datos(df_f)

    st.markdown("[¿Ya tienen sus sospechas? Vuelvan a **Su misión** para acusar ↑](#mision)")


def seccion_mision():
    s = st.session_state
    encabezado(1, "Su misión: descubrir 3 datos",
               "Lean la pista de cada tarjeta, investiguen con el dashboard de abajo y anoten su sospecha.",
               ancla="mision")
    ultimo = s.intentos[-1] if s.intentos else None
    for i, (col, m) in enumerate(zip(st.columns(3), MISION), 1):
        with col.container(key=f"card_{m['clave']}"):
            cabeza_tarjeta(i, m)
            st.markdown(f'<div class="cita">{m["nota"]}</div>', unsafe_allow_html=True)
            st.caption(m["como"])
            valor = st.selectbox(
                "Su sospecha", OPCIONES_MISION[m["clave"]], index=None, key=f"sos_{m['clave']}",
                placeholder="Aún no sabemos…", on_change=_limpiar_feedback,
                format_func=(lambda t: f"{t} ({REGION_DE[t]})") if m["clave"] == "tienda" else str,
            )
            # Resultado de la última acusación, mientras no cambien ese dato
            if ultimo and valor == ultimo[m["clave"]]:
                if ultimo["ok"][m["clave"]]:
                    st.badge("Correcto", icon=":material/check:", color="green")
                else:
                    st.badge("No es este", icon=":material/close:", color="red")

    listas = sum(s.get(f"sos_{m['clave']}") is not None for m in MISION)
    boton, estado = st.columns([1, 3], vertical_alignment="center")
    boton.button("Acusar", type="primary", icon=":material/gavel:", disabled=listas < 3,
                 on_click=_acusar, width="stretch")
    if listas < 3:
        estado.caption(f"**{listas} de 3** sospechas anotadas. El botón se activa cuando tengan las tres.")
    else:
        estado.caption(f"¡Listas! Cada tarjeta les dirá si acertaron. "
                       f"Cada acusación fallida resta {COSTO_ERROR} puntos.")
    if s.feedback:
        tipo, texto = s.feedback
        getattr(st, tipo)(texto)

    historial, pistas = st.columns(2)
    with historial:
        with st.expander(f"Acusaciones anteriores ({len(s.intentos)})", icon=":material/history:"):
            if not s.intentos:
                st.caption("Todavía no han acusado.")
            else:
                st.dataframe(
                    pd.DataFrame([{"#": n, "Tienda": i["tienda"], "Mes": i["mes"], "Producto": i["producto"],
                                   "Aciertos": f"{i['aciertos']} de 3"} for n, i in enumerate(s.intentos, 1)]),
                    hide_index=True, width="stretch",
                )
    with pistas:
        with st.expander("¿Atorados? Pidan una pista", icon=":material/lightbulb:"):
            for i in range(s.pistas):
                st.info(PISTAS[i])
            if s.pistas < len(PISTAS):
                st.button(f"Ver pista {s.pistas + 1} de {len(PISTAS)} (−{COSTO_PISTA} pts)", on_click=_usar_pista)
            else:
                st.caption("Ya vieron todas las pistas.")
    codigo(COD_ESTADO)


def panel_filtros():
    s = st.session_state
    with st.container(key="panel_filtros"):
        st.markdown('<div class="etiqueta">Filtros</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns([1, 1, 2, 2])
        c1.selectbox("Región", ["Todas", *REGIONES], key="f_region", on_change=_al_cambiar_region)
        opciones = ["Todas", *(TIENDAS if s.f_region == "Todas" else REGIONES[s.f_region])]
        if s.f_tienda not in opciones:
            s.f_tienda = "Todas"
        c2.selectbox("Tienda", opciones, key="f_tienda")
        s.rango = c3.select_slider("Meses", options=MESES, value=(MESES[0], MESES[-1]),
                                   key=f"f_meses_{s.v_meses}")
        c4.multiselect("Productos", PRODUCTOS, key="f_productos", placeholder="Elijan al menos uno")

        a, b = rango_meses()
        meses = MESES[a - 1] if a == b else f"{MESES[a - 1][:3]}–{MESES[b - 1][:3]}"
        donde = s.f_tienda if s.f_tienda != "Todas" else (
            "todas las tiendas" if s.f_region == "Todas" else f"región {s.f_region}")
        info, boton = st.columns([4, 1], vertical_alignment="center")
        info.caption(f"Viendo: **{donde}** · **{meses}** · **{len(s.f_productos)} de {len(PRODUCTOS)}** productos")
        boton.button("Limpiar filtros", icon=":material/restart_alt:", on_click=_limpiar_filtros, width="stretch")
    codigo(COD_FILTROS)


def indicadores(df: pd.DataFrame, df_f: pd.DataFrame):
    a, b = rango_meses()
    n_meses = b - a + 1
    anual = filtrar(df, con_meses=False)
    todo_el_anio = n_meses == len(MESES)

    ventas, tickets = df_f["ventas"].sum(), df_f["tickets"].sum()
    ventas_anual, tickets_anual = anual["ventas"].sum(), anual["tickets"].sum()
    ticket = ventas / tickets if tickets else 0
    ticket_anual = ventas_anual / tickets_anual if tickets_anual else 0

    def delta(actual: float, tipico: float, texto: str) -> str | None:
        if todo_el_anio or not tipico:
            return None
        return f"{actual / tipico - 1:+.0%} vs. {texto}"

    ayuda = ("«Mes típico» = promedio mensual de enero a octubre con los mismos filtros de "
             "región, tienda y producto. Elijan menos meses para ver la comparación.")
    c = st.columns(4)
    c[0].metric("Ventas", f"Q {ventas:,.0f}",
                delta(ventas / n_meses, ventas_anual / len(MESES), "mes típico"), help=ayuda, border=True)
    c[1].metric("Tickets", f"{tickets:,.0f}",
                delta(tickets / n_meses, tickets_anual / len(MESES), "mes típico"), help=ayuda, border=True)
    c[2].metric("Ticket promedio", f"Q {ticket:,.2f}", delta(ticket, ticket_anual, "el año"),
                help="Ventas ÷ tickets. Comparado contra el ticket promedio de todo el año.", border=True)
    lider = df_f.groupby("tienda")["ventas"].sum().idxmax()
    c[3].metric("Tienda líder", lider, help="La tienda con más ventas en la vista actual.", border=True)
    codigo(COD_KPI)


def vista_tiendas(df_f: pd.DataFrame):
    s = st.session_state
    por_tienda = df_f.groupby(["tienda", "region"], as_index=False)["ventas"].sum()
    regiones = [r for r in REGIONES if r in set(por_tienda["region"])]
    color = alt.Color("region:N", title="Región", scale=escala(list(REGIONES), PALETA),
                      legend=alt.Legend(orient="top", values=regiones))
    if s.f_tienda != "Todas":  # resaltar la tienda elegida
        color = alt.condition(alt.datum.tienda == s.f_tienda, alt.value(AZUL), alt.value(GRIS))
    chart = alt.Chart(por_tienda).mark_bar(cornerRadiusEnd=4).encode(
        x=alt.X("ventas:Q", title="Ventas (Q)", axis=alt.Axis(format="~s")),
        y=alt.Y("tienda:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)),
        color=color,
        tooltip=[alt.Tooltip("tienda:N", title="Tienda"), alt.Tooltip("region:N", title="Región"),
                 alt.Tooltip("ventas:Q", title="Ventas (Q)", format=",.0f")],
    ).properties(height=max(160, 36 * len(por_tienda)))
    st.markdown("**Ventas acumuladas por tienda en el período elegido**")
    st.caption("Las tiendas de la capital son más grandes y casi siempre ganan en el total: "
               "comparen cada tienda con las de **su misma región**.")
    grafica(chart)
    codigo(COD_TIENDAS)


def vista_tiempo(df: pd.DataFrame, df_f: pd.DataFrame):
    s = st.session_state
    trazo = None
    if s.f_tienda != "Todas":
        region = REGION_DE[s.f_tienda]
        vecinas = [t for t in REGIONES[region] if t != s.f_tienda]
        propia = df_f.groupby(["mes_num", "mes"], as_index=False)["ventas"].sum().assign(serie=s.f_tienda)
        otras = filtrar(df, tiendas=vecinas).groupby(["mes_num", "mes"], as_index=False)["ventas"].sum()
        otras = otras.assign(ventas=otras["ventas"] / len(vecinas), serie="Promedio de sus vecinas")
        mensual = pd.concat([propia, otras])
        dominio, colores = [s.f_tienda, "Promedio de sus vecinas"], [AZUL, GRIS]
        trazo = alt.StrokeDash("serie:N", scale=alt.Scale(domain=dominio, range=[[1, 0], [5, 4]]), legend=None)
        texto = f"Línea sólida: **{s.f_tienda}**. Punteada: promedio de las otras tiendas de la región {region}."
    elif s.f_region != "Todas":
        mensual = df_f.groupby(["mes_num", "mes", "tienda"], as_index=False)["ventas"].sum()
        mensual = mensual.rename(columns={"tienda": "serie"})
        dominio, colores = REGIONES[s.f_region], PALETA
        texto = f"Cada línea es una tienda de la región {s.f_region}. ¿Alguna se separa de las demás?"
    else:
        mensual = df_f.groupby(["mes_num", "mes", "region"], as_index=False)["ventas"].sum()
        mensual = mensual.rename(columns={"region": "serie"})
        dominio, colores = list(REGIONES), PALETA
        texto = "Cada línea es una región. Elijan una región en los filtros para ver sus tiendas."

    chart = alt.Chart(mensual).mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=70, filled=True)).encode(
        x=alt.X("mes:N", sort=MESES, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ventas:Q", title="Ventas (Q)", axis=alt.Axis(format="~s")),
        color=alt.Color("serie:N", title=None, scale=escala(dominio, colores), legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("serie:N", title="Serie"), alt.Tooltip("mes:N", title="Mes"),
                 alt.Tooltip("ventas:Q", title="Ventas (Q)", format=",.0f")],
    ).properties(height=340)
    if trazo is not None:
        chart = chart.encode(strokeDash=trazo)
    st.markdown("**Ventas por mes**")
    st.caption(texto)
    grafica(chart)
    codigo(COD_TIEMPO)


def vista_productos(df: pd.DataFrame, df_f: pd.DataFrame):
    s = st.session_state
    a, b = rango_meses()
    n_meses = b - a + 1
    anual = filtrar(df, con_meses=False)
    st.markdown("**Cada producto contra su mes típico**")
    st.caption("Mismos filtros de región y tienda. La flecha compara el promedio mensual del "
               "período elegido contra el promedio de todo el año.")
    cols = st.columns(len(s.f_productos))
    for col, producto in zip(cols, s.f_productos):
        actual = df_f.loc[df_f["producto"] == producto, "ventas"].sum()
        tipico = anual.loc[anual["producto"] == producto, "ventas"].sum() / len(MESES)
        delta = None if n_meses == len(MESES) or not tipico else f"{actual / n_meses / tipico - 1:+.0%}"
        col.metric(producto, f"Q {actual:,.0f}", delta, border=True)

    mensual = df_f.groupby(["mes_num", "mes", "producto"], as_index=False)["ventas"].sum()
    chart = alt.Chart(mensual).mark_line(strokeWidth=2.5, point=alt.OverlayMarkDef(size=70, filled=True)).encode(
        x=alt.X("mes:N", sort=MESES, title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("ventas:Q", title="Ventas (Q)", axis=alt.Axis(format="~s")),
        color=alt.Color("producto:N", title=None, scale=escala(PRODUCTOS, PALETA), legend=alt.Legend(orient="top")),
        tooltip=[alt.Tooltip("producto:N", title="Producto"), alt.Tooltip("mes:N", title="Mes"),
                 alt.Tooltip("ventas:Q", title="Ventas (Q)", format=",.0f")],
    ).properties(height=300)
    grafica(chart)


def vista_datos(df_f: pd.DataFrame):
    st.caption(f"{len(df_f):,} filas: una por día, tienda y producto. Hagan clic en una columna para ordenarla.")
    tabla = df_f[["fecha", "region", "tienda", "producto", "ventas", "tickets"]]
    st.dataframe(
        tabla, hide_index=True, width="stretch", height=360,
        column_config={
            "fecha": st.column_config.DateColumn("Fecha", format="DD/MM/YYYY"),
            "region": "Región", "tienda": "Tienda", "producto": "Producto",
            "ventas": st.column_config.NumberColumn("Ventas (Q)", format="%.2f"),
            "tickets": st.column_config.NumberColumn("Tickets"),
        },
    )
    st.download_button("Descargar CSV", tabla.to_csv(index=False).encode("utf-8"),
                       "ventas_cacao_quetzal.csv", "text/csv", icon=":material/download:")
    codigo(COD_DATOS)


# ───────────────────────────── Pantalla 3: caso resuelto ─────────────────────────────
def pantalla_resuelto(df: pd.DataFrame):
    barra_lateral()
    s = st.session_state
    if not s.festejado:
        st.balloons()
        s.festejado = True

    resueltos, _ = ranking()
    posicion = next((i for i, (e, _) in enumerate(resueltos) if e == s.equipo), None)

    hero("Caso cerrado", "¡Caso resuelto!",
         f"<b>{html.escape(s.equipo)}</b>, encontraron el pedido misterioso.", variante="resuelto")
    c = st.columns(4)
    c[0].metric("Tiempo", fmt_tiempo(s.fin - s.inicio), border=True)
    c[1].metric("Puntos", puntos(), border=True)
    c[2].metric("Acusaciones", len(s.intentos), border=True)
    c[3].metric("Posición", "—" if posicion is None else f"{posicion + 1}° de {len(resueltos)}", border=True)

    # Cifras del pedido calculadas desde los mismos datos que exploraron
    sospechoso = df[(df["tienda"] == SOLUCION["tienda"]) & (df["producto"] == SOLUCION["producto"])]
    por_mes = sospechoso.groupby("mes")["ventas"].sum()
    del_mes = por_mes[SOLUCION["mes"]]
    tipico = por_mes.drop(SOLUCION["mes"]).mean()
    dias = sospechoso["fecha"][sospechoso["mes"] == SOLUCION["mes"]].nunique()
    extra = del_mes - tipico

    encabezado(1, "Lo que pasó", f"{SOLUCION['tienda']} · {SOLUCION['mes']} · {SOLUCION['producto']}")
    with st.container(key="panel_historia"):
        st.markdown(
            f"Durante todo **{SOLUCION['mes'].lower()}**, alguien llegó cada día a la tienda de "
            f"**{SOLUCION['tienda']}** y pagó **un solo ticket** de unos **Q {extra / dias:,.0f}** en "
            f"**{SOLUCION['producto'].lower()}**. En total fueron **Q {extra:,.0f}** extra: ese producto "
            f"vendió **{del_mes / tipico - 1:+.0%}** contra su mes típico.\n\n"
            f"Lo curioso: en el **total anual**, {SOLUCION['tienda']} casi no se distinguía de sus vecinas. "
            "El pedido solo aparece al **filtrar** (región → tienda → mes) y **comparar** contra lo "
            "normal. Eso es justo lo que un dashboard dinámico permite y un reporte estático no.\n\n"
            "¿El comprador anónimo? **El Grupo 6.** Y el pedido era para ustedes…"
        )

    encabezado(2, "La sorpresa", "Se la ganaron.")
    with st.container(key="sorpresa"):
        st.markdown(SORPRESA)

    izq, der = st.columns(2, gap="large")
    with izq:
        encabezado(3, "Lo que usaron sin darse cuenta", "Los componentes de Streamlit detrás del juego.")
        with st.container(key="panel_componentes"):
            st.markdown(
                "- `st.selectbox` → elegir región, tienda y sus sospechas\n"
                "- `st.select_slider` → el rango de meses\n"
                "- `st.multiselect` → los productos\n"
                "- `st.metric` → indicadores con variación\n"
                "- `st.altair_chart` → las gráficas de barras y líneas\n"
                "- `st.dataframe` → la tabla que se puede ordenar\n"
                "- `st.button(disabled=...)` → acusar solo con las 3 sospechas\n"
                "- `st.sidebar` → el panel lateral con su tiempo y puntos\n"
                "- `st.session_state` → puntos, pistas e intentos\n"
                "- `st.cache_data` / `st.cache_resource` → datos y tablero compartido"
            )
            st.caption(f"Mientras investigaban, el script se ejecutó **{s.reejecuciones} veces**.")
    with der:
        encabezado(4, "Para discutir", "Compártanlo con la clase.")
        with st.container(key="panel_discusion"):
            st.markdown(
                "1. ¿Habrían encontrado el pedido con un reporte estático del total anual por tienda?\n"
                "2. ¿Qué filtro fue el decisivo para ustedes?\n"
                "3. ¿Qué pista falsa los distrajo más: febrero, mayo o Zona 10 como la tienda que más vende?"
            )


# ───────────────────────────── Vista del presentador ─────────────────────────────
@st.fragment(run_every=3)
def tablero_en_vivo():
    resueltos, investigando = ranking()
    c1, c2 = st.columns(2)
    c1.metric("Equipos investigando", investigando, border=True)
    c2.metric("Casos resueltos", len(resueltos), border=True)
    if not resueltos:
        st.info("Aún nadie resuelve el caso. ¿Quién será el primero?")
        return
    st.dataframe(
        pd.DataFrame([{"Lugar": f"{i + 1}°", "Equipo": e, "Puntos": d["puntos"], "Tiempo": fmt_tiempo(d["tiempo"]),
                       "Acusaciones": d.get("intentos", 0), "Pistas": d.get("pistas", 0)}
                      for i, (e, d) in enumerate(resueltos)]),
        hide_index=True, width="stretch",
    )


def pantalla_presentador(df: pd.DataFrame):
    hero("El caso del pedido misterioso · Grupo 6", "Tablero en vivo", "Se actualiza solo cada 3 segundos.")
    tablero_en_vivo()
    with st.expander("Controles del presentador", icon=":material/lock:"):
        pin = st.text_input("PIN", type="password")
        if pin and pin != PIN_PRESENTADOR:
            st.error("PIN incorrecto.")
        elif pin:
            if st.toggle("Mostrar la solución"):
                st.success(f"**{SOLUCION['tienda']}** · **{SOLUCION['mes']}** · **{SOLUCION['producto']}**")
            confirmo = st.checkbox("Confirmo que quiero borrar a todos los equipos")
            if st.button("Vaciar tablero", disabled=not confirmo):
                t = tablero_compartido()
                with t["candado"]:
                    t["equipos"].clear()
                st.toast("Tablero vaciado", icon=":material/delete:")


# ───────────────────────────── Principal ─────────────────────────────
def main():
    st.set_page_config(page_title="El caso del pedido misterioso", page_icon=":material/search:",
                       layout="wide", initial_sidebar_state="expanded")
    st.html(ESTILOS)
    iniciar_estado()
    st.session_state.reejecuciones += 1
    df = cargar_datos()

    if st.query_params.get("modo") == "presentador":
        pantalla_presentador(df)
        return
    pantallas = {"intro": pantalla_intro, "investigando": pantalla_investigacion, "resuelto": pantalla_resuelto}
    pantallas[st.session_state.etapa](df)


main()
