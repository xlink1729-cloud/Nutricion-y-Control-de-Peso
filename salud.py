import datetime
from datetime import date
from datetime import time as dt_time
import os
import time
import google.genai as genai
import matplotlib.pyplot as plt
import pandas as pd
import psycopg2
import plotly.express as px
import streamlit as st

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(
    page_title="App de Alto Rendimiento", page_icon="⚡", layout="wide"
)

# Estilos CSS Personalizados
st.markdown(
    """
    <style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .metric-card {
        background-color: #1E222D;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #2E3440;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Inicialización de Gemini Client
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Modelo estándar a utilizar
MODEL_NAME = "gemini-1.5-flash"

# ==========================================
# 2. GESTIÓN DE BASE DE DATOS (POSTGRESQL)
# ==========================================
def get_connection():
    try:
        conn = psycopg2.connect(st.secrets["postgres"]["url"])
        return conn
    except Exception as e:
        st.error(f"Error al conectar con la Base de Datos: {e}")
        return None

def run_query(query, params=(), fetch=True):
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if fetch:
                result = cur.fetchall()
            else:
                conn.commit()
                result = True
        return result
    except Exception as e:
        st.error(f"Error en consulta SQL: {e}")
        return []
    finally:
        conn.close()

# Inicialización de tablas si no existen
def init_db():
    queries = [
        """
        CREATE TABLE IF NOT EXISTS seguimiento_diario (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            fecha DATE,
            peso FLOAT,
            horas_sueno FLOAT,
            energia INT,
            humor INT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS comidas (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            fecha DATE,
            descripcion TEXT,
            calorias INT,
            proteinas INT
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS habitos (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(50),
            fecha DATE,
            habito VARCHAR(100),
            completado BOOLEAN
        );
        """,
    ]
    for q in queries:
        run_query(q, fetch=False)

init_db()

# Estado de la Sesión
if "user_id" not in st.session_state:
    st.session_state.user_id = "usuario_demo"

USER_ID = st.session_state.user_id

# ==========================================
# 3. BARRA LATERAL (NAVEGACIÓN)
# ==========================================
st.sidebar.title("⚡ Dashboard de Rendimiento")
menu = st.sidebar.radio(
    "Selecciona una opción:",
    [
        "1. Visión General",
        "2. Registro Diario (Salud)",
        "3. Optimización de Sueño",
        "4. Nutrición & Registro Inteligente",
        "5. Entrenamientos & Rutinas",
        "6. Gestión de Tiempo / Pomodoro",
        "7. Tracker de Hábitos",
        "8. Reporte Semanal (IA)",
        "9. Consultoría Directa IA",
    ],
)

# ==========================================
# MÓDULO 1: VISIÓN GENERAL
# ==========================================
if menu == "1. Visión General":
    st.title("🔥 Visión General del Rendimiento")
    st.write(f"Bienvenido de nuevo, **{USER_ID}**.")

    col1, col2, col3, col4 = st.columns(4)

    # Cargar datos desde la BD
    datos_recientes = run_query(
        "SELECT peso, horas_sueno, energia FROM seguimiento_diario WHERE user_id = %s ORDER BY fecha DESC LIMIT 1",
        (USER_ID,),
    )
    comidas_recientes = run_query(
        "SELECT SUM(calorias) FROM comidas WHERE user_id = %s AND fecha = %s",
        (USER_ID, date.today()),
    )

    peso_actual = datos_recientes[0][0] if datos_recientes else "--"
    sueno_actual = datos_recientes[0][1] if datos_recientes else "--"
    energia_actual = datos_recientes[0][2] if datos_recientes else "--"
    cals_hoy = (
        comidas_recientes[0][0]
        if comidas_recientes and comidas_recientes[0][0]
        else 0
    )

    col1.metric("Peso Último", f"{peso_actual} kg")
    col2.metric("Sueño Anoche", f"{sueno_actual} hrs")
    col3.metric("Nivel de Energía", f"{energia_actual}/10")
    col4.metric("Kcal Hoy", f"{cals_hoy} kcal")

    st.markdown("---")
    st.subheader("📈 Resumen Rápido")
    st.info(
        "Utiliza la barra lateral para registrar tu día a día o interactuar con la IA para analizar tu nutrición y descanso."
    )

# ==========================================
# MÓDULO 2: REGISTRO DIARIO (SALUD)
# ==========================================
elif menu == "2. Registro Diario (Salud)":
    st.title("📝 Registro Diario de Métricas")

    col_input, col_chart = st.columns([1, 1.5])

    with col_input:
        st.subheader("Ingresar Datos de Hoy")
        fecha_input = st.date_input("Fecha", date.today())
        peso = st.number_input(
            "Peso (kg)", min_value=30.0, max_value=200.0, value=75.0, step=0.1
        )
        sueno = st.number_input(
            "Horas de Sueño",
            min_value=0.0,
            max_value=16.0,
            value=7.5,
            step=0.5,
        )
        energia = st.slider("Nivel de Energía (1-10)", 1, 10, 7)
        humor = st.slider("Estado de Ánimo (1-10)", 1, 10, 7)

        if st.button("Guardar Registro"):
            query = """
                INSERT INTO seguimiento_diario (user_id, fecha, peso, horas_sueno, energia, humor)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            run_query(
                query,
                (USER_ID, fecha_input, peso, sueno, energia, humor),
                fetch=False,
            )
            st.success("¡Registro guardado exitosamente!")

    with col_chart:
        st.subheader("Evolución Reciente")
        registros_db = run_query(
            "SELECT fecha AS \"Fecha\", peso AS \"Peso\", horas_sueno AS \"Sueño\" FROM seguimiento_diario WHERE user_id = %s ORDER BY fecha ASC",
            (USER_ID,),
        )

        if registros_db:
            df = pd.DataFrame(registros_db, columns=["Fecha", "Peso", "Sueño"])
            fig = px.line(
                df,
                x="Fecha",
                y=["Peso", "Sueño"],
                title="Histórico de Peso y Sueño",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("No hay suficientes datos para mostrar gráficas.")

# ==========================================
# MÓDULO 3: OPTIMIZACIÓN DE SUEÑO
# ==========================================
elif menu == "3. Optimización de Sueño":
    st.title("🌙 Calculadora y Optimización de Sueño")

    st.write("Basado en ciclos circadianos estándar de 90 minutos.")
    hora_despertar = st.time_input(
        "¿A qué hora necesitas despertarte?", dt_time(7, 0)
    )

    if st.button("Calcular Hora Recomendada para Dormir"):
        # Convertir a datetime para operaciones
        now = datetime.datetime.now()
        dt_despertar = datetime.datetime.combine(now.date(), hora_despertar)

        # 5 ciclos = 7.5 hrs, 6 ciclos = 9 hrs (sumando 15 min para conciliar sueño)
        opcion1 = dt_despertar - datetime.timedelta(hours=9, minutes=15)
        opcion2 = dt_despertar - datetime.timedelta(hours=7, minutes=45)

        st.success(
            f"**Opción 1 (9 hrs):** Ir a la cama a las **{opcion1.strftime('%H:%M')}**"
        )
        st.success(
            f"**Opción 2 (7.5 hrs):** Ir a la cama a las **{opcion2.strftime('%H:%M')}**"
        )

    st.markdown("---")
    st.subheader("💡 Consejo IA para mejorar tu Descanso")
    if st.button("Generar Consejo de Descanso"):
        if client:
            prompt = "Dame 3 consejos concisos y validados científicamente para mejorar la calidad del sueño profundo."
            response = client.models.generate_content(
                model=MODEL_NAME, contents=prompt
            )
            st.markdown(response.text)
        else:
            st.error("API Key de Gemini no configurada.")

# ==========================================
# MÓDULO 4: NUTRICIÓN & REGISTRO INTELIGENTE
# ==========================================
elif menu == "4. Nutrición & Registro Inteligente":
    st.title("🥗 Nutrición con IA")

    col_macro, col_ia = st.columns([1, 1])

    with col_macro:
        st.subheader("Registro de Comidas de Hoy")
        descripcion = st.text_input("Descripción de la comida (ej. 200g pechuga con arroz)")
        kcal = st.number_input("Calorías (Kcal)", min_value=0, value=500)
        proteina = st.number_input("Proteínas (g)", min_value=0, value=30)

        if st.button("Guardar Comida"):
            query = "INSERT INTO comidas (user_id, fecha, descripcion, calorias, proteinas) VALUES (%s, %s, %s, %s, %s)"
            run_query(
                query,
                (USER_ID, date.today(), descripcion, kcal, proteina),
                fetch=False,
            )
            st.success("Comida registrada.")

    with col_ia:
        st.subheader("🤖 Analizar Comida mediante Descripción (IA)")
        texto_libre = st.text_area(
            "Describe lo que comiste:",
            placeholder="Ejemplo: Un tazón de avena con plátano, miel y una cucharada de crema de maní.",
        )

        if st.button("Calcular Macros con IA"):
            if client and texto_libre:
                prompt = f"""
                Analiza el siguiente plato: "{texto_libre}". 
                Estima las calorías totales y gramos de proteína. 
                Devuelve únicamente el formato exacto:
                KCALS: [numero]
                PROTEINA: [numero]
                DETALLE: [breve explicación de 1 frase]
                """
                response = client.models.generate_content(
                    model=MODEL_NAME, contents=prompt
                )
                texto_respuesta = response.text
                st.write(texto_respuesta)

                # CORRECCIÓN SINTÁCTICA CRÍTICA DE FILTER
                kcal_calc, prot_calc = 0, 0
                for linea in texto_respuesta.split("\n"):
                    if "KCALS:" in linea:
                        digits = "".join(filter(str.isdigit, linea))
                        kcal_calc = int(digits) if digits else 0
                    if "PROTEINA:" in linea:
                        digits = "".join(filter(str.isdigit, linea))
                        prot_calc = int(digits) if digits else 0

                if kcal_calc > 0:
                    run_query(
                        "INSERT INTO comidas (user_id, fecha, descripcion, calorias, proteinas) VALUES (%s, %s, %s, %s, %s)",
                        (
                            USER_ID,
                            date.today(),
                            texto_libre[:50],
                            kcal_calc,
                            prot_calc,
                        ),
                        fetch=False,
                    )
                    st.success(
                        f"¡Registrado automáticamente! {kcal_calc} kcal | {prot_calc}g Proteína"
                    )
            else:
                st.error("Requiere la API Key de Gemini y un texto de entrada.")

# ==========================================
# MÓDULO 5: ENTRENAMIENTOS & RUTINAS
# ==========================================
elif menu == "5. Entrenamientos & Rutinas":
    st.title("🏋️ Generador de Rutinas IA")

    nivel = st.selectbox("Nivel de experiencia", ["Principiante", "Intermedio", "Avanzado"])
    equipo = st.selectbox("Equipamiento", ["Gimnasio Completo", "Mancuernas y Peso Corporal", "Solo Peso Corporal"])
    objetivo = st.text_input("Objetivo principal", "Hipertrofia / Ganar masa muscular")

    if st.button("Generar Rutina"):
        if client:
            prompt = f"Diseña una rutina de entrenamiento de 3 días enfocada en {objetivo}. Nivel: {nivel}. Equipamiento disponible: {equipo}. Presenta el resultado en formato Markdown con tablas."
            with st.spinner("Diseñando rutina personalizada..."):
                response = client.models.generate_content(
                    model=MODEL_NAME, contents=prompt
                )
                st.markdown(response.text)
        else:
            st.error("API Key de Gemini no configurada.")

# ==========================================
# MÓDULO 6: GESTIÓN DE TIEMPO / POMODORO
# ==========================================
elif menu == "6. Gestión de Tiempo / Pomodoro":
    st.title("⏱️ Temporizador Pomodoro")

    duracion_min = st.number_input("Minutos de trabajo", min_value=1, max_value=60, value=25)

    if st.button("Iniciar Bloque de Enfoque"):
        segundos = duracion_min * 60
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i in range(segundos, 0, -1):
            mins, secs = divmod(i, 60)
            status_text.markdown(f"### ⏳ Tiempo restante: **{mins:02d}:{secs:02d}**")
            progress_bar.progress((segundos - i) / segundos)
            time.sleep(1)

        status_text.markdown("### 🎉 ¡Bloque completado! Toma un descanso.")
        st.balloons()

# ==========================================
# MÓDULO 7: TRACKER DE HÁBITOS
# ==========================================
elif menu == "7. Tracker de Hábitos":
    st.title("✅ Tracker de Hábitos")

    nuevo_habito = st.text_input("Nuevo hábito a seguir:")
    if st.button("Agregar Hábito") and nuevo_habito:
        run_query(
            "INSERT INTO habitos (user_id, fecha, habito, completado) VALUES (%s, %s, %s, %s)",
            (USER_ID, date.today(), nuevo_habito, False),
            fetch=False,
        )
        st.success(f"Hábito '{nuevo_habito}' registrado.")

    st.subheader("Hábitos de Hoy")
    habitos_hoy = run_query(
        "SELECT id, habito, completado FROM habitos WHERE user_id = %s AND fecha = %s",
        (USER_ID, date.today()),
    )

    if habitos_hoy:
        for hab_id, hab_nombre, estado in habitos_hoy:
            check = st.checkbox(hab_nombre, value=estado, key=f"hab_{hab_id}")
            if check != estado:
                run_query(
                    "UPDATE habitos SET completado = %s WHERE id = %s",
                    (check, hab_id),
                    fetch=False,
                )
                st.rerun()
    else:
        st.info("No hay hábitos registrados para el día de hoy.")

# ==========================================
# MÓDULO 8: REPORTE SEMANAL (IA)
# ==========================================
elif menu == "8. Reporte Semanal (IA)":
    st.title("📊 Análisis Semanal Consolidado")

    # Lectura correcta desde PostgreSQL
    registros = run_query(
        "SELECT fecha, peso, horas_sueno, energia FROM seguimiento_diario WHERE user_id = %s ORDER BY fecha DESC LIMIT 7",
        (USER_ID,),
    )

    if st.button("Generar Diagnóstico Semanal con IA"):
        if not registros:
            st.warning("No hay suficientes datos registrados en la BD para generar el reporte.")
        elif client:
            contexto = f"Datos de los últimos días del usuario: {registros}"
            prompt = f"Actúa como un coach de rendimiento. Analiza estos datos semanales del usuario y dame un reporte estratégico breve (Puntos fuertes, áreas de mejora y 2 acciones clave): {contexto}"
            with st.spinner("Analizando tu semana..."):
                response = client.models.generate_content(
                    model=MODEL_NAME, contents=prompt
                )
                st.markdown(response.text)
        else:
            st.error("API Key de Gemini no configurada.")

# ==========================================
# MÓDULO 9: CONSULTORÍA DIRECTA IA
# ==========================================
elif menu == "9. Consultoría Directa IA":
    st.title("💬 Consultor de Rendimiento IA")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Mostrar historial
    for mensaje in st.session_state.chat_history:
        with st.chat_message(mensaje["role"]):
            st.markdown(mensaje["content"])

    # Entrada de usuario
    user_prompt = st.chat_input("Haz una pregunta sobre tu salud, entrenamiento o productividad...")
    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        if client:
            with st.chat_message("assistant"):
                response = client.models.generate_content(
                    model=MODEL_NAME, contents=user_prompt
                )
                st.markdown(response.text)
                st.session_state.chat_history.append(
                    {"role": "assistant", "content": response.text}
                )
        else:
            st.error("API Key de Gemini no configurada.")
