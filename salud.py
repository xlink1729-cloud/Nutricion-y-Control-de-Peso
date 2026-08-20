import pandas as pd
import plotly.express as px
import streamlit as st
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
        "📊 Control de Peso y Músculo",
        "🥤 Licuados 5:00 AM (L-J)",
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
            "Meta (kg)",
            "Faltan (kg)",
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
# MÓDULO 1: PERFIL INICIAL Y CONTROL DE PESO
# ==========================================
if opcion == "📊 Control de Peso y Músculo":
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
# MÓDULO 2: PLAN DE LICUADOS DE LUNES A JUEVES (5:10 AM)
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
# MÓDULO 3: GENERADOR DE RECETAS SEGÚN PLAN NUTRICIONAL
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
# MÓDULO 4: LISTA DE COMPRAS
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