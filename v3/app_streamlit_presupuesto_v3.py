# -*- coding: utf-8 -*-
"""
Aplicación para la generación de presupuestos de acometidas - SERVICIUDAD E.S.P.
Permite calcular costos de obra civil, accesorios y generar un PDF con formato oficial.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from reportlab.lib.units import cm
import json
import time
import base64

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle

# Configuración de la página de Streamlit
st.set_page_config(
    page_title='Presupuesto - Cotizaciones - SERVICIUDAD', 
    page_icon='💧', 
    layout='wide',
    initial_sidebar_state='collapsed'
)

# Rutas de archivos de configuración y recursos
BASE_DIR = Path(__file__).parent
CFG_PATH = BASE_DIR / 'config_presupuesto_acometidas_v3.csv'
ASSET_HEADER_PDF = BASE_DIR / 'serviciudad_pdf_header.png'
ASSET_LOGO_UI = BASE_DIR / 'logo.jpg'
ASSET_FOOTER = BASE_DIR / 'serviciudad_pdf_footer.jpg'
STATE_PATH = BASE_DIR / 'consecutivo_state.json'
OUTPUT_DIR = BASE_DIR / 'salidas_pdf'
OUTPUT_DIR.mkdir(exist_ok=True)

# --- Paleta de colores y estilos visuales ---
PRIMARY = '#047AB3'
DARK = '#003555'
ACCENT = '#F79854'
BG1 = '#061826'
BG2 = '#0B2C3C'

# Inyectar CSS personalizado para mejorar la UI/UX y la tipografía
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', sans-serif;
}}

/* Ocultar elementos por defecto de Streamlit (footer, decoraciones) */
#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
header {{visibility: hidden;}}

.stApp {{
  background: radial-gradient(circle at 20% 20%, rgba(4,122,179,0.15), transparent 40%),
              radial-gradient(circle at 80% 80%, rgba(247,152,84,0.1), transparent 40%),
              linear-gradient(135deg, #0f172a, #1e293b);
  color: #f8fafc;
}}

.glass {{
  background: rgba(30, 41, 59, 0.7);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  border-radius: 16px;
  padding: 24px;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  margin-bottom: 20px;
}}

.h1 {{ 
    font-size: 36px; 
    font-weight: 800; 
    background: linear-gradient(90deg, #38bdf8, #818cf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 10px 0; 
}}

.sub {{ 
    color: #94a3b8; 
    font-size: 16px;
    margin: 0 0 24px 0; 
}}

/* Estilo para los botones */
.stButton>button, .stDownloadButton>button {{
  width: 100%;
  border-radius: 12px;
  border: none;
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: white;
  font-weight: 600;
  padding: 0.75rem 1.5rem;
  transition: all 0.3s ease;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}}

.stButton>button:hover, .stDownloadButton>button:hover {{
  transform: translateY(-2px);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
  filter: brightness(1.1);
}}

/* Estilo para inputs y selects */
div[data-baseweb="input"], div[data-baseweb="select"], textarea {{
  background: rgba(15, 23, 42, 0.6) !important;
  border-radius: 10px !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
}}

/* Quitar el relleno de las columnas de Streamlit para un look más limpio */
[data-testid="column"] {{
    padding: 0 10px;
}}

/* Estilo para etiquetas de inputs */
label p {{
    font-weight: 600 !important;
    color: #cbd5e1 !important;
}}

/* Formulario con Glassmorphism */
[data-testid="stForm"] {{
    background: rgba(30, 41, 59, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    border-radius: 16px;
    padding: 30px;
}}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_config(path: str) -> pd.DataFrame:
    """Carga el archivo CSV de configuración."""
    return pd.read_csv(path)

# Cargar la configuración global
cfg = load_config(CFG_PATH)

# ---------- Funciones auxiliares de configuración ----------

def cfg_get(section, key, default=''):
    """Obtiene un valor de configuración del DataFrame."""
    rows = cfg[(cfg.section==section) & (cfg.key==key) & (cfg.servicio.fillna('')=='')]
    return str(rows['valor'].iloc[0]) if not rows.empty else str(default)

def get_param(name: str, default=0.0) -> float:
    """Obtiene un parámetro numérico (IVA, ADM, etc)."""
    rows = cfg[(cfg.section=='parametros') & (cfg.key==name.upper())]
    return float(rows['valor'].iloc[0]) if not rows.empty else float(default)

def options_for(key: str):
    """Obtiene las opciones para un selectbox desde la configuración."""
    rows = cfg[(cfg.section=='listas') & (cfg.key==key)]
    return list(rows['valor'].dropna().unique())

def base_ml(servicio, diametro, profundidad, superficie) -> float:
    """Calcula el costo base por metro lineal según las condiciones."""
    rows = cfg[(cfg.section=='precios_base') & (cfg.servicio==servicio) & (cfg.diametro==diametro) &
               (cfg.profundidad==profundidad) & (cfg.superficie==superficie) & (cfg.item=='BASE_ML')]
    return float(rows['valor'].iloc[0]) if not rows.empty else 0.0

def accesorio(servicio, key, diametro) -> float:
    """Obtiene el costo unitario de un accesorio."""
    rows = cfg[(cfg.section=='accesorios') & (cfg.servicio==servicio) & (cfg.key==key) & (cfg.diametro==diametro)]
    return float(rows['valor'].iloc[0]) if not rows.empty else 0.0

def firma(servicio: str, key: str, default=''):
    """Obtiene los datos de los firmantes (nombre/cargo)."""
    rows = cfg[(cfg.section=='firmas') & (cfg.key==key) & (cfg.servicio==servicio)]
    if rows.empty:
        rows = cfg[(cfg.section=='firmas') & (cfg.key==key) & (cfg.servicio.fillna('')=='')]
    return str(rows['valor'].iloc[0]) if not rows.empty else str(default)

# Parámetros constantes cargados desde el CSV
IVA = get_param('IVA', 0.19)
ADM = get_param('ADM', 0.10)
UTIL = get_param('UTILIDAD', 0.05)

EMPRESA = cfg_get('documento','EMPRESA','SERVICIUDAD ESP')
NIT = cfg_get('documento','NIT','')
NUIR_DEFAULT = cfg_get('documento','NUIR_DEFAULT','')
PREFIJO = cfg_get('documento','CONSECUTIVO_PREFIJO','PR')
DIGITOS = int(cfg_get('documento','CONSECUTIVO_DIGITOS','6'))

# ---------- Persistencia de Consecutivos ----------

def _load_state():
    """Carga el estado de los consecutivos desde un archivo JSON."""
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding='utf-8'))
        except Exception:
            return {}
    return {}

def _save_state(state: dict):
    """Guarda el estado de los consecutivos en un archivo JSON."""
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

def _get_image_base64(path):
    """Convierte una imagen local a base64 para inyectarla en un tag img de HTML directo."""
    try:
        with open(path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    except Exception:
        return ""

def next_consecutivo(prefix: str, digits: int) -> str:
    """Genera el siguiente número de consecutivo basado en el año actual."""
    year = datetime.now(timezone(timedelta(hours=-5))).year
    state = _load_state()
    key = f"{prefix}-{year}"
    n = int(state.get(key, 0)) + 1
    state[key] = n
    _save_state(state)
    return f"{prefix}-{year}-{n:0{digits}d}"


def money(x: float) -> str:
    """Formatea un número como moneda colombiana."""
    return f"$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.')


def build_pdf_bytes(meta: dict, items_df: pd.DataFrame, totals: dict) -> bytes:
    """
    Construye el archivo PDF en memoria siguiendo los requerimientos de diseño de SERVICIUDAD.
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    W, H = letter

    # Ajuste de márgenes (2.5 cm internos)
    M = 2.5 * cm
    content_w = W - 2 * M

    # Coordenadas fijas para la zona de firmas
    SIG_LINE_Y = M + 2.0 * cm
    SIG_RUBRIC_SPACE = 1.0 * cm
    SIG_TOP = SIG_LINE_Y + SIG_RUBRIC_SPACE

    # Posición de textos bajo la línea de firma
    NAME_Y = SIG_LINE_Y - 0.7 * cm
    CARGO_Y = SIG_LINE_Y - 1.3 * cm

    # --- Cabecera ---
    header_h = 3.2 * cm
    # Mantenemos un buen margen superior para el banner horizontal original de la plantilla
    header_y = H - M - header_h

    try:
        c.drawImage(
            ASSET_HEADER_PDF,
            M, header_y,
            width=content_w, height=header_h,
            preserveAspectRatio=False, mask='auto'
        )
    except Exception:
        pass

    # --- Pie de página ---
    # footer_h = 0.35 * cm
    # footer_y = M
    # try:
    #     c.drawImage(
    #         ASSET_FOOTER,
    #         M, footer_y,
    #         width=content_w, height=footer_h,
    #         preserveAspectRatio=True, mask='auto'
    #     )
    # except Exception:
    #     pass

    # --- Datos de control (NUIR, Consecutivo, Fecha) alineados a la derecha ---
    # Al usar el banner, bajamos un poco más el texto para separar del logo
    info_y = header_y - 0.8 * cm
    
    c.setFillColor(colors.black)
    c.setFont('Helvetica-Bold', 9)
    c.drawRightString(W - M, info_y, f"NUIR {meta.get('nuir','')}")
    c.setFont('Helvetica', 9)
    c.drawRightString(W - M, info_y - 0.5 * cm, f"Consecutivo: {meta.get('consecutivo','')}")
    c.drawRightString(W - M, info_y - 1.0 * cm, f"Fecha: {meta.get('fecha_visible','')}")

    # --- Títulos del documento ---
    y = info_y - 1.5 * cm
    c.setFont('Helvetica-Bold', 13)
    c.drawCentredString(W / 2, y, meta.get("tipo_documento", "COTIZACIÓN DE SERVICIO"))
    y -= 0.6 * cm
    c.drawCentredString(W / 2, y, "")

    # --- Bloque de información del cliente (2 columnas) ---
    y -= 1.0 * cm
    xL = M
    xR = M + content_w * 0.55  # Ajuste para que la segunda columna esté más a la derecha

    # Reducido el salto de línea para ganar más espacio en la misma página
    line_h = 0.45 * cm
    step = 0.9 * cm

    def field(x, y, label, value):
        c.setFont('Helvetica-Bold', 9)
        c.drawString(x, y, label)
        c.setFont('Helvetica', 9)
        # Reemplazar los guiones bajos por espacios en blanco para la vista
        val_str = str(value).replace("_", " ") if value is not None else ""
        c.drawString(x, y - line_h, val_str)

    field(xL, y, "SERVICIO", meta.get("servicio", ""))
    field(xR, y, "DIRECCIÓN", meta.get("direccion", ""))
    y -= step

    field(xL, y, "NOMBRE DEL CLIENTE", meta.get("nombre", ""))
    field(xR, y, "CÉDULA", meta.get("cedula", ""))
    y -= step

    field(xL, y, "EMAIL", meta.get("email", ""))
    field(xR, y, "TELÉFONO", meta.get("telefono", ""))
    y -= step

    field(xL, y, "DIÁMETRO ACOMETIDA", meta.get("diametro", ""))
    field(xR, y, "TIPO DE SUPERFICIE", meta.get("superficie", ""))
    y -= step

    field(xL, y, "PROFUNDIDAD DE EXCAVACIÓN", meta.get("profundidad", ""))
    field(xR, y, "CAJA DE INSPECCIÓN REQUIERE", meta.get("caja_req", ""))
    y -= step

    field(xL, y, "SILLA Y PVC", meta.get("silla_req", ""))
    field(xR, y, "BOQUILLA MORTERO", meta.get("boq_req", ""))
    y -= step + 0.3 * cm

    # --- Tabla de ítems ---
    data = [list(items_df.columns)] + items_df.values.tolist()
    col_widths = [1.2 * cm, 7.5 * cm, 1.6 * cm, 1.6 * cm, 2.3 * cm, 2.4 * cm]

    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 8),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
    ]))

    tw, th = t.wrapOn(c, content_w, H)
    table_top = y
    table_bottom = table_top - th
    t.drawOn(c, M, table_bottom)

    # --- Cálculo de cordenadas para Totales (Flotando debajo de la tabla de forma segura) ---
    totals_start_y = table_bottom - 0.8 * cm

    # --- Totales (Alineados a la derecha de forma dinámica) ---
    x_val = W - M 
    x_lab = x_val - 8.5 * cm  # Ancho del bloque de etiquetas

    current_y = totals_start_y

    tot_y_top = current_y + 0.45 * cm
    c.setStrokeColor(colors.HexColor(DARK))
    c.setLineWidth(1.0)
    c.line(x_lab, tot_y_top, x_val, tot_y_top)

    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_lab, current_y, "COSTO DIRECTO")
    c.drawRightString(x_val, current_y, money(totals["costo_directo"]))
    current_y -= 0.5 * cm
    
    c.setFont("Helvetica", 9)
    c.drawString(x_lab, current_y, "ADMINISTRACIÓN")
    c.drawRightString(x_val - 2.8*cm, current_y, f"{int(ADM*100)}%")
    c.drawRightString(x_val, current_y, money(totals["admin"]))
    current_y -= 0.5 * cm

    c.drawString(x_lab, current_y, "UTILIDAD")
    c.drawRightString(x_val - 2.8*cm, current_y, f"{int(UTIL*100)}%")
    c.drawRightString(x_val, current_y, money(totals["utilidad"]))
    current_y -= 0.35 * cm
    
    # Línea divisoria gris
    c.setStrokeColor(colors.grey)
    c.setLineWidth(0.5)
    c.line(x_lab, current_y, x_val, current_y)
    current_y -= 0.45 * cm
    
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_lab, current_y, "TOTAL ACOMETIDA")
    c.drawRightString(x_val, current_y, money(totals["subtotal"]))
    current_y -= 0.5 * cm
    
    c.setFont("Helvetica", 9)
    c.drawString(x_lab, current_y, "IVA - TOTAL ACOMETIDA")
    c.drawRightString(x_val - 2.8*cm, current_y, f"{int(IVA*100)}%")
    c.drawRightString(x_val, current_y, money(totals["iva"]))
    current_y -= 0.35 * cm
    
    # Línea fuerte de cierre antes del gran total
    c.setStrokeColor(colors.HexColor(DARK))
    c.setLineWidth(1.0)
    c.line(x_lab, current_y, x_val, current_y)
    current_y -= 0.5 * cm
    
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_lab, current_y, "VALOR TOTAL")
    c.drawRightString(x_val, current_y, money(totals["total"]))

    # --- Bloque de Firmas ---
    # Garantiza que quede ordenadamente debajo de los totales y sin rayar el footer
    SIG_LINE_Y = current_y - 2.0 * cm 
    NAME_Y = SIG_LINE_Y - 0.6 * cm
    CARGO_Y = SIG_LINE_Y - 1.1 * cm

    left_sig_x1 = M
    left_sig_x2 = M + content_w * 0.42
    right_sig_x1 = M + content_w * 0.55
    right_sig_x2 = W - M

    c.setStrokeColor(colors.black)
    c.setLineWidth(0.8)

    # Líneas para firma
    c.line(left_sig_x1, SIG_LINE_Y, left_sig_x2, SIG_LINE_Y)
    c.line(right_sig_x1, SIG_LINE_Y, right_sig_x2, SIG_LINE_Y)

    # Nombres de firmantes
    c.setFont("Helvetica-Bold", 9)
    c.drawString(left_sig_x1, NAME_Y, meta.get("firma1_nombre", ""))
    c.drawString(right_sig_x1, NAME_Y, meta.get("firma2_nombre", ""))

    # Cargos de firmantes
    c.setFont("Helvetica", 8)
    c.drawString(left_sig_x1, CARGO_Y, meta.get("firma1_cargo", ""))
    c.drawString(right_sig_x1, CARGO_Y, meta.get("firma2_cargo", ""))

    c.showPage()
    c.save()
    return buf.getvalue()


