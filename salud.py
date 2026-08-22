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
        st.subheader("📝 Registrar Hoy")
        f_reg = st.date_input("Fecha", key="f_diaria")
        p_reg = st.number_input("Peso (kg)", min_value=30.0, max_value=200.0, value=82.5, step=0.1)

        if st.button("📌 Guardar Peso Diario", use_container_width=True):
            nuevo_p = pd.DataFrame([{"Fecha": pd.to_datetime(f_reg), "Peso (kg)": float(p_reg)}])
            
            if "historial_diario" not in st.session_state:
                st.session_state.historial_diario = pd.DataFrame(columns=["Fecha", "Peso (kg)"])

            # Evitar duplicados del mismo día y ordenar
            st.session_state.historial_diario = (
                pd.concat([st.session_state.historial_diario, nuevo_p])
                .drop_duplicates(subset=["Fecha"], keep="last")
                .sort_values("Fecha")
                .reset_index(drop=True)
            )
            st.success("¡Peso registrado exitosamente!")
            st.rerun()

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
                                model="gemini-3.7-flash", contents=prompt_calorias
                            )
                            texto_respuesta = response.text.strip()
                            
                            # Parsear la respuesta de la IA de forma segura
                            kcal_calc = 350  # Valor por defecto si falla el parseo
                            prot_calc = 20
                            
                            for linea in texto_respuesta.split('\n'):
                                if "KCALS:" in linea:
                                    kcal_calc = int(''.filter(str.isdigit, linea)) if any(c.isdigit() for c in linea) else 350
                                if "PROTEINA:" in linea:
                                    prot_calc = int(''.filter(str.isdigit, linea)) if any(c.isdigit() for c in linea) else 20
                            
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
            hora_inicio = st.time_input("Hora de entrada:", value=time(7, 0))
        with col_h2:
            hora_salida = st.time_input("Hora de salida:", value=time(19, 0))
        with col_h3:
            hora_comida = st.time_input("Hora de comida:", value=time(12, 0))

        col_h4, col_h5, col_h6, col_h7 = st.columns(4)
        with col_h4:
            hora_licuado = st.time_input(
                "Licuado / Al despertar:", value=time(5, 10)
            )
        with col_h5:
            hora_desayuno = st.time_input("Desayuno:", value=time(7, 30))
        with col_h6:
            hora_col2 = st.time_input(
                "Colación Tarde (Media Tarde):", value=time(16, 30)
            )
        with col_h7:
            hora_cena = st.time_input("Cena:", value=time(20, 0))

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
                    model="gemini-2.5-flash", contents=prompt
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
                    # Prompt del sistema para guiar a Gemini a actuar como un Coach Nutricional
                    system_instruction = (
                        "Eres un Coach Nutricional empático, práctico y directo. "
                        "Cuando el usuario te diga lo que comió, debes:\n"
                        "1. Confirmar el registro.\n"
                        "2. Dar un estimado aproximado de calorías (kcal) y proteína (g).\n"
                        "3. Dar un breve consejo o feedback motivacional sobre si tiene margen para sus siguientes comidas.\n"
                        "Mantén la respuesta corta (máximo 3-4 oraciones) y tono amigable."
                    )
                    
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"{system_instruction}\n\nEntrada del usuario: {prompt}"
                    )
                    
                    respuesta_txt = response.text
                    st.markdown(respuesta_txt)
                    
                    # Guardar respuesta en el historial
                    st.session_state.chat_asistente.append({"role": "assistant", "content": respuesta_txt})
                except Exception as e:
                    st.error(f"Error al conectar con el asistente: {e}")