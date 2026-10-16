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

        /* CAJAS DE ENTRADA DE TEXTO */
        .stTextInput input,
        div[data-baseweb="input"] input {
            background-color: #ffffff !important;
            color: #0B3B4F !important;
            -webkit-text-fill-color: #0B3B4F !important;
            border: 1px solid #10B981 !important;
            border-radius: 10px !important;
            font-weight: 500 !important;
        }

        /* AUTOCOMPLETADO DEL NAVEGADOR */
        .stTextInput input:-webkit-autofill,
        .stTextInput input:-webkit-autofill:hover, 
        .stTextInput input:-webkit-autofill:focus {
            -webkit-text-fill-color: #0B3B4F !important;
            -webkit-box-shadow: 0 0 0px 1000px #ffffff inset !important;
            transition: background-color 5000s ease-in-out 0s;
        }

        /* BOTONES PRINCIPALES (VERDE CON DEGRADADO) */
        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            border-radius: 12px !important;
            font-weight: 700 !important;
            background: linear-gradient(135deg, #10B981 0%, #059669 100%) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: none !important;
            padding: 0.75rem 1rem !important;
            box-shadow: 0 6px 18px rgba(16, 185, 129, 0.35) !important;
            transition: all 0.3s ease !important;
            
            -webkit-appearance: none !important;
            -moz-appearance: none !important;
            appearance: none !important;
            -webkit-tap-highlight-color: transparent !important;
        }

        /* HOVER / TOUCH EN BOTÓN CON TONO NARANJA DE ACCENTO DE VITA COACH */
        div.stButton > button:hover,
        div.stButton > button:focus,
        div.stButton > button:active,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:focus,
        div[data-testid="stFormSubmitButton"] > button:active {
            background: linear-gradient(135deg, #F39C12 0%, #E67E22 100%) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: none !important;
            box-shadow: 0 8px 22px rgba(243, 156, 18, 0.45) !important;
            outline: none !important;
            transform: translateY(-2px) !important;
        }

        div.stButton > button *,
        div[data-testid="stFormSubmitButton"] > button * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    try:
        with open("static/vitacoach.jpg", "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
        logo_html = f'<div class="logo-card-container"><div class="logo-card"><img src="data:image/jpeg;base64,{img_b64}" alt="VITA COACH"></div></div>'
    except Exception:
        logo_html = ""

    st.markdown(logo_html, unsafe_allow_html=True)

    tab_login, tab_registro, tab_recuperar = st.tabs(
        ["INICIAR SESIÓN", "REGISTRO", "RECUPERAR"]
    )

    # 1. FORMULARIO LOGIN
    with tab_login:
        with st.form("login_form"):
            email_input = st.text_input(
                "Correo electrónico",
                placeholder="ejemplo@correo.com",
                key="login_email",
            )
            password_input = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••",
                key="login_pass",
            )
            submit_login = st.form_submit_button(
                "INGRESAR", use_container_width=True
            )

            if submit_login:
                bloqueado, segs = esta_bloqueado("login")
                if bloqueado:
                    st.error(
                        f"Demasiados intentos fallidos. Reintenta en {segs}s."
                    )
                else:
                    usuario_valido = verificar_usuario(
                        email_input, password_input
                    )
                    if usuario_valido:
                        resetear_intentos("login")
                        st.session_state.user = usuario_valido
                        st.rerun()
                    else:
                        registrar_intento_fallido("login")
                        intentos_restantes = (
                            MAX_ATTEMPTS - st.session_state.get("login_attempts", 0)
                        )
                        if intentos_restantes > 0:
                            st.error(
                                "Credenciales incorrectas. Intentos restantes:"
                                f" {intentos_restantes}"
                            )
                        else:
                            st.error(
                                "Límite superado. Bloqueado por"
                                f" {LOCKOUT_DURATION}s."
                            )

    # 2. FORMULARIO REGISTRO
    with tab_registro:
        with st.form("registro_form"):
            nombre_nuevo = st.text_input(
                "Nombre completo", placeholder="Tu nombre"
            )
            email_nuevo = st.text_input(
                "Correo electrónico",
                placeholder="ejemplo@correo.com",
                key="reg_email",
            )
            password_nuevo = st.text_input(
                "Contraseña",
                type="password",
                placeholder="••••••••",
                key="reg_pass",
            )
            pin_nuevo = st.text_input(
                "PIN de seguridad (4 dígitos)",
                max_chars=4,
                type="password",
                placeholder="1234",
                key="reg_pin",
            )
            submit_registro = st.form_submit_button(
                "REGISTRARME", use_container_width=True
            )

            if submit_registro:
                bloqueado, segs = esta_bloqueado("registro")
                if bloqueado:
                    st.error(
                        f"Límite de solicitudes de registro. Reintenta en"
                        f" {segs}s."
                    )
                else:
                    if (
                        nombre_nuevo
                        and email_nuevo
                        and password_nuevo
                        and len(pin_nuevo) == 4
                    ):
                        exito, msg = registrar_nuevo_usuario(
                            nombre_nuevo, email_nuevo, password_nuevo, pin_nuevo
                        )
                        if exito:
                            resetear_intentos("registro")
                            st.success(
                                "¡Cuenta creada! Ahora puedes iniciar sesión."
                            )
                        else:
                            registrar_intento_fallido("registro")
                            st.error(f"Error al registrar: {msg}")
                    else:
                        registrar_intento_fallido("registro")
                        st.error(
                            "Por favor completa todos los campos correctamente."
                        )

    # 3. FORMULARIO RECUPERAR
    with tab_recuperar:
        with st.form("recuperar_form"):
            email_recuperar = st.text_input(
                "Correo electrónico",
                placeholder="ejemplo@correo.com",
                key="rec_email",
            )
            pin_recuperar = st.text_input(
                "PIN de seguridad",
                max_chars=4,
                type="password",
                placeholder="1234",
                key="rec_pin",
            )
            nueva_pw = st.text_input(
                "Nueva contraseña",
                type="password",
                placeholder="••••••••",
                key="rec_pw1",
            )
            confirmar_pw = st.text_input(
                "Confirmar contraseña",
                type="password",
                placeholder="••••••••",
                key="rec_pw2",
            )
            submit_recuperar = st.form_submit_button(
                "ACTUALIZAR CONTRASEÑA", use_container_width=True
            )

            if submit_recuperar:
                bloqueado, segs = esta_bloqueado("recuperar")
                if bloqueado:
                    st.error(
                        f"Bloqueo de seguridad activo. Reintenta en {segs}s."
                    )
                elif nueva_pw != confirmar_pw:
                    st.error("Las contraseñas no coinciden.")
                else:
                    exito, msg = cambiar_password_db(
                        email_recuperar, pin_recuperar, nueva_pw
                    )
                    if exito:
                        resetear_intentos("recuperar")
                        st.success(msg)
                    else:
                        registrar_intento_fallido("recuperar")
                        st.error(msg)

    # Detiene la ejecución para no cargar el dashboard/app si no hay usuario
    st.stop()

# --- A PARTIR DE AQUÍ SÍ HAY SESIÓN INICIADA ---
user_id = st.session_state.user["id"]
st.sidebar.markdown(f"👤 **Usuario:** {st.session_state.user['nombre']}")
if st.sidebar.button("🚪 Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

st.title("🥗 NutriTrack & Generador de Recetas")
st.write(
    f"Hola, {st.session_state.user['nombre']}. Lleva el control de tu progreso"
    " físico, planifica tu semana y transforma tus porciones en recetas reales."
)


# --- MENÚ PRINCIPAL DE NAVEGACIÓN ---
opcion = st.sidebar.radio(
    "Selecciona una sección:",
    [
        "🏠 Dashboard Principal",
        "📊 Control de Peso y Músculo",
        "📉 Registro Diario de Peso",
        "🥤 Generador de Licuados",
        "🥗 Registro de Alimentación",
        "🍳 Generador de Recetas",
        "🛒 Lista de Compras",
        "🔥 Seguimiento de Hábitos",
        "📈 Reporte Semanal",
        "🤖 Asistente Virtual Nutricional",
    ],
)

if "lista_compras" not in st.session_state:
    st.session_state.lista_compras = []

# ==========================================
# MÓDULO 0: DASHBOARD PRINCIPAL
# ==========================================
if opcion == "🏠 Dashboard Principal":
    st.header("🏠 Resumen Diario")
    st.write("Vista rápida de tus metas, consumo e indicadores del día.")

    # 1. Consulta de Control de Peso
    registros_db = run_query(
        """
        SELECT fecha, peso, objetivo, meta_principal, fecha_objetivo, diferencia, imc, diagnostico, grasa, musculo, meta_kcal 
        FROM control_peso WHERE user_id = %s ORDER BY fecha ASC
    """,
        (user_id,),
    )

    # 2. Consulta de Reloj Inteligente / Diario
    registro_reloj = run_query(
        """
        SELECT pasos, horas_sueno 
        FROM seguimiento_diario 
        WHERE user_id = %s 
        ORDER BY fecha DESC LIMIT 1
    """,
        (user_id,),
    )

    pasos_actuales = registro_reloj[0][0] if registro_reloj else 0
    sueno_actual = float(registro_reloj[0][1]) if registro_reloj else 0.0

    if registros_db:
        df_progreso = pd.DataFrame(
            registros_db,
            columns=[
                "Fecha",
                "Peso (kg)",
                "Objetivo (kg)",
                "Meta Principal",
                "Fecha Objetivo",
                "Diferencia (kg)",
                "IMC",
                "Diagnóstico",
                "Grasa (%)",
                "Músculo (%)",
                "Meta Kcal",
            ],
        )

        ultimo_registro = df_progreso.iloc[-1]
        primer_registro = df_progreso.iloc[0]

        peso_inicial = float(primer_registro["Peso (kg)"])
        peso_actual = float(ultimo_registro["Peso (kg)"])
        peso_meta = float(ultimo_registro["Objetivo (kg)"])
        meta_kcal = int(ultimo_registro["Meta Kcal"])

        kg_cambiados = abs(peso_inicial - peso_actual)
        kg_meta_total = abs(peso_inicial - peso_meta)
        pct_avance = (
            min(1.0, max(0.0, kg_cambiados / kg_meta_total))
            if kg_meta_total > 0
            else 1.0
        )

        st.markdown("### 📈 Progreso General")
        st.write(
            f"**Has avanzado {kg_cambiados:.1f} kg de {kg_meta_total:.1f} kg"
            " objetivo**"
        )
        st.progress(pct_avance)
        st.caption(
            f"🎯 Cumplido el **{int(pct_avance * 100)}%** de tu meta de peso."
        )

        st.markdown("---")
        st.markdown("### 🗓️ Estado de Hoy")

        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric("⚖️ Peso Actual", f"{peso_actual:.1f} kg")
        col_p2.metric("🎯 Peso Objetivo", f"{peso_meta:.1f} kg")
        col_p3.metric(
            "📉 Diferencia Restante", f"{abs(peso_actual - peso_meta):.1f} kg"
        )

        st.markdown("---")

        col_n1, col_n2, col_n3 = st.columns(3)
        col_n1.metric("🔥 Meta Calórica", f"{meta_kcal} kcal/día")
        col_n2.metric("🍽️ Calorías Restantes", f"{meta_kcal} kcal")
        col_n3.metric("🥗 Proteína Objetivo", "~120g - 150g")

        st.markdown("---")
        st.markdown("### ⌚ Indicadores de tu Reloj Inteligente")

        col_h1, col_h2, col_h3 = st.columns(3)
        agua_rec = (peso_actual * 35) / 1000
        
        col_h1.metric("💧 Meta de Agua", f"{agua_rec:.1f} L/día")
        
        # Métrica dinámica de pasos
        diff_pasos = pasos_actuales - 10000
        col_h2.metric(
            "🚶 Pasos del Día", 
            f"{pasos_actuales:,}", 
            delta=f"{diff_pasos:+,} vs meta" if pasos_actuales > 0 else None
        )
        
        # Métrica dinámica de sueño
        col_h3.metric(
            "😴 Sueño Reparador", 
            f"{sueno_actual} hrs", 
            delta="Óptimo (>=7h)" if sueno_actual >= 7.0 else "Revisar descanso" if sueno_actual > 0 else None,
            delta_color="normal" if sueno_actual >= 7.0 else "inverse"
        )

    else:
        st.info(
            "👋 ¡Bienvenido! Ingresa primero tus datos en la sección **📊 Control"
            " de Peso y Músculo** para activar tu Dashboard."
        )

# ==========================================
# MÓDULO 1: PERFIL INICIAL Y CONTROL DE PESO
# ==========================================
elif opcion == "📊 Control de Peso y Músculo":
    st.header("👤 Perfil Inicial, Diagnóstico y Objetivos")
    st.write(
        "Configura tus datos biométricos para obtener tu diagnóstico"
        " metabólico y dar seguimiento a tus metas."
    )

    col1, col2 = st.columns([1.2, 1.8])

    with col1:
        st.subheader("1. Perfil Inicial")
        fecha = st.date_input("Fecha de registro", key="fecha_reg")
        genero = st.selectbox("Sexo", ["Hombre", "Mujer"])
        edad = st.number_input("Edad", min_value=10, max_value=120, value=28)
        estatura_cm = st.number_input(
            "Estatura (cm)",
            min_value=100.0,
            max_value=250.0,
            value=170.0,
            step=1.0,
        )
        peso = st.number_input(
            "Peso actual (kg)",
            min_value=30.0,
            max_value=200.0,
            value=84.0,
            step=0.1,
        )
        peso_meta = st.number_input(
            "🎯 Peso objetivo (kg)",
            min_value=30.0,
            max_value=200.0,
            value=70.0,
            step=0.1,
        )

        actividad = st.selectbox(
            "Nivel de actividad:",
            [
                "Sedentario (Oficina / Trabajo de escritorio)",
                "Ligero (Oficina + Caminata diaria ligera)",
                "Mixto 50/50 (Oficina + Trabajo de campo / Mantenimiento)",
                "Activo (Trabajo físico pesado o ejercicio diario)",
                "Muy Activo (Trabajo pesado + Ejercicio intenso)",
            ],
            index=2,
        )

        objetivo = st.selectbox(
            "Objetivo principal:",
            [
                "Perder peso (Déficit calórico)",
                "Recomposición corporal (Perder grasa y ganar músculo)",
                "Mantener peso (Mantenimiento)",
                "Ganar masa muscular (Superávit ligero)",
            ],
        )

        usar_fecha_meta = st.checkbox("¿Agregar fecha objetivo?")
        fecha_meta = None
        if usar_fecha_meta:
            fecha_meta = st.date_input("Fecha objetivo", key="fecha_obj")

        estatura_m = estatura_cm / 100
        imc = peso / (estatura_m**2)
        if imc < 18.5:
            diagnostico_imc = "Bajo peso"
        elif 18.5 <= imc < 25.0:
            diagnostico_imc = "Peso normal"
        elif 25.0 <= imc < 30.0:
            diagnostico_imc = "Sobrepeso"
        elif 30.0 <= imc < 35.0:
            diagnostico_imc = "Obesidad Clase I"
        else:
            diagnostico_imc = "Obesidad Clase II/III"

        peso_saludable_aprox = 22.5 * (estatura_m**2)

        if genero == "Hombre":
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) + 5
        else:
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) - 161

        mult_act = {
            "Sedentario (Oficina / Trabajo de escritorio)": 1.2,
            "Ligero (Oficina + Caminata diaria ligera)": 1.375,
            "Mixto 50/50 (Oficina + Trabajo de campo / Mantenimiento)": 1.55,
            "Activo (Trabajo físico pesado o ejercicio diario)": 1.725,
            "Muy Activo (Trabajo pesado + Ejercicio intenso)": 1.9,
        }
        tdee = tmb * mult_act[actividad]

        if "Perder peso" in objetivo:
            meta_calorica = tdee * 0.80
        elif "Recomposición" in objetivo:
            meta_calorica = tdee * 0.90
        elif "Ganar masa" in objetivo:
