import datetime
from datetime import time
from google import genai
import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
import bcrypt
import base64
import time
import streamlit as st

# --- CONFIGURACIÓN DE RATE LIMITING ---
MAX_ATTEMPTS = 3
LOCKOUT_DURATION = 60  # Segundos de bloqueo

# Inicializar variables de Rate Limiting por pestaña
for key in ["login", "registro", "recuperar"]:
    if f"{key}_attempts" not in st.session_state:
        st.session_state[f"{key}_attempts"] = 0
    if f"{key}_lockout" not in st.session_state:
        st.session_state[f"{key}_lockout"] = 0


def esta_bloqueado(key):
    """Verifica si un formulario específico está bloqueado."""
    tiempo_actual = time.time()
    lockout_time = st.session_state[f"{key}_lockout"]
    if lockout_time > tiempo_actual:
        tiempo_restante = int(lockout_time - tiempo_actual)
        return True, tiempo_restante
    return False, 0


def registrar_intento_fallido(key):
    """Suma un intento fallido y activa el bloqueo si supera el límite."""
    st.session_state[f"{key}_attempts"] += 1
    if st.session_state[f"{key}_attempts"] >= MAX_ATTEMPTS:
        st.session_state[f"{key}_lockout"] = time.time() + LOCKOUT_DURATION


def resetear_intentos(key):
    """Limpia los intentos al completar una acción con éxito."""
    st.session_state[f"{key}_attempts"] = 0
    st.session_state[f"{key}_lockout"] = 0


# Configuración de la página
st.set_page_config(
    page_title="NutriTrack & Recetas", page_icon="🥗", layout="wide"
)

# Inicializar cliente de Gemini utilizando el Secret de Streamlit Cloud
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


# Función para obtener una conexión fresca a la base de datos
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])

# --- FUNCIONES DE SEGURIDAD ACTUALIZADAS ---
def registrar_nuevo_usuario(nombre, email, password, pin):
    hashed_pw = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    try:
        execute_db(
            """
            INSERT INTO usuarios (nombre, email, password, pin_seguridad)
            VALUES (%s, %s, %s, %s)
            """,
            (nombre, email, hashed_pw, pin),
        )
        return True, "Ok"
    except Exception as e:
        return False, str(e)


def cambiar_password_db(email, pin, nueva_password):
    # Validar que el PIN corresponda al correo
    user = run_query(
        "SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s) AND"
        " pin_seguridad = %s",
        (email, pin),
    )
    if not user:
        return False, "El correo o el PIN de seguridad son incorrectos."

    # Si el PIN es correcto, actualizamos la contraseña
    hashed_pw = bcrypt.hashpw(
        nueva_password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")
    try:
        execute_db(
            """
            UPDATE usuarios 
            SET password = %s 
            WHERE LOWER(email) = LOWER(%s)
            """,
            (hashed_pw, email),
        )
        return True, "¡Contraseña actualizada con éxito!"
    except Exception as e:
        return False, f"Error al actualizar: {e}"

def verificar_usuario(email, password):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, password FROM usuarios WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()
            # Verificar la contraseña ingresada contra el hash guardado
            if user and bcrypt.checkpw(
                password.encode("utf-8"), user[2].encode("utf-8")
            ):
                return {"id": user[0], "nombre": user[1], "email": email}
        return None
    finally:
        conn.close()

def run_query(query, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
    finally:
        conn.close()


def execute_db(query, params=None):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def guardar_receta_db(categoria, tiempo, cuerpo_receta):
    user_id = st.session_state.user["id"]
    try:
        execute_db(
            """
            INSERT INTO recetas (user_id, categoria, tiempo, cuerpo)
            VALUES (%s, %s, %s, %s)
            """,
            (user_id, categoria, tiempo, cuerpo_receta),
        )
        st.success("¡Receta guardada exitosamente en tu cuenta!")
    except Exception as e:
        st.error(f"Error al guardar la receta: {e}")

# --- CONTROL DE SESIÓN CON CENTRADO Y LOGO OPTIMIZADO Y AGRANDADO ---
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    # --- CSS DE STREAMLIT ALINEADO A VITA COACH ---
    st.markdown(
        """
        <style>
        #MainMenu, footer, header {visibility: hidden;}
        
        /* FONDO PRINCIPAL EN TONOS AZUL TEAL Y VERDE MENTA */
        .stApp {
            background: radial-gradient(circle at 20% 20%, #0d5c63 0%, #0B3B4F 50%),
                        radial-gradient(circle at 80% 80%, #062f3a 0%, #041d24 100%);
            background-attachment: fixed;
        }
        
        .main .block-container {
            max-width: 480px !important;
            padding-top: 1.5rem !important;
            padding-bottom: 2rem !important;
            margin: 0 auto !important;
        }

        /* CARD Y TAMAÑO AMPLIADO DEL LOGO */
        .logo-card-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 1.5rem;
            width: 100%;
        }
        .logo-card {
            background: rgba(255, 255, 255, 0.98);
            padding: 10px;
            border-radius: 20px;
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.45);
            width: 100%;
            max-width: 360px; /* Aumentado para que resalte completamente */
            text-align: center;
            border: 2px solid rgba(46, 204, 113, 0.4);
        }
        .logo-card img {
            width: 100%;
            height: auto;
            max-height: 200px; /* Mayor espacio vertical para legibilidad */
            display: block;
            border-radius: 12px;
            object-fit: contain;
        }

        /* STYLING DE PESTAÑAS (FORZADO BRUTO CON PALETA VITA COACH) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background-color: rgba(11, 59, 79, 0.6) !important;
            padding: 6px;
            border-radius: 14px;
            margin-bottom: 1.2rem;
            border: 1px solid rgba(255, 255, 255, 0.15);
            width: 100%;
        }

        .stTabs [data-baseweb="tab"],
        .stTabs [data-baseweb="tab"] *,
        .stTabs [data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 0.9 !important;
            font-weight: 600 !important;
        }

        /* PESTAÑA ACTIVA CON VERDE MENTA (#10B981) */
        .stTabs [aria-selected="true"] {
            background-color: #10B981 !important;
            border-radius: 10px !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }

        .stTabs [aria-selected="true"] *,
        .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            font-weight: 800 !important;
        }

        /* OCULTA LÍNEA DE SELECCIÓN POR DEFECTO */
        .stTabs [data-baseweb="tab-highlight-title"],
        .stTabs [data-baseweb="tab-border"] {
            background-color: transparent !important;
            display: none !important;
        }

        /* CONTENEDOR DEL FORMULARIO GLASSMORPHISM */
        [data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.06) !important;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 22px !important;
            padding: 1.8rem !important;
            box-shadow: 0 10px 35px 0 rgba(0, 0, 0, 0.4);
        }

        /* ETIQUETAS DE CAMPOS DE TEXTO */
        [data-testid="stWidgetLabel"] label, 
        .stTextInput label {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        /* CAJAS DE ENTRADA
