import pandas as pd
import plotly.express as px
import streamlit as st
from google import genai

import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai

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
            
            # --- 1. MÉTIRCAS BÁSICAS Y EXTREMOS ---
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
# MÓDULO 4: REGISTRO DE ALIMENTACIÓN Y MACROS
# ==========================================
elif opcion == "🥗 Registro de Alimentación":
    st.header("🥗 Registro de Alimentación Diario")
    st.write("Registra tus alimentos del día o selecciona tus **Comidas Frecuentes** para ahorrar tiempo.")

    # Inicializar estado para comidas frecuentes y registro del día
    if "comidas_frecuentes" not in st.session_state:
        st.session_state.comidas_frecuentes = [
            {
                "Nombre": "Licuado de plátano + avena + leche",
                "Tipo": "Desayuno",
                "Kcal": 450,
                "Proteína (g)": 22,
                "Carbs (g)": 65,
                "Grasa (g)": 8,
            },
            {
                "Nombre": "Pechuga a la plancha con arroz y verdura",
                "Tipo": "Comida",
                "Kcal": 550,
                "Proteína (g)": 45,
                "Carbs (g)": 50,
                "Grasa (g)": 10,
            },
        ]

    if "diario_alimentos" not in st.session_state:
        st.session_state.diario_alimentos = pd.DataFrame(
            columns=["Hora/Comida", "Alimento", "Kcal", "Proteína (g)", "Carbs (g)", "Grasa (g)"]
        )

    # --- SECCIÓN: BOTÓN RÁPIDO "REPETIR COMIDA FRECUENTE" ---
    st.subheader("⚡ Carga Rápida: Comidas Frecuentes")
    st.caption("Toca 'Repetir' para añadir tus platos habituales al registro de hoy sin volver a escribir.")

    cols_frec = st.columns(len(st.session_state.comidas_frecuentes))
    for idx, item in enumerate(st.session_state.comidas_frecuentes):
        with cols_frec[idx]:
            st.markdown(f"**{item['Tipo']}:** {item['Nombre']}")
            st.caption(f"🔥 {item['Kcal']} kcal | 🥗 {item['Proteína (g)']}g Prot")
            if st.button(f"🔁 Repetir", key=f"frec_{idx}", use_container_width=True):
                nueva_comida = pd.DataFrame([{
                    "Hora/Comida": item['Tipo'],
                    "Alimento": item['Nombre'],
                    "Kcal": item['Kcal'],
                    "Proteína (g)": item['Proteína (g)'],
                    "Carbs (g)": item['Carbs (g)'],
                    "Grasa (g)": item['Grasa (g)'],
                }])
                st.session_state.diario_alimentos = pd.concat(
                    [st.session_state.diario_alimentos, nueva_comida], ignore_index=True
                )
                st.success(f"¡{item['Nombre']} añadido a hoy!")

    st.markdown("---")

    col_form, col_resumen = st.columns([1.1, 1.9])

    # --- FORMULARIO DE REGISTRO MANUAL O CREACIÓN ---
    with col_form:
        st.subheader("📝 Registrar Nuevo Alimento")
        categoria = st.selectbox("Comida", ["Desayuno", "Comida", "Cena", "Snack"])
        nombre_alimento = st.text_input("Alimento / Platillo", placeholder="Ej. Licuado de plátano")
        porcion = st.text_input("Porción", placeholder="Ej. 1 vaso / 200g")
        
        c_k, c_p = st.columns(2)
        kcal = c_k.number_input("Calorías (kcal)", min_value=0, value=300)
        prot = c_p.number_input("Proteína (g)", min_value=0, value=15)
        
        c_c, c_g = st.columns(2)
        carbs = c_c.number_input("Carbohidratos (g)", min_value=0, value=40)
        grasa = c_g.number_input("Grasas (g)", min_value=0, value=5)

        guardar_frecuente = st.checkbox("⭐ Guardar en 'Comidas Frecuentes'")

        if st.button("📌 Añadir a Hoy", use_container_width=True):
            if nombre_alimento.strip() != "":
                nuevo_item = pd.DataFrame([{
                    "Hora/Comida": categoria,
                    "Alimento": f"{nombre_alimento} ({porcion})" if porcion else nombre_alimento,
                    "Kcal": kcal,
                    "Proteína (g)": prot,
                    "Carbs (g)": carbs,
                    "Grasa (g)": grasa,
                }])
                st.session_state.diario_alimentos = pd.concat(
                    [st.session_state.diario_alimentos, nuevo_item], ignore_index=True
                )

                if guardar_frecuente:
                    st.session_state.comidas_frecuentes.append({
                        "Nombre": nombre_alimento,
                        "Tipo": categoria,
                        "Kcal": kcal,
                        "Proteína (g)": prot,
                        "Carbs (g)": carbs,
                        "Grasa (g)": grasa,
                    })
                st.success("¡Alimento registrado!")
                st.rerun()

    # --- RESUMEN Y MACRONUTRIENTES DEL DÍA ---
    with col_resumen:
        st.subheader("📊 Totales del Día")

        tot_kcal = st.session_state.diario_alimentos["Kcal"].sum()
        tot_prot = st.session_state.diario_alimentos["Proteína (g)"].sum()
        tot_carbs = st.session_state.diario_alimentos["Carbs (g)"].sum()
        tot_grasa = st.session_state.diario_alimentos["Grasa (g)"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🔥 Calorías", f"{tot_kcal} kcal")
        m2.metric("🥗 Proteínas", f"{tot_prot} g")
        m3.metric("🍞 Carbs", f"{tot_carbs} g")
        m4.metric("🥑 Grasas", f"{tot_grasa} g")

        st.markdown("##### 🍽️ Consumo Registrado Hoy")
        if not st.session_state.diario_alimentos.empty:
            st.dataframe(st.session_state.diario_alimentos, use_container_width=True)
            if st.button("🗑️ Borrar Diario de Hoy"):
                st.session_state.diario_alimentos = pd.DataFrame(
                    columns=["Hora/Comida", "Alimento", "Kcal", "Proteína (g)", "Carbs (g)", "Grasa (g)"]
                )
                st.rerun()
        else:
            st.info("Aún no has registrado ningún alimento el día de hoy.")

# ==========================================
# MÓDULO 5: GENERADOR DE RECETAS SEGÚN PLAN NUTRICIONAL
# ==========================================
elif opcion == "🍳 Generador de Recetas":
    st.header("🍳 Generador de Recetas según tu Plan Nutricional")
    st.write(
        "Configura tus horarios y porciones exactas para recibir recetas"
        " personalizadas según tu día."
    )

    PLAN_NUTRICIONAL = {
        "Al despertar": {
            "Lácteos": 1,
            "Grasas c/ Prot": 1,
            "Sugerencia Horario": "5:10 AM (Licuado ligero)",
        },
        "Desayuno": {
            "Verduras": 1,
            "Frutas": 1,
            "Cereales": 2,
            "AOA (Proteína)": 2.5,
            "Grasas s/ Prot": 1,
            "Sugerencia Horario": "7:30 AM (Oficina / Inicio de turno)",
        },
        "Colación 1": {
            "Frutas": 1,
            "Grasas c/ Prot": 1,
            "Sugerencia Horario": "10:30 AM (A mitad de mañana)",
        },
        "Comida": {
            "Verduras": 1,
            "Cereales": 3,
            "AOA (Proteína)": 5,
            "Grasas s/ Prot": 2,
            "Sugerencia Horario": "2:00 PM (Turno de comida)",
        },
        "Colación 2": {
            "Frutas": 1,
            "Sugerencia Horario": "5:00 PM (A mitad de tarde)",
        },
        "Cena": {
            "Verduras": 1,
            "Cereales": 3,
            "AOA (Proteína)": 2.5,
            "Grasas s/ Prot": 1,
            "Sugerencia Horario": "7:30 PM (Al regresar a casa)",
        },
    }

    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tiempo_comida = st.selectbox(
            "Selecciona el tiempo de comida:", list(PLAN_NUTRICIONAL.keys())
        )
    with col_t2:
        modalidad_trabajo = st.selectbox(
            "Modalidad de tu día:",
            [
                "Normal / En casa / Oficina",
                "🛠️ Día de Campo / Para llevar en Hielera/Tupper (Resistente al calor)",
            ],
        )

    datos_comida = PLAN_NUTRICIONAL[tiempo_comida].copy()
    sugerencia_h = datos_comida.pop("Sugerencia Horario")

    st.markdown(
        f"#### 📊 Porciones asignadas para **{tiempo_comida}** *(Horario"
        f" habitual: {sugerencia_h})*:"
    )

    cols = st.columns(len(datos_comida))
    for idx, (grupo, cant) in enumerate(datos_comida.items()):
        cols[idx].metric(grupo, f"{cant} porc.")

    st.markdown("---")
    st.subheader("⚙️ Gustos y Restricciones")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        alimentos_favoritos = st.text_input(
            "💚 Alimentos que te GUSTAN (separados por coma):",
            "Pollo, aguacate, tortillas de maíz, queso panela, jitomate, atún, plátano, avena",
        )
    with col_g2:
        alimentos_no_gustan = st.text_input(
            "❌ Alimentos que NO te gustan o evitas:",
            "Cilantro, mayonesa, pescado, calabacita",
        )

    if st.button("🍳 Generar Receta Personalizada"):
        try:
            porciones_str = ", ".join(
                [f"{cant} porción(es) de {grupo}" for grupo, cant in datos_comida.items()]
            )

            prompt = f"""
            Actúa como un Chef y Nutriólogo Experto. Crea una receta deliciosa y práctica.

            CONTEXTO DEL USUARIO:
            - Tiempo de comida: '{tiempo_comida}' (Horario sugerido: {sugerencia_h})
            - Modalidad: '{modalidad_trabajo}'. Si es día de campo, priorizar alimentos transportables e ideales para el calor de Colima.

            PORCIONES EXACTAS DE LA NUTRIÓLOGA:
            {porciones_str}.

            PREFERENCIAS PERSONALIZADAS:
            - Alimentos preferidos / disponibles: {alimentos_favoritos}.
            - Alimentos prohibidos / NO le gustan: {alimentos_no_gustan} (ESTRICTAMENTE NO INCLUIR NINGUNO DE ESTOS).

            FORMATO DE RESPUESTA REQUERIDO (En Markdown exacto):
            📌 **Nombre de la Receta**
            
            🥗 **Ingredientes y Cantidades Exactas**:
            - [Cantidad exacta] [Ingrediente 1]
            - [Cantidad exacta] [Ingrediente 2]
            
            👩‍🍳 **Pasos de Preparación**:
            1. Paso 1...
            2. Paso 2...
            
            🧊 **Tip de Empaque / Conservación**:
            [Tip específico de conservación térmica o empaque]
            """

            with st.spinner("Diseñando tu receta según tus porciones y gustos..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt
                )
                receta_texto = response.text

            st.session_state["ultima_receta"] = receta_texto
            st.session_state["receta_tiempo"] = tiempo_comida

        except Exception as e:
            st.error(f"Error al conectar con Gemini: {e}")

    if "ultima_receta" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["ultima_receta"])

        if st.button("🛒 Agregar Ingredientes a la Lista de Compras"):
            st.session_state.lista_compras.append(
                f"Receta para {st.session_state['receta_tiempo']}"
            )
            st.success("¡Receta agregada a tu lista de supermercado!")

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