def save_config_updates(updates: dict, servicio: str = ''):
    """Actualiza los valores de configuración en el archivo CSV."""
    global cfg
    df = cfg.copy()
    for (section, key), value in updates.items():
        mask = (df.section==section) & (df.key==key) & (df.servicio.fillna('')==servicio)
        if mask.any():
            df.loc[mask, 'valor'] = str(value)
        else:
            df = pd.concat([df, pd.DataFrame([{
                'section': section, 'key': key, 'servicio': servicio,
                'diametro':'','profundidad':'','superficie':'','item':'','valor': str(value)
            }])], ignore_index=True)
    df.to_csv(CFG_PATH, index=False, encoding='utf-8')
    st.cache_data.clear()
    cfg = load_config(CFG_PATH)


# ---------- Estado inicial y valores predeterminados ----------

# Limpiar guiones bajos para visualización amigable
def clean_label(text):
    return text.replace('_', ' ')

DEFAULTS = {
    'nuir': NUIR_DEFAULT,
    'tipo_documento': None,
    'servicio': options_for('SERVICIO')[0] if options_for('SERVICIO') else 'ACUEDUCTO',
    'diametro': options_for('DIAMETRO')[0] if options_for('DIAMETRO') else '6"',
    'profundidad': options_for('PROFUNDIDAD')[0] if options_for('PROFUNDIDAD') else '0 a 1 m',
    'superficie': options_for('TIPO_SUPERFICIE')[0] if options_for('TIPO_SUPERFICIE') else 'CON_PAVIMENTO',
    'ml': 1,
    'direccion': '',
    'nombre': '',
    'cedula': '',
    'email': '',
    'telefono': '',
    'caja_req': options_for('CAJA_INSPECCION')[1] if len(options_for('CAJA_INSPECCION'))>1 else 'NO_REQUIERE',
    'cant_caja': 0,
    'silla_req': options_for('SILLA_PVC')[1] if len(options_for('SILLA_PVC'))>1 else 'NO_REQUIERE',
    'cant_silla': 0,
    'boq_req': options_for('BOQUILLA_MORTERO')[1] if len(options_for('BOQUILLA_MORTERO'))>1 else 'NO_LO_REQUIERE',
    'cant_boq': 0,
}

