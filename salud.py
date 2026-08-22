from datetime import datetime, time
from google import genai
import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st
import bcrypt

# Configuración de la página
st.set_page_config(
    page_title="NutriTrack & Recetas", page_icon="🥗", layout="wide"
)

# Inicializar cliente de Gemini utilizando el Secret de Streamlit Cloud
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])


# Función para obtener una conexión fresca a la base de datos
def get_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])


# --- FUNCIONES DE BASE DE DATOS Y AUTENTICACIÓN ---
def registrar_nuevo_usuario(nombre, email, password):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            if cur.fetchone():
                return False, "El correo electrónico ya está registrado."

            # Hashear la contraseña antes de guardarla
            hashed_password = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            cur.execute(
                "INSERT INTO usuarios (nombre, email, password) VALUES (%s, %s, %s) RETURNING id",
                (nombre, email, hashed_password),
            )
            nuevo_id = cur.fetchone()[0]
            conn.commit()
            return True, nuevo_id
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


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


# --- CONTROL DE SESIÓN ---
if "user" not in st.session_state:
    st.session_state.user = None

# Si NO hay sesión iniciada, mostramos las pestañas y detenemos la ejecución aquí mismo
if not st.session_state.user:
    st.markdown(
        "<h2 style='text-align: center;'>🥗 NutriTrack & Recetas</h2>",
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 1.5, 1])

    with col2:
        tab_login, tab_registro = st.tabs(["🔑 Iniciar Sesión", "📝 Registrarme"])

        with tab_login:
            with st.form("login_form"):
                email_input = st.text_input(
                    "Correo electrónico", key="login_email"
                )
                password_input = st.text_input(
                    "Contraseña", type="password", key="login_pass"
                )
                submit_login = st.form_submit_button(
                    "Entrar", use_container_width=True
                )

                if submit_login:
                    usuario_valido = verificar_usuario(
                        email_input, password_input
                    )
                    if usuario_valido:
                        st.session_state.user = usuario_valido
                        st.success(
                            f"¡Bienvenido de vuelta,"
                            f" {usuario_valido['nombre']}!"
                        )
                        st.rerun()
                    else:
                        st.error("Correo o contraseña incorrectos.")

        with tab_registro:
            with st.form("registro_form"):
                nombre_nuevo = st.text_input("Nombre completo")
                email_nuevo = st.text_input(
                    "Correo electrónico", key="reg_email"
                )
                password_nuevo = st.text_input(
                    "Crea una contraseña", type="password", key="reg_pass"
                )
                submit_registro = st.form_submit_button(
                    "Crear Cuenta", use_container_width=True
                )

                if submit_registro:
                    if not nombre_nuevo or not email_nuevo or not password_nuevo:
                        st.warning(
                            "Por favor, completa todos los campos para"
                            " registrarte."
                        )
                    else:
                        exito, resultado = registrar_nuevo_usuario(
                            nombre_nuevo, email_nuevo, password_nuevo
                        )
                        if exito:
                            st.success(
                                "¡Cuenta creada con éxito! Ve a la pestaña"
                                " 'Iniciar Sesión' para entrar."
                            )
                        else:
                            st.error(f"No se pudo registrar: {resultado}")
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
        "🥤 Licuados 5:00 AM (L-J)",
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

    registros_db = run_query(
        """
        SELECT fecha, peso, objetivo, meta_principal, fecha_objetivo, diferencia, imc, diagnostico, grasa, musculo, meta_kcal 
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

        col_h1, col_h2 = st.columns(2)
        agua_rec = (peso_actual * 35) / 1000
        col_h1.metric("💧 Meta de Agua", f"{agua_rec:.1f} L/día")
        col_h2.metric("🚶 Pasos / Actividad", "10,000 pasos")
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
                execute_db(
                    """
                    INSERT INTO control_peso (user_id, fecha, peso, objetivo, meta_principal, fecha_objetivo, diferencia, imc, diagnostico, grasa, musculo, meta_kcal)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                    (
                        user_id,
                        fecha,
                        peso,
                        peso_meta,
                        objetivo,
                        str(fecha_meta) if fecha_meta else None,
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
    st.write(
        "Registra tu peso cada mañana y deja que la app interprete las"
        " tendencias por ti."
    )

    col_ingreso, col_analisis = st.columns([1, 2])

    with col_ingreso:
        st.subheader("📝 Registrar Hoy")
        f_reg = st.date_input("Fecha", key="f_diaria")
        p_reg = st.number_input(
            "Peso (kg)", min_value=30.0, max_value=200.0, value=82.5, step=0.1
        )

        if st.button("📌 Guardar Peso Diario", use_container_width=True):
            try:
                execute_db(
                    """
                    INSERT INTO registro_diario_peso (user_id, fecha, peso)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, fecha) DO UPDATE SET peso = EXCLUDED.peso
                """,
                    (user_id, f_reg, p_reg),
                )
                st.success("¡Peso diario registrado exitosamente!")
            except Exception as e:
                st.error(f"Error al guardar: {e}")

    with col_analisis:
        st.subheader("📊 Análisis e Interpretación")
        diarios_db = run_query(
            "SELECT fecha, peso FROM registro_diario_peso WHERE user_id = %s ORDER BY fecha ASC",
            (user_id,),
        )

        if diarios_db:
            df = pd.DataFrame(diarios_db, columns=["Fecha", "Peso (kg)"])
            df["Fecha"] = pd.to_datetime(df["Fecha"])

            p_actual = df.iloc[-1]["Peso (kg)"]
            p_min = df["Peso (kg)"].min()
            p_max = df["Peso (kg)"].max()
            ultimos_7 = df.tail(7)
            prom_semanal = ultimos_7["Peso (kg)"].mean()

            st.success(
                f"💡 Tu promedio semanal actual es de **{prom_semanal:.2f} kg**."
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("⚖️ Peso Diario", f"{p_actual:.1f} kg")
            c2.metric("📅 Promedio Semanal", f"{prom_semanal:.2f} kg")
            c3.metric("📉 Mínimo Histórico", f"{p_min:.1f} kg")
            c4.metric("📈 Máximo Histórico", f"{p_max:.1f} kg")

            df["Promedio Móvil"] = (
                df["Peso (kg)"].rolling(window=7, min_periods=1).mean()
            )
            fig = px.line(
                df,
                x="Fecha",
                y=["Peso (kg)", "Promedio Móvil"],
                markers=True,
                title="Peso Diario vs. Tendencia Real",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Aún no hay registros diarios guardados en la base de datos."
            )

# ==========================================
# MÓDULO 3: LICUADOS 5:00 AM
# ==========================================
elif opcion == "🥤 Licuados 5:00 AM (L-J)":
    st.header("🥤 Planificador de Licuados para el Despertar (5:10 AM)")
    frutas_disponibles = st.text_input(
        "🍎 Frutas disponibles en casa esta semana:",
        "Manzana, papaya, fresas congeladas, peras, plátano",
    )
    if st.button("🥤 Generar Plan de Licuados (Lunes a Jueves)"):
        try:
            prompt = f"Crea un plan de 4 licuados para despertar usando estas frutas: {frutas_disponibles}."
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            st.session_state["plan_licuados_texto"] = response.text
        except Exception as e:
            st.error(f"Error: {e}")

    if "plan_licuados_texto" in st.session_state:
        st.markdown(st.session_state["plan_licuados_texto"])

# ==========================================
# MÓDULO 4: REGISTRO DE ALIMENTACIÓN
# ==========================================
elif opcion == "🥗 Registro de Alimentación":
    st.header("🥗 Registro de Alimentación")
    st.write(
        "Controla tus porciones guardadas en tu perfil para este usuario."
    )
    st.info("Módulo de porciones sincronizado con tu cuenta.")

# ==========================================
# MÓDULO 5: GENERADOR DE RECETAS AVANZADO
# ==========================================
elif opcion == "🍳 Generador de Recetas":
    st.header("🍳 Generador Inteligente de Recetas")
    
    # --- FORMULARIO DE PREFERENCIAS ---
    with st.expander("⚙️ Configuración de Preferencias y Horarios", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            tiempo_comida = st.selectbox("Tiempo de comida:", ["Desayuno", "Comida", "Cena"])
            horario_trabajo = st.time_input("Hora de tu jornada de trabajo:", value=time(9, 0))
            proteinas = st.text_input("Proteínas preferidas (pollo, carne, huevo, tofu...):", "Pollo, Huevo, Pescado")
        with col2:
            frutas_verduras = st.text_input("Frutas y Verduras que te gustan:", "Manzana, Espinacas, Brócoli, Fresas")
            no_gustan = st.text_input("Ingredientes que NO te gustan:", "Cebolla, Calabaza")
            nivel_cocina = st.select_slider("Nivel de dificultad (tiempo disponible):", options=["Muy Rápido", "Estándar", "Gourmet"])

    if st.button("🍳 Generar Receta Personalizada", use_container_width=True):
        with st.spinner("Diseñando tu platillo ideal..."):
            try:
                # Construimos el prompt con todas tus variables
                prompt = f"""
                Actúa como un chef y nutricionista experto. 
                Crea una receta para {tiempo_comida}.
                Considerando que mi horario de trabajo inicia a las {horario_trabajo.strftime('%H:%M')}, 
                la receta debe ser adecuada en tiempo y energía.
                
                Preferencias:
                - Proteínas a incluir: {proteinas}
                - Frutas/Verduras que me gustan: {frutas_verduras}
                - Ingredientes que NO debo incluir: {no_gustan}
                - Nivel de cocina: {nivel_cocina}
                
                La receta debe ser saludable, equilibrada, práctica y deliciosa.
                """
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt
                )
                
                receta_txt = response.text
                st.markdown("---")
                st.markdown(receta_txt)
                
                # Guardar en sesión
                st.session_state.ultima_receta = receta_txt
                
            except Exception as e:
                st.error(f"Error al generar: {e}")

    # Guardar en BD si ya existe una receta
    if "ultima_receta" in st.session_state:
        if st.button("💾 Guardar esta receta en mi cuenta"):
            try:
                execute_db(
                    """
                    INSERT INTO recetas_guardadas (user_id, dia_semana, tiempo_comida, receta_texto)
                    VALUES (%s, %s, %s, %s)
                """,
                    (user_id, "General", tiempo_comida, st.session_state.ultima_receta),
                )
                st.success("¡Receta guardada!")
            except Exception as e:
                st.error(f"Error: {e}")

# ==========================================
# MÓDULO 6: LISTA DE COMPRAS
# ==========================================
elif opcion == "🛒 Lista de Compras":
    st.header("🛒 Tu Lista de Supermercado")
    nuevo_item = st.text_input("Agregar ingrediente:")
    if st.button("Añadir"):
        if nuevo_item:
            st.session_state.lista_compras.append(nuevo_item)
            st.success("Agregado.")
    for item in st.session_state.lista_compras:
        st.write(f"- {item}")

# ==========================================
# MÓDULO 7: HÁBITOS
# ==========================================
elif opcion == "🔥 Seguimiento de Hábitos":
    st.header("🔥 Registro de Hábitos Diarios")
    f_habito = st.date_input("Fecha hábito")
    h_agua = st.checkbox("Agua suficiente")
    if st.button("Guardar Hábitos"):
        try:
            execute_db(
                """
                INSERT INTO habitos_diarios (user_id, fecha, agua, cumplido_total)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, fecha) DO UPDATE SET agua = EXCLUDED.agua
            """,
                    (user_id, f_habito, h_agua, h_agua),
            )
            st.success("Hábitos guardados correctamente.")
        except Exception as e:
            st.error(f"Error: {e}")

# ==========================================
# MÓDULO 8: REPORTES SEMANALES
# ==========================================
elif opcion == "📈 Reporte Semanal":
    st.header("📈 Reporte Semanal de Progreso")
    st.write(
        "Aquí puedes visualizar el comportamiento consolidado de tus registros"
        " recientes."
    )

# ==========================================
# MÓDULO 9: ASISTENTE VIRTUAL NUTRICIONAL
# ==========================================
elif opcion == "🤖 Asistente Virtual Nutricional":
    st.header("🤖 Coach Personal de Nutrición")
    if prompt := st.chat_input("Escribe lo que comiste..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash", contents=prompt
            )
            with st.chat_message("assistant"):
                st.markdown(response.text)
        except Exception as e:
            st.error(f"Error: {e}")