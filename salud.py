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

# --- CONTROL DE SESIÓN CON CENTRADO Y LOGO OPTIMIZADO ---
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    # --- CSS DE STREAMLIT ---
    st.markdown(
        """
        <style>
        #MainMenu, footer, header {visibility: hidden;}
        .stApp {
            background: radial-gradient(circle at 20% 20%, #064e3b 0%, #111827 50%),
                        radial-gradient(circle at 80% 80%, #022c22 0%, #000000 100%);
            background-attachment: fixed;
        }
        .main .block-container {
            max-width: 420px !important;
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            margin: 0 auto !important;
        }
        .logo-card-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 1.2rem;
        }
        .logo-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 12px;
            border-radius: 20px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.5);
            max-width: 150px;
            text-align: center;
        }
        .logo-card img {
            width: 100%;
            height: auto;
            display: block;
            border-radius: 12px;
        }

        /* --- STYLING DE PESTAÑAS (FORZADO BRUTO) --- */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background-color: rgba(0, 0, 0, 0.4) !important;
            padding: 6px;
            border-radius: 12px;
            margin-bottom: 1.2rem;
            border: 1px solid rgba(255, 255, 255, 0.1);
            width: 100%;
        }

        /* FUERZA ABSOLUTA DE COLOR BLANCO EN CUALQUIER ELEMENTO DENTRO DE LAS PESTAÑAS */
        .stTabs [data-baseweb="tab"],
        .stTabs [data-baseweb="tab"] *,
        .stTabs [data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 0.9 !important;
            font-weight: 600 !important;
        }

        /* PESTAÑA ACTIVA / SELECCIONADA */
        .stTabs [aria-selected="true"] {
            background-color: #059669 !important;
            border-radius: 8px !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
        }

        .stTabs [aria-selected="true"] *,
        .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            opacity: 1 !important;
            font-weight: 800 !important;
        }

        /* OCULTA LA LÍNEA ROJA DE SELECCIÓN POR DEFECTO DE STREAMLIT */
        .stTabs [data-baseweb="tab-highlight-title"],
        .stTabs [data-baseweb="tab-border"] {
            background-color: transparent !important;
            display: none !important;
        }

        /* --- FORMULARIO --- */
        [data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.04) !important;
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
            border-radius: 20px !important;
            padding: 1.5rem !important;
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        /* --- ETIQUETAS DE TEXTO SOBRE CAJAS --- */
        [data-testid="stWidgetLabel"] label, 
        .stTextInput label {
            color: #ffffff !important;
            font-weight: 600 !important;
        }

        /* --- CAJAS DE TEXTO (FONDO BLANCO Y TEXTO NEGRO) --- */
        .stTextInput input,
        div[data-baseweb="input"] input {
            background-color: #ffffff !important;
            color: #000000 !important;
            -webkit-text-fill-color: #000000 !important;
            border: 1px solid rgba(255, 255, 255, 0.3) !important;
            border-radius: 10px !important;
        }

        /* AUTOCOMPLETADO DEL NAVEGADOR EN CAJAS DE TEXTO */
        .stTextInput input:-webkit-autofill,
        .stTextInput input:-webkit-autofill:hover, 
        .stTextInput input:-webkit-autofill:focus {
            -webkit-text-fill-color: #000000 !important;
            -webkit-box-shadow: 0 0 0px 1000px #ffffff inset !important;
            transition: background-color 5000s ease-in-out 0s;
        }

        /* --- BOTONES (CORREGIDO PARA MÓVILES) --- */
        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            background: linear-gradient(135deg, #059669 0%, #10b981 100%) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: none !important;
            padding: 0.65rem 1rem !important;
            
            /* Anular comportamiento predeterminado de iOS Safari / Chrome Android */
            -webkit-appearance: none !important;
            -moz-appearance: none !important;
            appearance: none !important;
            -webkit-tap-highlight-color: transparent !important;
        }

        /* EVITAR QUE SE VUELVA BLANCO EN CELULARES AL TOCAR O ENFOCAR */
        div.stButton > button:hover,
        div.stButton > button:focus,
        div.stButton > button:active,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:focus,
        div[data-testid="stFormSubmitButton"] > button:active {
            background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: none !important;
            box-shadow: none !important;
            outline: none !important;
        }

        /* FORZAR TEXTO BLANCO EN CONTENEDORES INTERNOS DEL BOTÓN */
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
        with open("static/logo.jpg", "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
        logo_html = f'<div class="logo-card-container"><div class="logo-card"><img src="data:image/jpeg;base64,{img_b64}" alt="NutriTrack"></div></div>'
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
            meta_calorica = tdee * 1.15
        else:
            meta_calorica = tdee

        kilos_diferencia = peso - peso_meta
        val_genero = 1 if genero == "Hombre" else 0
        pct_grasa = max(
            5.0,
            min(
                (1.20 * imc)
                + (0.23 * edad)
                - (10.8 * val_genero)
                - 5.4,
                60.0,
            ),
        )
        pct_musculo = 100.0 - pct_grasa

        st.markdown("---")
        st.markdown("### 🧮 Métricas Calculadas Automáticamente:")

        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric(
                "1. IMC", f"{imc:.1f}", delta=diagnostico_imc, delta_color="off"
            )
            st.metric("3. Metabolismo Basal (TMB)", f"{int(tmb)} kcal/día")
            st.metric("5. Meta Calórica Orientativa", f"{int(meta_calorica)} kcal/día")
        with m_col2:
            st.metric("2. Peso Saludable Aprox.", f"~{peso_saludable_aprox:.1f} kg")
            st.metric("4. Gasto Diario (TDEE)", f"{int(tdee)} kcal/día")

        if st.button("💾 Guardar Perfil / Registro"):
            try:
                execute_db("""
                INSERT INTO control_peso (user_id, fecha, peso, objetivo, meta_principal, fecha_objetivo, diferencia, imc, diagnostico, grasa, musculo, meta_kcal)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    fecha,
                    peso,
                    peso_meta,
                    objetivo,
                    fecha_meta,  # psycopg2 gestionará None como NULL automáticamente
                    round(kilos_diferencia, 1),
                    round(imc, 1),
                    diagnostico_imc,
                    round(pct_grasa, 1),
                    round(pct_musculo, 1),
                    int(meta_calorica),
                    ),
                )
                st.success("¡Perfil y registro guardados en la base de datos!")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    with col2:
        st.subheader("2. Seguimiento y Progreso")
        registros_db = run_query(
            """
            SELECT fecha, peso, objetivo, meta_principal, diferencia, imc, diagnostico, grasa, musculo, meta_kcal 
            FROM control_peso WHERE user_id = %s ORDER BY fecha ASC
        """,
            (user_id,),
        )

        if registros_db:
            df_progreso = pd.DataFrame(
                registros_db,
                columns=[
                    "Fecha",
                    "Peso (kg)",
                    "Objetivo (kg)",
                    "Meta Principal",
                    "Diferencia (kg)",
                    "IMC",
                    "Diagnóstico",
                    "Grasa (%)",
                    "Músculo (%)",
                    "Meta Kcal",
                ],
            )

            peso_inicial = float(df_progreso.iloc[0]["Peso (kg)"])
            peso_actual = float(df_progreso.iloc[-1]["Peso (kg)"])
            peso_meta_val = float(df_progreso.iloc[-1]["Objetivo (kg)"])

            total_a_cambiar = abs(peso_inicial - peso_meta_val)
            cambio_actual = abs(peso_inicial - peso_actual)

            if total_a_cambiar > 0:
                porcentaje_avance = min(
                    1.0, max(0.0, cambio_actual / total_a_cambiar)
                )
                st.write(
                    f"**Avance hacia la meta:** {int(porcentaje_avance * 100)}%"
                )
                st.progress(porcentaje_avance)

            st.dataframe(df_progreso, use_container_width=True)

            fig = px.line(
                df_progreso,
                x="Fecha",
                y=["Peso (kg)", "Objetivo (kg)"],
                markers=True,
                title="Evolución del Peso vs. Peso Objetivo",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Aún no hay registros. Ingresa tus datos a la izquierda y"
                " guarda tu perfil."
            )
       