for k,v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

if 'form_key' not in st.session_state:
    st.session_state.form_key = 0

def reset_form():
    """Limpia todos los campos del formulario y fuerza reinicio de UI."""
    for key in list(st.session_state.keys()):
        if key not in ['authenticated', 'form_key']:
            del st.session_state[key]
    st.session_state.form_key += 1
    st.rerun()

# ---------- Sistema de Login ----------
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    # Ampliamos la caja central reduciendo los márgenes laterales (cambiamos a 1.8 en el centro)
    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Integramos Logo, Títulos y Formulario en una Sola "Caja" sin usar divs anidados externos
        with st.form("login_form"):
            st.markdown(f"""
            <div style="text-align: center; margin-bottom: 25px;">
                <img src="data:image/jpeg;base64,{_get_image_base64(ASSET_LOGO_UI)}" width="140" style="border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); margin-bottom: 20px;">
                <h2 style="color: white; margin-bottom: 5px; font-weight: 800; font-size: 32px;">Acceso Restringido</h2>
                <p style="color: #94a3b8; font-size: 16px; margin-bottom: 0;">Por favor, identifícate para ingresar al aplicativo.</p>
            </div>
            """, unsafe_allow_html=True)
            
            username = st.text_input("Correo electrónico", placeholder="correo@serviciudad.com")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button("Ingresar", use_container_width=True)
            
            if submit_button:
                # Obtenemos las credenciales desde los secretos inyectados o usamos unas por defecto en modo local de depuración
                VALID_USER = st.secrets.get("admin_username", "adminaplicativo@serviciudad.com")
                VALID_PASS = st.secrets.get("admin_password", "adminserviciudad**")

                if username.strip().lower() == VALID_USER and password == VALID_PASS:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("❌ Credenciales incorrectas.")
                    
    # Detenemos la ejecución del resto del script para proteger la app
    st.stop()


