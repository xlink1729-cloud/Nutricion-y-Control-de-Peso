import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai
from datetime import datetime, time
import psycopg2

# Configuración de la página
st.set_page_config(
    page_title="NutriTrack & Recetas", page_icon="🥗", layout="wide"
)

# Inicializar cliente de Gemini utilizando el Secret de Streamlit Cloud
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

st.title("🥗 NutriTrack & Generador de Recetas")
st.write(
    "Lleva el control de tu progreso físico, planifica tu semana y transforma"
    " tus porciones en recetas reales."
)

# Función para conectar a Neon cargando la URL desde secrets.toml
@st.cache_resource
def init_connection():
    return psycopg2.connect(st.secrets["postgres"]["url"])


conn = init_connection()

# Función helper para ejecutar consultas de lectura (SELECT)
def run_query(query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params)
        return cur.fetchall()

# Función helper para guardar o actualizar datos (INSERT / UPDATE)
def execute_db(query, params=None):
    with conn.cursor() as cur:
        cur.execute(query, params)
        conn.commit()

# Función para guardar la receta en Neon
def guardar_receta_db(dia, tiempo, texto_receta):
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO recetas_guardadas (dia_semana, tiempo_comida, receta_texto)
                VALUES (%s, %s, %s)
            """,
                (dia, tiempo, texto_receta),
            )
            conn.commit()
            st.success("💾 ¡Receta guardada exitosamente en la base de datos!")
    except Exception as e:
        st.error(f"Error al guardar en la base de datos: {e}")

def calcular_requerimiento_calorico(peso, estatura_cm, edad, sexo, nivel_actividad):
    """Calcula el Gasto Energético Total (TDEE) estimado usando Harris-Benedict."""
    if sexo.lower() in ["hombre", "masculino"]:
        tbm = 88.362 + (13.397 * peso) + (4.799 * estatura_cm) - (5.677 * edad)
    else:
        tbm = 447.593 + (9.247 * peso) + (3.098 * estatura_cm) - (4.330 * edad)

    # Factores de actividad física
    factores = {
        "Sedentario (pocos o ningún ejercicio)": 1.2,
        "Ligeramente activo (1-3 días/semana)": 1.375,
        "Moderadamente activo (3-5 días/semana)": 1.55,
        "Muy activo (6-7 días/semana)": 1.725,
        "Fuerte / Atleta (entrenamiento doble)": 1.9,
    }
    factor = factores.get(nivel_actividad, 1.375)
    return int(tbm * factor)


def calcular_calorias_porciones(plan):
    """Estima las calorías diarias que suma el plan de porciones (SMAE)."""
    tabla_kcal = {
        "Verduras": 25,
        "Frutas": 60,
        "Cereales": 70,
        "AOA (Proteína)": 75,
        "Lácteos": 110,
        "Grasas s/ Prot": 45,
        "Grasas c/ Prot": 70,
        "Leguminosas": 120,
    }
    total_kcal = 0
    for tiempo, grupos in plan.items():
        for grupo, cant in grupos.items():
            total_kcal += tabla_kcal.get(grupo, 50) * cant
    return int(total_kcal)

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

# Inicializar bases de datos simples en la sesión
if "registro_progreso" not in st.session_state:
    st.session_state.registro_progreso = pd.DataFrame(
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
        ]
    )

if "lista_compras" not in st.session_state:
    st.session_state.lista_compras = []

# ==========================================
# MÓDULO 0: DASHBOARD PRINCIPAL
# ==========================================
if opcion == "🏠 Dashboard Principal":
    st.header("🏠 Resumen Diario")
    st.write("Vista rápida de tus metas, consumo e indicadores del día.")

    if not st.session_state.registro_progreso.empty:
        # Extraer datos reales del registro
        ultimo_registro = st.session_state.registro_progreso.iloc[-1]
        primer_registro = st.session_state.registro_progreso.iloc[0]

        peso_inicial = float(primer_registro["Peso (kg)"])
        peso_actual = float(ultimo_registro["Peso (kg)"])
        peso_meta = float(ultimo_registro["Objetivo (kg)"])
        meta_kcal = int(ultimo_registro["Meta Kcal"])

        kg_cambiados = abs(peso_inicial - peso_actual)
        kg_meta_total = abs(peso_inicial - peso_meta)
        pct_avance = min(1.0, max(0.0, kg_cambiados / kg_meta_total)) if kg_meta_total > 0 else 1.0

        st.markdown("### 📈 Progreso General")
        st.write(
            f"**Has avanzado {kg_cambiados:.1f} kg de {kg_meta_total:.1f} kg objetivo**"
        )
        st.progress(pct_avance)
        st.caption(f"🎯 Cumplido el **{int(pct_avance * 100)}%** de tu meta de peso.")

        st.markdown("---")
        st.markdown("### 🗓️ Estado de Hoy")

        # Fila 1: Control de Peso
        col_p1, col_p2, col_p3 = st.columns(3)
        col_p1.metric("⚖️ Peso Actual", f"{peso_actual:.1f} kg")
        col_p2.metric("🎯 Peso Objetivo", f"{peso_meta:.1f} kg")
        col_p3.metric("📉 Diferencia Restante", f"{abs(peso_actual - peso_meta):.1f} kg")

        st.markdown("---")

        # Fila 2: Nutrición y Calorías
        col_n1, col_n2, col_n3 = st.columns(3)
        col_n1.metric("🔥 Meta Calórica", f"{meta_kcal} kcal/día")
        col_n2.metric("🍽️ Calorías Restantes", f"{meta_kcal} kcal")
        col_n3.metric("🥗 Proteína Objetivo", "~120g - 150g")

        st.markdown("---")

        # Fila 3: Estilo de Vida y Hábitos
        col_h1, col_h2 = st.columns(2)
        agua_rec = (peso_actual * 35) / 1000
        col_h1.metric("💧 Meta de Agua", f"{agua_rec:.1f} L/día")
        col_h2.metric("🚶 Pasos / Actividad", "10,000 pasos")
    else:
        st.info("👋 ¡Bienvenido! Ingresa primero tus datos en la sección **📊 Control de Peso y Músculo** para activar tu Dashboard.")

# ==========================================
# MÓDULO 1: PERFIL INICIAL Y CONTROL DE PESO
# ==========================================
elif opcion == "📊 Control de Peso y Músculo":
    st.header("👤 Perfil Inicial, Diagnóstico y Objetivos")
    st.write(
        "Configura tus datos biométricos para obtener tu diagnóstico metabólico y dar seguimiento a tus metas."
    )

    col1, col2 = st.columns([1.2, 1.8])

    with col1:
        st.subheader("1. Perfil Inicial")
        fecha = st.date_input("Fecha de registro", key="fecha_reg")
        genero = st.selectbox("Sexo", ["Hombre", "Mujer"])
        edad = st.number_input("Edad", min_value=10, max_value=120, value=28)
        estatura_cm = st.number_input(
            "Estatura (cm)", min_value=100.0, max_value=250.0, value=170.0, step=1.0
        )
        peso = st.number_input(
            "Peso actual (kg)", min_value=30.0, max_value=200.0, value=84.0, step=0.1
        )
        peso_meta = st.number_input(
            "🎯 Peso objetivo (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1
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

        # ----------------------------------------------------
        # 🧮 CÁLCULOS AUTOMÁTICOS DE LA APP
        # ----------------------------------------------------
        estatura_m = estatura_cm / 100
        
        # 1. IMC y Diagnóstico
        imc = peso / (estatura_m ** 2)
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

        # 2. Peso Saludable Aproximado (IMC ideal ~22.5)
        peso_saludable_aprox = 22.5 * (estatura_m ** 2)

        # 3. Metabolismo Basal (TMB - Mifflin-St Jeor)
        if genero == "Hombre":
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) + 5
        else:
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) - 161

        # 4. Gasto Energético Diario Estimado (TDEE)
        mult_act = {
            "Sedentario (Oficina / Trabajo de escritorio)": 1.2,
            "Ligero (Oficina + Caminata diaria ligera)": 1.375,
            "Mixto 50/50 (Oficina + Trabajo de campo / Mantenimiento)": 1.55,
            "Activo (Trabajo físico pesado o ejercicio diario)": 1.725,
            "Muy Activo (Trabajo pesado + Ejercicio intenso)": 1.9,
        }
        tdee = tmb * mult_act[actividad]

        # 5. Meta Calórica Orientativa según el Objetivo seleccionado
        if "Perder peso" in objetivo:
            meta_calorica = tdee * 0.80  # Déficit del 20%
        elif "Recomposición" in objetivo:
            meta_calorica = tdee * 0.90  # Déficit ligero del 10% (o tdee directo)
        elif "Ganar masa" in objetivo:
            meta_calorica = tdee * 1.15  # Superávit del 15%
        else:
            meta_calorica = tdee        # Mantenimiento

        # Composición corporal y diferencia
        kilos_diferencia = peso - peso_meta
        val_genero = 1 if genero == "Hombre" else 0
        pct_grasa = max(5.0, min((1.20 * imc) + (0.23 * edad) - (10.8 * val_genero) - 5.4, 60.0))
        pct_musculo = 100.0 - pct_grasa

        # ----------------------------------------------------
        # 📊 DESPLIEGUE DE RESULTADOS
        # ----------------------------------------------------
        st.markdown("---")
        st.markdown("### 🧮 Métricas Calculadas Automáticamente:")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.metric("1. IMC", f"{imc:.1f}", delta=diagnostico_imc, delta_color="off")
            st.metric("3. Metabolismo Basal (TMB)", f"{int(tmb)} kcal/día")
            st.metric("5. Meta Calórica Orientativa", f"{int(meta_calorica)} kcal/día")
        with m_col2:
            st.metric("2. Peso Saludable Aprox.", f"~{peso_saludable_aprox:.1f} kg")
            st.metric("4. Gasto Diario (TDEE)", f"{int(tdee)} kcal/día")

        # Hidratación recomendada
        agua_base = (peso * 35) / 1000
        agua_oficina = agua_base + 0.5
        agua_campo = agua_base + 1.2

        st.markdown("---")
        st.markdown("#### 💧 Hidratación Recomendada:")
        c_h1, c_h2 = st.columns(2)
        c_h1.metric("🏢 Día de Oficina", f"{agua_oficina:.1f} L/día")
        c_h2.metric("🛠️ Día de Campo", f"{agua_campo:.1f} L/día")

        if st.button("💾 Guardar Perfil / Registro"):
            nuevo_registro = pd.DataFrame(
                [[
                    fecha,
                    peso,
                    peso_meta,
                    objetivo,
                    fecha_meta if fecha_meta else "N/A",
                    round(kilos_diferencia, 1),
                    round(imc, 1),
                    diagnostico_imc,
                    round(pct_grasa, 1),
                    round(pct_musculo, 1),
                    int(meta_calorica),
                ]],
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
            st.session_state.registro_progreso = pd.concat(
                [st.session_state.registro_progreso, nuevo_registro],
                ignore_index=True,
            )
            st.success("¡Perfil y registro guardados exitosamente!")

    with col2:
        st.subheader("2. Seguimiento y Progreso")

        if not st.session_state.registro_progreso.empty:
            peso_inicial = float(st.session_state.registro_progreso.iloc[0]["Peso (kg)"])
            peso_actual = float(st.session_state.registro_progreso.iloc[-1]["Peso (kg)"])

            total_a_cambiar = abs(peso_inicial - peso_meta)
            cambio_actual = abs(peso_inicial - peso_actual)

            if total_a_cambiar > 0:
                porcentaje_avance = min(1.0, max(0.0, cambio_actual / total_a_cambiar))
                st.write(f"**Avance hacia la meta:** {int(porcentaje_avance * 100)}%")
                st.progress(porcentaje_avance)

            st.dataframe(st.session_state.registro_progreso, use_container_width=True)

            fig = px.line(
                st.session_state.registro_progreso,
                x="Fecha",
                y=["Peso (kg)", "Objetivo (kg)"],
                markers=True,
                title="Evolución del Peso vs. Peso Objetivo",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Ingresa tus datos en la sección 'Perfil Inicial' y haz clic en 'Guardar Perfil / Registro'.")

    # 🔥 ESTIMACIÓN DE INGESTA CALÓRICA DIARIA
    st.markdown("---")
    st.subheader("🔥 Estimación de Ingesta Calórica Diaria")

    peso_u = st.session_state.get("peso", peso)
    estatura_u = st.session_state.get("estatura", estatura_cm)
    edad_u = st.session_state.get("edad", edad)
    sexo_u = st.session_state.get("sexo", genero)
    actividad_u = st.session_state.get("nivel_actividad", actividad)

    kcal_requeridas = calcular_requerimiento_calorico(
        peso_u, estatura_u, edad_u, sexo_u, actividad_u
    )
    kcal_plan = calcular_calorias_porciones(
        st.session_state.get("plan_nutriologa_horarios", {})
    )

    col_k1, col_k2, col_k3 = st.columns(3)

    with col_k1:
        st.metric(
            label="🎯 Requerimiento Calórico Estimado",
            value=f"{kcal_requeridas:,} kcal/día",
            help="Calorías aproximadas para mantener tu peso según tu perfil y actividad física.",
        )

    with col_k2:
        st.metric(
            label="🥗 Calorías del Plan de Porciones",
            value=f"{kcal_plan:,} kcal/día",
            help="Suma aproximada de las calorías que contienen tus porciones asignadas por la nutrióloga.",
        )

    with col_k3:
        diferencia = kcal_plan - kcal_requeridas
        etiqueta = "Déficit" if diferencia < 0 else "Superávit"
        st.metric(
            label=f"⚖️ Balance ({etiqueta})",
            value=f"{diferencia:+} kcal",
            delta=f"{diferencia} kcal respecto al mantenimiento",
        )

    st.caption(
        "💡 *Nota: Estos valores son estimaciones aproximadas basadas en fórmulas estándar (Harris-Benedict) y valores promedio por grupo de alimentos (SMAE).*"
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
            nuevo_p = pd.DataFrame([{"Fecha": pd.to_datetime(f_reg), "Peso (kg)": p_reg}])
            
            if "historial_diario" not in st.session_state:
                st.session_state.historial_diario = pd.DataFrame(columns=["Fecha", "Peso (kg)"])

            # Evitar duplicados del mismo día
            st.session_state.historial_diario = (
                pd.concat([st.session_state.historial_diario, nuevo_p])
                .drop_duplicates(subset=["Fecha"], keep="last")
                .sort_values("Fecha")
                .reset_index(drop=True)
            )
            st.success("¡Peso registrado exitosamente!")

    with col_analisis:
        st.subheader("📊 Análisis e Interpretación")

        if "historial_diario" in st.session_state and not st.session_state.historial_diario.empty:
            df = st.session_state.historial_diario.copy()
            df["Fecha"] = pd.to_datetime(df["Fecha"])
            
            # --- 1. MÉTRICAS BÁSICAS Y EXTREMOS ---
            p_actual = df.iloc[-1]["Peso (kg)"]
            p_min = df["Peso (kg)"].min()
            p_max = df["Peso (kg)"].max()

            # Promedio últimos 7 días
            ultimos_7 = df.tail(7)
            prom_semanal = ultimos_7["Peso (kg)"].mean()

            # --- 2. COMPARATIVA SEMANAL & CONCLUSIÓN EN TEXTO ---
            if len(df) >= 7:
                # Promedio de los 7 días anteriores a esta semana
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
                diff_semanal = 0.0
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

            # Promedio móvil de 7 días para suavizar fluctuaciones de agua/comida
            df["Promedio Móvil"] = df["Peso (kg)"].rolling(window=7, min_periods=1).mean()

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
# MÓDULO 3: PLAN DE LICUADOS DE LUNES A JUEVES (5:10 AM)
# ==========================================
elif opcion == "🥤 Licuados 5:00 AM (L-J)":
    st.header("🥤 Planificador de Licuados para el Despertar (5:10 AM)")
    st.write(
        "Genera un menú práctico de licuados para tus días de trabajo (Lunes a Jueves). "
        "Están diseñados para romper el ayuno, darte energía y evitar llegar con hambre a tu desayuno de las 7:30 AM."
    )

    frutas_disponibles = st.text_input(
        "🍎 Frutas disponibles en casa esta semana:",
        "Manzana, papaya, fresas congeladas, peras, plátano",
    )

    base_liquida = st.multiselect(
        "🥛 Bases, semillas y agregados disponibles:",
        [
            "Leche de almendra",
            "Leche entera",
            "Leche deslactosada",
            "Yogurt griego",
            "Nueces",
            "Almendras",
            "Cacahuates",
            "Crema de cacahuate",
            "Semillas de chía/linaza",
            "Proteína en polvo",
        ],
        default=["Leche deslactosada", "Nueces", "Almendras"]
    )

    if st.button("🥤 Generar Plan de Licuados (Lunes a Jueves)"):
        try:
            prompt = f"""
            Actúa como un Nutriólogo Experto. Crea un plan de 4 LICUADOS DIFERENTES (de Lunes a Jueves) para consumir al despertar (5:10 AM).
            
            OBJETIVO:
            Brindar energía rápida, fácil digestión y evitar llegar con hambre feroz al desayuno de las 7:30 AM en la oficina.
            
            PORCIONES STRICTAS DE 'AL DESPERTAR':
            - 1 Porción de Lácteo/Base
            - 1 Porción de Grasa con Proteína (semillas, frutos secos, crema de cacahuate/almendra)
            - 1 Porción de Fruta
            
            INGREDIENTES DISPONIBLES:
            - Frutas: {frutas_disponibles}
            - Bases/Semillas: {', '.join(base_liquida)}
            
            FORMATO DE RESPUESTA REQUERIDO (Markdown):
            Presenta una lista clara estructurada por días:
            - 📌 **Lunes / Martes / Miércoles / Jueves**
            - 🥣 **Ingredientes y cantidades exactas**
            - 💡 **Beneficio matutino**
            """

            with st.spinner("Diseñando tus licuados de la semana..."):
                response = client.models.generate_content(
                    model="gemini-3.6-flash", contents=prompt
                )
                plan_licuados = response.text

            st.session_state["plan_licuados_texto"] = plan_licuados

        except Exception as e:
            st.error(f"Error al conectar con Gemini: {e}")

    if "plan_licuados_texto" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["plan_licuados_texto"])

        if st.button("🛒 Agregar ingredientes de licuados a la Lista de Compras"):
            st.session_state.lista_compras.append(
                f"Ingredientes para licuados (L-J): {frutas_disponibles}"
            )
            st.success("¡Ingredientes añadidos a la lista de compras!")

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
    # PESTAÑA 2: REGISTRO POR CALORÍAS Y REPETIR COMIDAS
    # ----------------------------------------------------
    with tab_frecuentes:
        st.subheader("⚡ Registro por Calorías y Comidas Frecuentes")
        st.caption("Ideal para días libres o para repetir platillos habituales con un solo clic.")

        if "comidas_frecuentes" not in st.session_state:
            st.session_state.comidas_frecuentes = [
                {"Nombre": "Licuado de plátano + avena", "Tipo": "Desayuno", "Kcal": 450, "Prot": 22},
                {"Nombre": "Pechuga + Arroz + Verduras", "Tipo": "Comida", "Kcal": 550, "Prot": 45},
            ]

        if "diario_alimentos" not in st.session_state:
            st.session_state.diario_alimentos = pd.DataFrame(
                columns=["Comida", "Alimento", "Kcal", "Proteína (g)"]
            )

        # Botones de Carga Rápida (Corregido con compatibilidad de llaves)
        st.markdown("##### 🔁 Repetir Comida Habitual")
        cols_frec = st.columns(len(st.session_state.comidas_frecuentes))
        for idx, item in enumerate(st.session_state.comidas_frecuentes):
            with cols_frec[idx]:
                # Extraer proteína de manera segura soporte 'Prot' o 'Proteína (g)'
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

        # Registro Manual
        col_f1, col_f2 = st.columns([1, 1])
        with col_f1:
            st.markdown("##### 📝 Registro Manual")
            cat = st.selectbox("Categoría", ["Desayuno", "Comida", "Cena", "Snack"])
            nom = st.text_input("Nombre del alimento", placeholder="Ej. Ensalada de pollo")
            kc = st.number_input("Calorías (kcal)", min_value=0, value=350)
            pr = st.number_input("Proteína (g)", min_value=0, value=25)

            if st.button("📌 Guardar en Diario", use_container_width=True):
                if nom.strip() != "":
                    nuevo_m = pd.DataFrame([{"Comida": cat, "Alimento": nom, "Kcal": kc, "Proteína (g)": pr}])
                    st.session_state.diario_alimentos = pd.concat(
                        [st.session_state.diario_alimentos, nuevo_m], ignore_index=True
                    )
                    st.success("¡Alimento registrado!")
                    st.rerun()

        with col_f2:
            st.markdown("##### 📊 Consumo de Hoy")
            tot_k = st.session_state.diario_alimentos["Kcal"].sum()
            tot_p = st.session_state.diario_alimentos["Proteína (g)"].sum()

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
            },  # Puente ligero (10:30 AM) para aguantar a la Comida (12:00 PM)
            "Comida": {
                "Verduras": 1,
                "Cereales": 3,
                "AOA (Proteína)": 4,
                "Grasas s/ Prot": 2,
            },  # Comida de las 12:00 PM
            "Colación 2": {
                "Frutas": 1,
                "Grasas c/ Prot": 1,
                "AOA (Proteína)": 1,
            },  # Refuerzo denso (4:30 PM) para aguantar hasta la Cena (8:00 PM)
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

    # 5. GENERACIÓN CON GEMINI 3.6
    if st.button("🍳 Generar Plan / Guía de Alimentación"):
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
               El usuario suele experimentar picos de hambre a las 5:00 PM y recurrir a pan dulce/galletas por falta de saciedad y practicidad.
               La Colación 2 (4:30 PM) DEBE ser highly portable (fácil de comer en oficina o trayecto) y combinar carbohidratos de lenta absorción, 
               grasa saludable y proteína (ej. fruta con crema de cacahuate/semillas, yogurt griego con frutos secos, o tostadas horneadas saladas).
               Debe estar diseñada explícitamente para erradicar el deseo de comprar ultraprocesados antes de llegar a la cena.

            2. GRASAS SALUDABLES: Usar únicamente Aceite de Oliva Extra Virgen, Aceite de Aguacate o Spray. Prohibidos aceites refinados.
            3. COCINADO: Priorizar métodos como plancha, vapor, horno, empapelado o air fryer. Evitar aderezos comerciales.
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
                - EXCLUIR: {alimentos_no_gustan}

                {reglas_prompt}

                INSTRUCCIONES:
                1. Presenta un cronograma por horas de cada tiempo de comida.
                2. Para la Colación de las {hora_col2.strftime('%I:%M %p')}, redacta una opción saciante y portable (Fruta + Grasa con Proteína + AOA) que evite llegar con hambre o antojo de pan dulce antes de la cena ({hora_cena.strftime('%I:%M %p')}).
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

            with st.spinner("Optimizando plan de saciedad con Gemini..."):
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