# ==========================================
# MÓDULO 2: REGISTRO DIARIO Y ANÁLISIS DE PESO
# ==========================================
elif opcion == "📉 Registro Diario de Peso":
    st.header("📉 Registro Diario y Análisis de Peso")
    st.write("Registra tu peso cada mañana y deja que la app interprete las tendencias por ti.")

    col_ingreso, col_analisis = st.columns([1, 2])

    with col_ingreso:
        st.subheader("📝 Registrar Datos del Día")
        f_reg = st.date_input("Fecha", key="f_diaria")
        p_reg = st.number_input("Peso (kg)", min_value=30.0, max_value=200.0, value=82.5, step=0.1)
        
        st.markdown("---")
        st.caption("⌚ Datos de tu Reloj Inteligente")
        pasos_reg = st.number_input("🚶 Pasos del día", min_value=0, max_value=100000, value=8000, step=500)
        sueno_reg = st.number_input("😴 Horas de sueño", min_value=0.0, max_value=24.0, value=7.5, step=0.5)
        kcal_reg = st.number_input("🔥 Kcal activas (Reloj)", min_value=0, max_value=10000, value=400, step=50)

        if st.button("📌 Guardar Registro Completo", use_container_width=True):
            try:
                execute_db(
                    """
                    INSERT INTO seguimiento_diario (user_id, fecha, peso, pasos, horas_sueno, calorias_activas)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (user_id, fecha) 
                    DO UPDATE SET 
                        peso = EXCLUDED.peso,
                        pasos = EXCLUDED.pasos,
                        horas_sueno = EXCLUDED.horas_sueno,
                        calorias_activas = EXCLUDED.calorias_activas;
                    """,
                    (user_id, f_reg, float(p_reg), int(pasos_reg), float(sueno_reg), int(kcal_reg))
                )
                st.success("¡Datos guardados correctamente en la base de datos!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    with col_analisis:
        st.subheader("📊 Análisis e Interpretación")

        if "historial_diario" in st.session_state and not st.session_state.historial_diario.empty:
            df = st.session_state.historial_diario.copy()
            df["Fecha"] = pd.to_datetime(df["Fecha"])
            df["Peso (kg)"] = pd.to_numeric(df["Peso (kg)"])
            
            # --- 1. MÉTRICAS BÁSICAS Y EXTREMOS ---
            p_actual = df.iloc[-1]["Peso (kg)"]
            p_min = df["Peso (kg)"].min()
            p_max = df["Peso (kg)"].max()

            # Promedio últimos 7 días
            ultimos_7 = df.tail(7)
            prom_semanal = ultimos_7["Peso (kg)"].mean()

            # --- 2. COMPARATIVA SEMANAL & CONCLUSIÓN EN TEXTO ---
            if len(df) >= 7:
                previo_7 = df.iloc[-14:-7] if len(df) >= 14 else df.iloc[:-7]
                prom_anterior = previo_7["Peso (kg)"].mean()
                diff_semanal = prom_semanal - prom_anterior

                if diff_semanal < 0:
                    mensaje_conclusion = f"🎉 **Esta semana bajaste {abs(diff_semanal):.2f} kg** en comparación con la semana anterior."
                    color_callout = "success"
                elif diff_semanal > 0:
                    mensaje_conclusion = f"⚠️ **Esta semana subiste {diff_semanal:.2f} kg** en comparación con la semana anterior."
                    color_callout = "warning"
                else:
                    mensaje_conclusion = "⚖️ **Tu peso se mantuvo exactamente igual** que la semana anterior."
                    color_callout = "info"
            else:
                mensaje_conclusion = f"💡 **Registra al menos 7 días** para calcular la diferencia semanal real. Tu promedio actual es de **{prom_semanal:.2f} kg**."
                color_callout = "info"

            # --- 3. MOSTRAR TARJETA DE CONCLUSIÓN DIRECTA ---
            if color_callout == "success":
                st.success(mensaje_conclusion)
            elif color_callout == "warning":
                st.warning(mensaje_conclusion)
            else:
                st.info(mensaje_conclusion)

            # --- 4. MÉTRICAS CLAVE EN PANTALLA ---
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("⚖️ Peso Diario", f"{p_actual:.1f} kg")
            c2.metric("📅 Promedio Semanal", f"{prom_semanal:.2f} kg")
            c3.metric("📉 Mínimo Histórico", f"{p_min:.1f} kg")
            c4.metric("📈 Máximo Histórico", f"{p_max:.1f} kg")

            # --- 5. GRÁFICA DE EVOLUCIÓN CON TENDENCIA MENSUAL ---
            st.markdown("---")
            st.markdown("##### 📈 Evolución y Tendencia")

            # Asegurar cálculo numérico limpio para el promedio móvil
            df["Promedio Móvil"] = df["Peso (kg)"].rolling(window=7, min_periods=1).mean().astype(float)

            fig = px.line(
                df,
                x="Fecha",
                y=["Peso (kg)", "Promedio Móvil"],
                markers=True,
                labels={"value": "Peso (kg)", "variable": "Indicador"},
                title="Peso Diario vs. Tendencia Real (Promedio Móvil)",
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tabla interactiva
            with st.expander("📋 Ver Historial de Datos"):
                st.dataframe(df.sort_values("Fecha", ascending=False), use_container_width=True)
        else:
            st.info("Aún no hay registros diarios. Utiliza el formulario de la izquierda para comenzar.")

# ==========================================
# MÓDULO 3: LICUADOS
# ==========================================
elif opcion == "🥤 Generador de Licuados":
    st.header("🥤 Planificador de Licuados")
    frutas_disponibles = st.text_input(
        "🍎 Frutas disponibles en casa esta semana:",
        "Manzana, papaya, fresas congeladas, peras, plátano",
    )
    if st.button("🥤 Generar Plan de Licuados"):
        try:
            prompt = f"Crea un plan de licuados usando estas frutas: {frutas_disponibles}."
            response = client.models.generate_content(
                model="gemini-3.7-flash", contents=prompt
            )

            st.session_state["plan_licuados_texto"] = response.text
        except Exception as e:
            st.error(f"Error: {e}")

    if "plan_licuados_texto" in st.session_state:
        st.markdown(st.session_state["plan_licuados_texto"])

# ==========================================
# MÓDULO 4: REGISTRO DE ALIMENTACIÓN DUAL
# ==========================================
elif opcion == "🥗 Registro de Alimentación":
    st.header("🥗 Registro de Alimentación")
    st.write("Elige tu método de registro preferido para el día de hoy.")

    # Creación de Pestañas
    tab_porciones, tab_frecuentes = st.tabs([
        "📋 Porciones (Plan Nutrióloga)", 
        "⚡ Calorías y Comidas Frecuentes"
    ])

    # ----------------------------------------------------
    # PESTAÑA 1: PLAN DE PORCIONES DE LA NUTRIÓLOGA
    # ----------------------------------------------------
    with tab_porciones:
        st.subheader("📋 Control por Equivalentes / Porciones")
        st.caption("Marca las porciones que vas consumiendo a lo largo del día según tu plan nutricional.")

        if "meta_porciones" not in st.session_state:
            st.session_state.meta_porciones = {
                "🥩 Proteína / Origen Animal": 5,
                "🍞 Cereales / Carbohidratos": 4,
                "🥦 Verduras": 4,
                "🍎 Frutas": 2,
                "🥑 Grasas Saludables": 3,
                "🥛 Lácteos": 1,
            }

        if "porciones_hoy" not in st.session_state:
            st.session_state.porciones_hoy = {k: 0 for k in st.session_state.meta_porciones.keys()}

        # Ajuste de metas de la nutrióloga
        with st.expander("⚙️ Configurar Metas Diarias de la Nutrióloga"):
            c_cfg = st.columns(2)
            for idx, (grupo, meta_val) in enumerate(st.session_state.meta_porciones.items()):
                col_target = c_cfg[idx % 2]
                st.session_state.meta_porciones[grupo] = col_target.number_input(
                    f"Meta - {grupo}", min_value=0, value=meta_val, key=f"cfg_{grupo}"
                )

        st.markdown("---")

        # Botones de registro rápido
        col_reg1, col_reg2 = st.columns(2)
        for idx, (grupo, meta_val) in enumerate(st.session_state.meta_porciones.items()):
            col_actual = col_reg1 if idx % 2 == 0 else col_reg2
            with col_actual:
                consumido = st.session_state.porciones_hoy[grupo]
                restante = meta_val - consumido
                
                st.markdown(f"**{grupo}**")
                c_b1, c_b2, c_info = st.columns([1, 1, 2])
                
                if c_b1.button("➕ 1", key=f"add_{grupo}"):
                    st.session_state.porciones_hoy[grupo] += 1
                    st.rerun()
                if c_b2.button("➖ 1", key=f"sub_{grupo}"):
                    if st.session_state.porciones_hoy[grupo] > 0:
                        st.session_state.porciones_hoy[grupo] -= 1
                        st.rerun()
                
                c_info.caption(f"Consumido: **{consumido}/{meta_val}** | Quedan: **{max(0, restante)}**")

        st.markdown("---")
        st.markdown("##### 📊 Avance de Porciones Hoy")
        for grupo, meta_val in st.session_state.meta_porciones.items():
            consumido = st.session_state.porciones_hoy[grupo]
            pct = min(1.0, consumido / meta_val) if meta_val > 0 else 0
            st.write(f"**{grupo}:** {consumido} / {meta_val}")
            st.progress(pct)

        if st.button("🔄 Reiniciar Porciones para Mañana"):
            st.session_state.porciones_hoy = {k: 0 for k in st.session_state.meta_porciones.keys()}
            st.rerun()

    # ----------------------------------------------------
    # PESTAÑA 2: REGISTRO POR CALORÍAS Y REPETIR COMIDAS (CON IA)
    # ----------------------------------------------------
    with tab_frecuentes:
        st.subheader("⚡ Registro Inteligente por Calorías")
        st.caption("Escribe lo que comiste en lenguaje natural y deja que la IA calcule las calorías y proteínas por ti.")

        if "comidas_frecuentes" not in st.session_state:
            st.session_state.comidas_frecuentes = [
                {"Nombre": "Licuado de plátano + avena", "Tipo": "Desayuno", "Kcal": 450, "Prot": 22},
                {"Nombre": "Pechuga + Arroz + Verduras", "Tipo": "Comida", "Kcal": 550, "Prot": 45},
            ]

        if "diario_alimentos" not in st.session_state:
            st.session_state.diario_alimentos = pd.DataFrame(
                columns=["Comida", "Alimento", "Kcal", "Proteína (g)"]
            )

        # Botones de Carga Rápida
        st.markdown("##### 🔁 Repetir Comida Habitual")
        cols_frec = st.columns(len(st.session_state.comidas_frecuentes))
        for idx, item in enumerate(st.session_state.comidas_frecuentes):
            with cols_frec[idx]:
                proteina_val = item.get("Prot", item.get("Proteína (g)", 0))
                
                st.markdown(f"**{item['Tipo']}:** {item['Nombre']}")
                st.caption(f"🔥 {item['Kcal']} kcal | 🥗 {proteina_val}g Prot")
                if st.button("🔁 Repetir", key=f"frec_tab_{idx}", use_container_width=True):
                    nuevo = pd.DataFrame([{
                        "Comida": item['Tipo'],
                        "Alimento": item['Nombre'],
                        "Kcal": item['Kcal'],
                        "Proteína (g)": proteina_val,
                    }])
                    st.session_state.diario_alimentos = pd.concat(
                        [st.session_state.diario_alimentos, nuevo], ignore_index=True
                    )
                    st.success(f"¡{item['Nombre']} agregado!")
                    st.rerun()

        st.markdown("---")

        # Registro Asistido por IA
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            st.markdown("##### 🪄 Registro Asistido con IA")
            cat = st.selectbox("Categoría", ["Desayuno", "Comida", "Cena", "Snack"], key="cat_ia")
            
            # Campo descriptivo libre
            desc_comida = st.text_area(
                "¿Qué comiste?", 
                placeholder="Ej. Sándwich de jamón con lechuga, jitomate, panela y mayonesa.",
                key="desc_ia"
            )

            if st.button("✨ Calcular con IA y Registrar", use_container_width=True):
                if desc_comida.strip() != "":
                    with st.spinner("Calculando nutrimentos con Gemini..."):
                        try:
                            prompt_calorias = f"""
                            Actúa como un nutriólogo experto. Analiza el siguiente alimento/platillo descrito por el usuario y estima sus calorías y proteína total de forma realista.
                            Alimento: "{desc_comida}"

                            Responde ÚNICAMENTE en el siguiente formato estricto de texto plano, sin explicaciones adicionales:
                            KCALS: [número entero de calorías aproximadas]
                            PROTEINA: [número entero de gramos de proteína aproximados]
                            """
                            
                            response = client.models.generate_content(
                                model="gemini-3.6-flash", contents=prompt_calorias
                            )
                            texto_respuesta = response.text.strip()
                            
                            # Parsear la respuesta de la IA de forma segura
                            kcal_calc = 350  # Valor por defecto si falla el parseo
                            prot_calc = 20
                            
                            for linea in texto_respuesta.split('\n'):
                                if "KCALS:" in linea:
                                    digits = "".join(c for c in linea if c.isdigit())
                                    kcal_calc = int(digits) if digits else 350
                                if "PROTEINA:" in linea:
                                    digits = "".join(c for c in linea if c.isdigit())
                                    prot_calc = int(digits) if digits else 20
                            
                            # Guardar directamente en el diario
                            nuevo_m = pd.DataFrame([{
                                "Comida": cat, 
                                "Alimento": desc_comida, 
                                "Kcal": kcal_calc, 
                                "Proteína (g)": prot_calc
                            }])
                            st.session_state.diario_alimentos = pd.concat(
                                [st.session_state.diario_alimentos, nuevo_m], ignore_index=True
                            )
                            st.success(f"¡Registrado! Estimado: 🔥 {kcal_calc} kcal | 🥗 {prot_calc}g prot")
                            st.rerun()

                        except Exception as e:
                            st.error(f"No se pudo calcular automáticamente: {e}")
                else:
                    st.warning("Por favor escribe qué fue lo que comiste.")

            # Opción por si prefieren meterlo a mano de forma tradicional
            with st.expander("📝 O ingresar manualmente (Sin IA)"):
                nom_m = st.text_input("Nombre corto", placeholder="Ej. Pollo con arroz")
                kc_m = st.number_input("Calorías (kcal)", min_value=0, value=350, key="kc_manual")
                pr_m = st.number_input("Proteína (g)", min_value=0, value=25, key="pr_manual")
                if st.button("📌 Guardar Manual", use_container_width=True):
                    if nom_m.strip() != "":
                        nuevo_man = pd.DataFrame([{"Comida": cat, "Alimento": nom_m, "Kcal": kc_m, "Proteína (g)": pr_m}])
                        st.session_state.diario_alimentos = pd.concat(
                            [st.session_state.diario_alimentos, nuevo_man], ignore_index=True
                        )
                        st.success("¡Guardado manualmente!")
                        st.rerun()

        with col_f2:
            st.markdown("##### 📊 Consumo de Hoy")
            tot_k = st.session_state.diario_alimentos["Kcal"].sum() if not st.session_state.diario_alimentos.empty else 0
            tot_p = st.session_state.diario_alimentos["Proteína (g)"].sum() if not st.session_state.diario_alimentos.empty else 0

            m_k, m_p = st.columns(2)
            m_k.metric("🔥 Total Calorías", f"{tot_k} kcal")
            m_p.metric("🥗 Total Proteína", f"{tot_p} g")

            if not st.session_state.diario_alimentos.empty:
                st.dataframe(st.session_state.diario_alimentos, use_container_width=True)
                if st.button("🗑️ Vaciar Diario"):
                    st.session_state.diario_alimentos = pd.DataFrame(
                        columns=["Comida", "Alimento", "Kcal", "Proteína (g)"]
                    )
                    st.rerun()

# ==========================================
# MÓDULO 5: GENERADOR DE RECETAS Y GUÍA DE ALIMENTACIÓN
# ==========================================
elif opcion == "🍳 Generador de Recetas":
    st.header("🍳 Generador de Recetas y Plan según Jornada")
    st.write(
        "Configura tus horarios de trabajo para adaptar tus comidas y porciones a tus turnos reales."
    )

# 1. CONFIGURACIÓN DE JORNADA LABORAL
    with st.expander("⏰ Configurar mi Jornada Laboral y Rutina", expanded=True):
        col_h1, col_h2, col_h3 = st.columns(3)
        with col_h1:
            hora_inicio = st.time_input("Hora de entrada:", value=datetime.time(7, 0))
        with col_h2:
            hora_salida = st.time_input("Hora de salida:", value=datetime.time(19, 0))
        with col_h3:
            hora_comida = st.time_input("Hora de comida:", value=datetime.time(12, 0))

        col_h4, col_h5, col_h6, col_h7 = st.columns(4)
        with col_h4:
            hora_licuado = st.time_input("Licuado / Al despertar:", value=datetime.time(5, 10))
        with col_h5:
            hora_desayuno = st.time_input("Desayuno:", value=datetime.time(7, 30))
        with col_h6:
            hora_col2 = st.time_input(
                "Colación Tarde (Media Tarde):", value=datetime.time(16, 30)
            )
        with col_h7:
            hora_cena = st.time_input("Cena:", value=datetime.time(20, 0))

        opcion_comedor = st.checkbox(
            "Tengo opción de Comedor de Empresa (Paquete Saludable / Ensaladas)",
            value=True,
        )

    # 2. PLAN BASE RESTRUCTURADO (Ajuste de puentes de saciedad)
    if "plan_nutriologa_horarios" not in st.session_state:
        st.session_state.plan_nutriologa_horarios = {
            "Al despertar": {"Lácteos": 1, "Grasas c/ Prot": 1},
            "Desayuno": {
                "Verduras": 1,
                "Frutas": 1,
                "Cereales": 2,
                "AOA (Proteína)": 2.5,
                "Grasas s/ Prot": 1,
            },
            "Colación 1": {
                "Frutas": 1
            },  
            "Comida": {
                "Verduras": 1,
                "Cereales": 3,
                "AOA (Proteína)": 4,
                "Grasas s/ Prot": 2,
            },  
            "Colación 2": {
                "Frutas": 1,
                "Grasas c/ Prot": 1,
                "AOA (Proteína)": 1,
            },  
            "Cena": {
                "Verduras": 1,
                "Cereales": 3,
                "AOA (Proteína)": 2.5,
                "Grasas s/ Prot": 1,
            },
        }

    plan_actual = st.session_state.plan_nutriologa_horarios

    # 3. SELECCIÓN DE MODALIDAD Y OPCIÓN DE COMEDOR
    st.markdown("---")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        opciones_tiempo = ["📌 Menú Completo del Día"] + list(
            plan_actual.keys()
        )
        tiempo_comida = st.selectbox(
            "Selecciona el tiempo de comida:", opciones_tiempo
        )
    with col_t2:
        modalidades = [
            "🏢 Oficina / Campo (Trabajo Mixto - Práctico para llevar)",
            "🏠 En Casa / Home Office (Cocinando al momento)",
            "🛠️ Campo Total / Trabajo Móvil (Sin microondas / En hielera)",
            "🏬 Comedor de Empresa (Selección inteligente de menú)",
        ]
        idx_def = 3 if opcion_comedor else 0
        modalidad_trabajo = st.selectbox(
            "Entorno y Modalidad de tu día:", modalidades, index=idx_def
        )

    if "Comedor" in modalidad_trabajo:
        opcion_comedor_elegida = st.radio(
            "🍽️ Opciones disponibles en comedor:",
            [
                "🥗 Paquete Saludable / Ensaladas",
                "🍲 Comida del Día / Paquete General",
            ],
            horizontal=True,
        )
    else:
        opcion_comedor_elegida = "N/A"

    # 4. GUSTOS Y RESTRICCIONES POR CATEGORÍA
    st.markdown("---")
    st.subheader("⚙️ Gustos y Restricciones por Categoría")

    tab_prot, tab_veg, tab_frutas = st.tabs(
        [
            "🥩 Proteínas y Carnes",
            "🥦 Verduras y Acompañamientos",
            "🍎 Frutas",
        ]
    )

    with tab_prot:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fav_prot = st.text_input(
                "💚 Proteínas preferidas:",
                "Pollo, queso panela, atún, huevo",
                key="fav_p",
            )
        with col_p2:
            no_prot = st.text_input(
                "❌ Proteínas a evitar:", "Pescado, cerdo, mariscos", key="no_p"
            )

    with tab_veg:
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            fav_veg = st.text_input(
                "💚 Verduras / Cereales preferidos:",
                "Jitomate, aguacate, tortillas, avena",
                key="fav_v",
            )
        with col_v2:
            no_veg = st.text_input(
                "❌ Verduras / Cereales a evitar:",
                "Cilantro, calabacita, mayonesa",
                key="no_v",
            )

    with tab_frutas:
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            fav_frutas = st.text_input(
                "💚 Frutas preferidas:", "Plátano, manzana, fresas", key="fav_f"
            )
        with col_f2:
            no_frutas = st.text_input(
                "❌ Frutas a evitar:", "Papaya, melón", key="no_f"
            )

    alimentos_favoritos = f"Proteínas: {fav_prot} | Verduras/Cereales: {fav_veg} | Frutas: {fav_frutas}"
    alimentos_no_gustan = f"Proteínas: {no_prot} | Verduras/Cereales: {no_veg} | Frutas: {no_frutas}"

    # 5. GENERACIÓN CON GEMINI
    if st.button("🍳 Generar Plan / Guía de Alimentación", use_container_width=True):
        try:
            duracion_jornada = (
                hora_salida.hour + hora_salida.minute / 60
            ) - (hora_inicio.hour + hora_inicio.minute / 60)
            if duracion_jornada < 0:
                duracion_jornada += 24

            contexto_rutina = f"""
            - Horario laboral: {hora_inicio.strftime('%I:%M %p')} a {hora_salida.strftime('%I:%M %p')} ({duracion_jornada:.1f} hrs)
            - Al despertar: {hora_licuado.strftime('%I:%M %p')}
            - Desayuno: {hora_desayuno.strftime('%I:%M %p')}
            - Comida principal: {hora_comida.strftime('%I:%M %p')} (Comedor: {opcion_comedor_elegida})
            - Colación 2 (Tarde): {hora_col2.strftime('%I:%M %p')}
            - Cena: {hora_cena.strftime('%I:%M %p')}
            """

            reglas_prompt = """
            REGLAS DE PREPARACIÓN Y SACIEDAD CRÍTICAS:
            1. CONTROL DEL ANTOJO DE TARDE (5:00 PM):
               El usuario suele experimentar picos de hambre por la tarde y recurrir a ultraprocesados por falta de saciedad y practicidad.
               La Colación 2 (4:30 PM) DEBE ser highly portable (fácil de comer en oficina o trayecto) y combinar carbohidratos de lenta absorción, 
               grasa saludable y proteína. Debe estar diseñada explícitamente para erradicar el deseo de comer pan dulce o galletas.

            2. GRASAS SALUDABLES: Usar únicamente Aceite de Oliva Extra Virgen, Aceite de Aguacate o Spray. Prohibidos aceites refinados.
            3. COCINADO: Priorizar métodos como plancha, vapor, horno o air fryer. Evitar aderezos comerciales.
            """

            if tiempo_comida == "📌 Menú Completo del Día":
                resumen_plan = ""
                for t_nombre, t_datos in plan_actual.items():
                    porciones_t = ", ".join(
                        [f"{cant} {grp}" for grp, cant in t_datos.items()]
                    )
                    resumen_plan += f"- **{t_nombre}**: {porciones_t}\n"

                prompt = f"""
                Actúa como Nutriólogo Experto. Diseña un cronograma de alimentación optimizado para la jornada:

                RUTINA DE HORARIOS:
                {contexto_rutina}
                Modalidad: '{modalidad_trabajo}'

                PORCIONES DE LA NUTRIÓLOGA:
                {resumen_plan}

                PREFERENCIAS:
                - Le gustan: {alimentos_favoritos}
                - EXCLUIR (No incluir bajo ningún concepto): {alimentos_no_gustan}

                {reglas_prompt}

                INSTRUCCIONES:
                1. Presenta un cronograma por horas de cada tiempo de comida.
                2. Para la Colación de las {hora_col2.strftime('%I:%M %p')}, redacta una opción saciante y portable.
                3. Da explicaciones claras para ajustar la comida de comedor ('{opcion_comedor_elegida}') controlando las porciones indicadas.
                """
            else:
                datos_comida = plan_actual[tiempo_comida].copy()
                porciones_str = ", ".join(
                    [
                        f"{cant} porción(es) de {grupo}"
                        for grupo, cant in datos_comida.items()
                    ]
                )

                prompt = f"""
                Actúa como Nutriólogo Asesor. Diseña la receta/guía para '{tiempo_comida}'.

                RUTINA: {contexto_rutina}
                MODALIDAD: '{modalidad_trabajo}' (Comedor: {opcion_comedor_elegida})
                PORCIONES: {porciones_str}
                GUSTOS: {alimentos_favoritos}
                EXCLUIR: {alimentos_no_gustan}

                {reglas_prompt}

                Si es la Colación 2, enfatiza que la preparación debe ser sustanciosa y rica en proteína/grasa saludable para aguantar la tarde.
                """

            with st.spinner("Optimizando plan con Gemini..."):
                response = client.models.generate_content(
                    model="gemini-3.6-flash", contents=prompt
                )
                receta_texto = response.text

            st.session_state["ultima_receta"] = receta_texto

        except Exception as e:
            st.error(f"Error al conectar con Gemini: {e}")

    if "ultima_receta" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["ultima_receta"])
        
        # Botón para guardar en la base de datos de Neon que ya tienes configurada
        if st.button("💾 Guardar esta receta en mi cuenta"):
            guardar_receta_db("General", tiempo_comida, st.session_state["ultima_receta"])

# ==========================================
# MÓDULO 6: LISTA DE COMPRAS
# ==========================================
elif opcion == "🛒 Lista de Compras":
    st.header("🛒 Tu Lista de Supermercado")

    nuevo_item = st.text_input("Agregar ingrediente o elemento al super:")
    if st.button("Añadir a la lista"):
        if nuevo_item:
            st.session_state.lista_compras.append(nuevo_item)
            st.success(f"'{nuevo_item}' agregado.")

    st.subheader("Lista pendiente:")
    if st.session_state.lista_compras:
        for idx, item in enumerate(st.session_state.lista_compras, 1):
            st.write(f"{idx}. {item}")

        if st.button("🗑️ Limpiar lista"):
            st.session_state.lista_compras = []
            st.rerun()
    else:
        st.info("Tu lista de compras está vacía.")

# ==========================================
# MÓDULO 7: HÁBITOS Y CUMPLIMIENTO DIARIO
# ==========================================
elif opcion == "🔥 Seguimiento de Hábitos":
    st.header("🔥 Registro de Hábitos Diarios")
    st.write("Marca tus hábitos cumplidos hoy para mantener y aumentar tu racha.")

    # Inicializar registro de hábitos en st.session_state
    if "historial_habitos" not in st.session_state:
        st.session_state.historial_habitos = pd.DataFrame(
            columns=[
                "Fecha",
                "Agua",
                "Objetivo_Nutricional",
                "Actividad_Fisica",
                "Sueno",
                "Frutas_Verduras",
                "Sin_Azucar",
                "Cumplido_Total",
            ]
        )

    # 1. FECHA Y FORMULARIO DE CHECKLIST DIARIO
    col_check, col_racha = st.columns([1.2, 1.8])

    with col_check:
        st.subheader("📅 Checklist de Hoy")
        f_habito = st.date_input("Fecha", key="f_habito_input")

        # Lista de hábitos con checkboxes
        h_agua = st.checkbox("💧 Tomé suficiente agua")
        h_nutricion = st.checkbox("🥗 Comí de acuerdo con mi objetivo")
        h_actividad = st.checkbox("🚶 Hice actividad física")
        h_sueno = st.checkbox("😴 Dormí bien")
        h_frutas = st.checkbox("🍎 Comí frutas / verduras")
        h_azucar = st.checkbox("🚫 Evité bebidas azucaradas")

        total_habitos = 6
        completados = sum([h_agua, h_nutricion, h_actividad, h_sueno, h_frutas, h_azucar])

        if st.button("💾 Guardar Hábitos de Hoy", use_container_width=True):
            # Se considera "Día Cumplido" si realiza al menos 4 de los 6 hábitos
            cumplio_dia = completados >= 4

            nuevo_registro_h = pd.DataFrame(
                [{
                    "Fecha": pd.to_datetime(f_habito),
                    "Agua": h_agua,
                    "Objetivo_Nutricional": h_nutricion,
                    "Actividad_Fisica": h_actividad,
                    "Sueno": h_sueno,
                    "Frutas_Verduras": h_frutas,
                    "Sin_Azucar": h_azucar,
                    "Cumplido_Total": cumplio_dia,
                }]
            )

            # Evitar duplicados del mismo día guardando el último registro
            st.session_state.historial_habitos = (
                pd.concat([st.session_state.historial_habitos, nuevo_registro_h])
                .drop_duplicates(subset=["Fecha"], keep="last")
                .sort_values("Fecha")
                .reset_index(drop=True)
            )
            st.success("¡Hábitos de hoy guardados!")
            st.rerun()

    # 2. CÁLCULO DE RACHA ACTUAL Y ESTADÍSTICAS
    with col_racha:
        st.subheader("🔥 Tu Racha Actual")

        df_h = st.session_state.historial_habitos.copy()

        if not df_h.empty:
            df_h["Fecha"] = pd.to_datetime(df_h["Fecha"])
            df_h = df_h.sort_values("Fecha", ascending=False)

            # Algoritmo para calcular la racha de días consecutivos cumplidos
            racha_actual = 0
            for idx, fila in df_h.iterrows():
                if fila["Cumplido_Total"]:
                    racha_actual += 1
                else:
                    break

            # Despliegue visual destacado de la racha
            if racha_actual > 0:
                st.markdown(
                    f"""
                    <div style="background-color: #1E293B; padding: 20px; border-radius: 12px; text-align: center; border: 2px solid #F59E0B;">
                        <h1 style="color: #F59E0B; margin: 0; font-size: 3em;">🔥 {racha_actual} DÍAS</h1>
                        <p style="color: #E2E8F0; margin: 5px 0 0 0; font-size: 1.2em;">¡Excelente constancia! Sigue así.</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.info("🔥 **Racha actual: 0 días.** ¡Completa al menos 4 hábitos hoy para comenzar tu racha!")

            st.markdown("---")

            # Métrica de porcentaje de efectividad mensual
            dias_totales = len(df_h)
            dias_exitosos = df_h["Cumplido_Total"].sum()
            pct_efectividad = (dias_exitosos / dias_totales) * 100 if dias_totales > 0 else 0

            m_h1, m_h2 = st.columns(2)
            m_h1.metric("📊 Días Registrados", f"{dias_totales} días")
            m_h2.metric("🎯 Efectividad Total", f"{pct_efectividad:.0f}%")

            # Mostrar tabla detallada del historial
            with st.expander("📋 Ver Historial Completo de Hábitos"):
                st.dataframe(df_h, use_container_width=True)
        else:
            st.info("Aún no has registrado hábitos. Marca tus casillas a la izquierda y guarda tu día.")

# ==========================================
# MÓDULO 8: REPORTES SEMANALES
# ==========================================
elif opcion == "📈 Reporte Semanal":
    st.header("📈 Reporte Semanal de Progreso")
    st.write("Consulta el balance consolidado de tu última semana y la interpretación de tu evolución.")

    # 1. EVALUAR SI HAY DATOS EN EL HISTORIAL DIARIO
    if "historial_diario" in st.session_state and not st.session_state.historial_diario.empty:
        df_p = st.session_state.historial_diario.copy()
        df_p["Fecha"] = pd.to_datetime(df_p["Fecha"])
        df_p = df_p.sort_values("Fecha")

        # Tomar datos de los últimos 7 días registrados (o los disponibles)
        ultimos_7 = df_p.tail(7)
        
        peso_ini = ultimos_7.iloc[0]["Peso (kg)"]
        peso_fin = ultimos_7.iloc[-1]["Peso (kg)"]
        cambio_peso = peso_fin - peso_ini

        # Obtener o simular promedios de hábitos / nutrición de la semana
        prom_kcal = 1940
        if "diario_alimentos" in st.session_state and not st.session_state.diario_alimentos.empty:
            tot_k = st.session_state.diario_alimentos["Kcal"].sum()
            if tot_k > 0:
                prom_kcal = int(tot_k)

        prom_pasos = "7,820"
        prom_agua = "2.1 L"

        # --- SECCIÓN: TARJETA RESUMEN "TU SEMANA" ---
        st.subheader("🗓️ Tu Semana")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("⚖️ Peso Inicial", f"{peso_ini:.1f} kg")
        c2.metric("⚖️ Peso Final", f"{peso_fin:.1f} kg")
        
        # Color del delta según si subió o bajó
        delta_str = f"{cambio_peso:+.1f} kg"
        c3.metric("📉 Cambio de Peso", f"{peso_fin:.1f} kg", delta=delta_str, delta_color="inverse")

        st.markdown("---")

        c4, c5, c6 = st.columns(3)
        c4.metric("🔥 Promedio de Calorías", f"{prom_kcal} kcal")
        c5.metric("🚶 Promedio de Pasos", f"{prom_pasos} pasos")
        c6.metric("💧 Agua Promedio", f"{prom_agua}")

        st.markdown("---")

        # --- SECCIÓN: CONCLUSIÓN DE LA APP ---
        st.subheader("💡 Conclusión Semanal")

        if cambio_peso < 0:
            conclusion_txt = (
                f"🎉 **Tu progreso va en buena dirección.** Esta semana bajaste **{abs(cambio_peso):.1f} kg** "
                f"y mantuviste una excelente constancia en tu actividad física y nutrición."
            )
            st.success(conclusion_txt)
        elif cambio_peso > 0:
            conclusion_txt = (
                f"⚠️ **Esta semana subiste {cambio_peso:.1f} kg.** Revisa tus porciones de alimentos y "
                f"asegúrate de mantener la hidratación y el nivel de actividad objetivo."
            )
            st.warning(conclusion_txt)
        else:
            conclusion_txt = (
                "⚖️ **Tu peso se mantuvo estable esta semana.** Si tu objetivo es perder peso, "
                "evalúa hacer un ajuste ligero en tus porciones o aumentar tu conteo diario de pasos."
            )
            st.info(conclusion_txt)

        # Resumen gráfico semanal
        st.markdown("##### 📊 Tendencia de los Últimos 7 Días")
        fig_semana = px.line(
            ultimos_7,
            x="Fecha",
            y="Peso (kg)",
            markers=True,
            title="Evolución de Peso de la Semana",
        )
        st.plotly_chart(fig_semana, use_container_width=True)

    else:
        st.info("👋 Para generar tu primer reporte semanal, ingresa al menos un par de registros en el apartado **📉 Registro Diario de Peso**.")

# ==========================================
# MÓDULO 9: ASISTENTE VIRTUAL NUTRICIONAL (IA)
# ==========================================
elif opcion == "🤖 Asistente Virtual Nutricional":
    st.header("🤖 Coach Personal de Nutrición")
    st.write("Escribe o dicta lo que comiste en lenguaje natural y la IA calculará tus macros y te dará feedback en tiempo real.")

    # Inicializar historial de conversación del asistente
    if "chat_asistente" not in st.session_state:
        st.session_state.chat_asistente = []

    # Mostrar mensajes previos del chat
    for mensaje in st.session_state.chat_asistente:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    # Entrada de texto del usuario
    if prompt := st.chat_input("Ejemplo: Hoy desayuné 2 huevos, 2 tortillas y un café con leche..."):
        # Guardar y mostrar mensaje del usuario
        st.session_state.chat_asistente.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generar respuesta con la API de Gemini
        with st.chat_message("assistant"):
            with st.spinner("Analizando tu comida..."):
                try:
                    # 1. Obtener datos de meta de la DB del usuario de manera segura
                    perfil_db = run_query(
                        "SELECT meta_kcal FROM control_peso WHERE user_id = %s ORDER BY fecha DESC LIMIT 1",
                        (user_id,)
                    )
                    meta_calorias = perfil_db[0][0] if perfil_db else 2000

                    # 2. Sumar consumo de calorías registradas en el día
                    calorias_hoy_previas = 0
                    if "diario_alimentos" in st.session_state and not st.session_state.diario_alimentos.empty:
                        calorias_hoy_previas = int(st.session_state.diario_alimentos["Kcal"].sum())

                    # 3. System Instruction completo y dinámico
                    system_instruction = (
                        "Eres un Coach Nutricional empático, práctico y preciso. "
                        "Tu tarea es analizar la comida registrada por el usuario, calcular sus macros y compararlos contra sus métricas diarias personales.\n\n"
                        "Sigue estrictamente esta estructura de respuesta:\n"
                        "1. Confirmar brevemente el registro.\n"
                        "2. Dar un desglose estimado de macronutrientes: Calorías (kcal), Proteína (g), Carbohidratos (g) y Grasas (g).\n"
                        "3. Balance Calórico Diario:\n"
                        "   - Calcula las calorías totales acumuladas sumando las calorías de esta comida a las calorías previas ingresadas.\n"
                        "   - Compara el total acumulado contra la Meta Diaria del usuario.\n"
                        "   - Si el total es MENOR o IGUAL a la meta: Indica exactamente cuántas kcal le RESTAN para el día.\n"
                        "   - Si el total SUPERA la meta: Indica claramente por cuántas kcal se EXCEDIÓ y da un consejo amable para ajustar la siguiente comida o el día de mañana.\n"
                        "4. Breve recomendación nutricional sobre los ingredientes (ej. impacto de aderezos, azúcares o calidad de la proteína).\n"
                        "Mantén un tono motivacional y directo."
                    )

                    # 4. Contexto específico enviado a la API
                    prompt_con_contexto = (
                        f"[PERFIL DE CONSUMO DEL USUARIO HOY]\n"
                        f"- Meta diaria de calorías: {meta_calorias} kcal\n"
                        f"- Calorías consumidas previamente hoy: {calorias_hoy_previas} kcal\n\n"
                        f"[COMIDA REGISTRADA]: {prompt}"
                    )

                    response = client.models.generate_content(
                        model="gemini-3.6-flash",
                        contents=f"{system_instruction}\n\n{prompt_con_contexto}"
                    )

                    respuesta_coach = response.text
                    st.markdown(respuesta_coach)
                    
                    # Guardar respuesta en el historial corrigiendo el nombre de la variable
                    st.session_state.chat_asistente.append({"role": "assistant", "content": respuesta_coach})
                except Exception as e:
                    st.error(f"Error al conectar con el asistente: {e}")