# ---------- Interfaz de Usuario (Layout) ----------

# Contenedor principal para centrar tanto el título como el logo
col_espacio_izq, col_central, col_espacio_der = st.columns([1, 6, 1])

with col_central:
    # Usamos Flexbox de CSS para alinear perfectamente el texto a la izquierda y el logo a la derecha,
    # pero manteniendo todo el bloque centrado en la pantalla.
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: center; gap: 30px; margin-top: 10px; margin-bottom: 30px;">
        <div style="text-align: right;">
            <h1 style="font-size: 38px; font-weight: 800; background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;">SERVICIUDAD E.S.P</h1>
            <p style="color: #94a3b8; font-size: 16px; margin: 0; margin-top: 5px;">Sistema Inteligente de Presupuesto para Acometidas</p>
        </div>
        <div>
            <img src="data:image/jpeg;base64,{_get_image_base64(ASSET_LOGO_UI)}" width="110" style="border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);">
        </div>
    </div>
    """, unsafe_allow_html=True)

# Layout centralizado principal
_, main_col, _ = st.columns([1, 8, 1], gap='large')

with main_col:
    # Botones centrados y anchos
    if st.button('🧹 LIMPIAR FORMULARIO', use_container_width=True, type='primary', help='Borrar todos los datos y reiniciar'):
        reset_form()

    # Expandible para configuraciones técnicas (firmas y NUIR)
    with st.expander('⚙️ Opciones Avanzadas (Documento y Firmas)', expanded=False):
        cA, cB = st.columns(2)
        with cA:
            nuir_def = st.text_input('NUIR por defecto', value=NUIR_DEFAULT)
            pref = st.text_input('Prefijo para Consecutivo', value=PREFIJO)
            dig = st.number_input('Dígitos numéricos', min_value=3, max_value=10, value=DIGITOS, step=1)
        with cB:
            f1n = st.text_input('Nombre Firmante 1', value=firma(st.session_state.servicio, 'FIRMA1_NOMBRE'))
            f1c = st.text_input('Cargo Firmante 1', value=firma(st.session_state.servicio, 'FIRMA1_CARGO'))
            f2n = st.text_input('Nombre Firmante 2', value=firma(st.session_state.servicio, 'FIRMA2_NOMBRE'))
            f2c = st.text_input('Cargo Firmante 2', value=firma(st.session_state.servicio, 'FIRMA2_CARGO'))

        if st.button('💾 Guardar Cambios'):
            save_config_updates({
                ('documento','NUIR_DEFAULT'): nuir_def,
                ('documento','CONSECUTIVO_PREFIJO'): pref,
                ('documento','CONSECUTIVO_DIGITOS'): str(int(dig)),
                ('firmas','FIRMA1_NOMBRE'): f1n,
                ('firmas','FIRMA1_CARGO'): f1c,
                ('firmas','FIRMA2_NOMBRE'): f2n,
                ('firmas','FIRMA2_CARGO'): f2c,
            })
            st.success('Cambios guardados exitosamente.')

    # Formulario principal de captura de datos
    with st.form(f'form_presupuesto_{st.session_state.form_key}'):
        st.markdown('#### 👤 1. Información Cliente')
        
        # Ocultamos NUIR del formulario
        st.session_state.nuir = NUIR_DEFAULT
        
        ops_tipo_doc = ['COTIZACIÓN DE SERVICIO', 'PRESUPUESTO DE SERVICIO']
        
        # Obtenemos valor actual, si no es uno de la lista lo dejamos como None
        curr_val = st.session_state.get('tipo_documento')
        curr_idx = ops_tipo_doc.index(curr_val) if curr_val in ops_tipo_doc else None
        
        st.session_state.tipo_documento = st.selectbox('📄 Tipo de Documento', ops_tipo_doc, index=curr_idx, placeholder='Seleccione el tipo el tipo de documento')

        col1, col2 = st.columns(2)
        with col1:
            st.session_state.nombre = st.text_input('📝 Nombre - Razón Social', value=st.session_state.nombre)
            st.session_state.cedula = st.text_input('🪪 Identificación (Cédula - NIT)', value=st.session_state.cedula)
            st.session_state.direccion = st.text_input('📍 Dirección de la obra', value=st.session_state.direccion)
        with col2:
            st.session_state.servicio = st.selectbox('💧 Tipo de Servicio', options_for('SERVICIO'), index=options_for('SERVICIO').index(st.session_state.servicio) if st.session_state.servicio in options_for('SERVICIO') else 0)
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                st.session_state.telefono = st.text_input('📱 Teléfono', value=st.session_state.telefono)
            with col2_2:
                st.session_state.email = st.text_input('📧 Email', value=st.session_state.email)

        st.markdown('---')
        st.markdown('#### 📏 2. Especificaciones Técnicas')
        
        col3, col4, col5 = st.columns(3)
        with col3:
            # Ahora permite ingresar texto o seleccionar de la lista (simulado con selectbox que permite escritura si lo soporta Streamlit nativo, o mantieniendo lista con ayuda visual)
            st.session_state.diametro = st.selectbox('⭕ Diámetro Acometida', options_for('DIAMETRO'), index=options_for('DIAMETRO').index(st.session_state.diametro) if st.session_state.diametro in options_for('DIAMETRO') else 0, help="Seleccione el diámetro base.")
            
        with col4:
            st.session_state.profundidad = st.selectbox('↕️ Profundidad', options_for('PROFUNDIDAD'), index=options_for('PROFUNDIDAD').index(st.session_state.profundidad) if st.session_state.profundidad in options_for('PROFUNDIDAD') else 0)
            
        with col5:
            st.session_state.ml = st.number_input('📏 Longitud (m lineales)', min_value=1, value=int(st.session_state.ml), step=1)
        
        raw_ops = options_for('TIPO_SUPERFICIE')
        st.session_state.superficie = st.radio('🛣️ Tipo de Superficie', raw_ops, format_func=clean_label, index=raw_ops.index(st.session_state.superficie) if st.session_state.superficie in raw_ops else 0, horizontal=True)


        st.markdown('---')
        st.markdown('#### 🛠️ 3. Accesorios y Complementos')
        a1, a2, a3 = st.columns(3)
        with a1:
            ops_caja = options_for('CAJA_INSPECCION')
            st.session_state.caja_req = st.selectbox('📦 Caja de inspección', ops_caja, format_func=clean_label, index=ops_caja.index(st.session_state.caja_req) if st.session_state.caja_req in ops_caja else 0)
        with a2:
            ops_silla = options_for('SILLA_PVC')
            st.session_state.silla_req = st.selectbox('🪑 Silla Y - PVC', ops_silla, format_func=clean_label, index=ops_silla.index(st.session_state.silla_req) if st.session_state.silla_req in ops_silla else 0)
        with a3:
            ops_boq = options_for('BOQUILLA_MORTERO')
            st.session_state.boq_req = st.selectbox('🧱 Boquilla en mortero', ops_boq, format_func=clean_label, index=ops_boq.index(st.session_state.boq_req) if st.session_state.boq_req in ops_boq else 0)

        st.markdown('<br>', unsafe_allow_html=True)

        # Centrar el botón del formulario
        col_btn_sub1, col_btn_sub2, col_btn_sub3 = st.columns([1, 2, 1])
        with col_btn_sub2:
            generar = st.form_submit_button('🚀 CALCULAR Y PREPARAR DOCUMENTO PDF', use_container_width=True)

# ---------- Lógica de Procesamiento y Generación ----------

if generar:
    if not st.session_state.tipo_documento:
        st.error('❌ **ES NECESARIO SELECCIONAR UN TIPO DE DOCUMENTO** para proceder.', icon='🚨')
        st.stop()
        
    # Obtener valores directamente desde las constantes globales fijadas en el config CSV
    tasa_iva = IVA
    tasa_adm = ADM
    tasa_util = UTIL

    # Pantalla de carga (UX mejorada)
    with st.status("🛠️ Generando presupuesto...", expanded=True) as status:
        st.write("Cargando precios base...")
        time.sleep(0.5)
        
        servicio = st.session_state.servicio
        diametro = st.session_state.diametro
        profundidad = st.session_state.profundidad
        superficie = st.session_state.superficie
        ml = int(st.session_state.ml)

        # Cálculos de costos base
        base_unit = base_ml(servicio, diametro, profundidad, superficie)
        base_total = base_unit * ml

        # Cálculos de accesorios
        costo_caja_u = accesorio(servicio, 'CAJA_INSPECCION', diametro)
        costo_silla_u = accesorio(servicio, 'SILLA_PVC', diametro)
        costo_boq_u = accesorio(servicio, 'BOQUILLA_MORTERO', diametro)

        # Verificación lógica de requerimientos. Se asume 1 unidad base de cada cosa si requieren SI
        caja_si = 'SI' in str(st.session_state.caja_req).upper()
        silla_si = 'SI' in str(st.session_state.silla_req).upper()
        boq_si = 'SI' in str(st.session_state.boq_req).upper()

        total_caja = (1 * costo_caja_u) if caja_si else 0.0
        total_silla = (1 * costo_silla_u) if silla_si else 0.0
        total_boq = (1 * costo_boq_u) if boq_si else 0.0

        # Totales financieros dinámicos
        costo_directo = base_total + total_caja + total_silla + total_boq
        admin = costo_directo * tasa_adm
        utilidad = (costo_directo + admin) * tasa_util
        subtotal = costo_directo + admin + utilidad
        iva = subtotal * tasa_iva
        total = subtotal + iva

        st.write("Generando consecutivo...")
        consecutivo = next_consecutivo(PREFIJO, DIGITOS)
        fecha_visible = datetime.now(timezone(timedelta(hours=-5))).strftime('%d/%m/%Y %H:%M')

        # Construcción de la tabla de ítems para visualización y PDF
        items = []
        items.append({'Ítem':'1.1','Descripción':'Incluye: Señalización - Excavaciones\nLlenos- Retiros - Tuberia Novafort-\nSub base - Transporte','Unidad':'ML','Cantidad': ml,'Valor Unitario': money(base_unit),'Valor Total': money(base_total)})
        items.append({'Ítem':'1.2.','Descripción':'Caja de inspección en concreto de\n17,2 Mpa, tapa reforzada en concreto de 20,7 Mpa','Unidad':'UND','Cantidad': 1 if caja_si else 0,'Valor Unitario': money(costo_caja_u),'Valor Total': money(total_caja)})
        items.append({'Ítem':'1.3','Descripción':'Accesorio alcantarillado silla Yee\nPVC','Unidad':'UND','Cantidad': 1 if silla_si else 0,'Valor Unitario': money(costo_silla_u),'Valor Total': money(total_silla)})
        desc_boq = 'Emboquillado de tubo en mortero 1:2' if boq_si else 'No lleva Boquilla Mortero'
        items.append({'Ítem':'1.4','Descripción': desc_boq,'Unidad':'UND','Cantidad': 1 if boq_si else 0,'Valor Unitario': money(costo_boq_u),'Valor Total': money(total_boq)})

        items_df = pd.DataFrame(items)

        st.write("Construyendo PDF oficial...")
        meta = {
            'nuir': st.session_state.nuir,
            'tipo_documento': st.session_state.tipo_documento,
            'consecutivo': consecutivo,
            'fecha_visible': fecha_visible,
            'servicio': servicio,
            'direccion': st.session_state.direccion,
            'nombre': st.session_state.nombre,
            'cedula': st.session_state.cedula,
            'email': st.session_state.email,
            'telefono': st.session_state.telefono,
            'diametro': diametro,
            'superficie': superficie,
            'profundidad': profundidad,
            'caja_req': st.session_state.caja_req,
            'silla_req': st.session_state.silla_req,
            'boq_req': st.session_state.boq_req,
            'firma1_nombre': firma(servicio, 'FIRMA1_NOMBRE'),
            'firma1_cargo': firma(servicio, 'FIRMA1_CARGO'),
            'firma2_nombre': firma(servicio, 'FIRMA2_NOMBRE'),
            'firma2_cargo': firma(servicio, 'FIRMA2_CARGO'),
        }

        # Override explícito solo para el cálculo temporal si se requiere global local
        
        # En vez de "global ADM", simplemente reasignamos el diccionario de totales:
        totals = {'costo_directo': costo_directo,'admin': admin,'utilidad': utilidad,'subtotal': subtotal,'iva': iva,'total': total}

        pdf_bytes = build_pdf_bytes(meta, items_df[['Ítem','Descripción','Unidad','Cantidad','Valor Unitario','Valor Total']], totals)

        # Guardar en servidor de forma silenciosa
        safe_fecha = datetime.now(timezone(timedelta(hours=-5))).strftime('%Y%m%d_%H%M')
        out_name = f"{consecutivo}_{safe_fecha}.pdf"
        (OUTPUT_DIR / out_name).write_bytes(pdf_bytes)
        
        status.update(label="✅ Presupuesto completado", state="complete", expanded=False)

    # Mostrar Resultados Finales en la UI en el centro
    with main_col:
        st.toast("¡Cálculo finalizado exitosamente!", icon='🚀')
        
        st.markdown('<div class="resultado-container" style="background: rgba(30,41,59,0.7); padding: 25px; border-radius: 16px; border: 1px solid rgba(255,255,255,0.1); margin-top: 20px;">', unsafe_allow_html=True)
        st.subheader('📊 Detalle de Ítems')
        st.dataframe(items_df, use_container_width=True)

        # Métricas clave con estilo Streamlit
        m1, m2, m3 = st.columns(3)
        m1.metric('COSTO DIRECTO', money(costo_directo))
        m2.metric('SUBTOTAL (CON AIU)', money(subtotal))
        m3.metric('VALOR TOTAL (IVA INC.)', money(total))

        st.markdown('<br>', unsafe_allow_html=True)
        # Botón de descarga prominente centrado
        dl_col1, dl_col2, dl_col3 = st.columns([1, 2, 1])
        with dl_col2:
            st.download_button(
                label='💾 DESCARGAR PDF OFICIAL', 
                data=pdf_bytes, 
                file_name=out_name, 
                mime='application/pdf',
                key='download-pdf-btn',
                use_container_width=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

