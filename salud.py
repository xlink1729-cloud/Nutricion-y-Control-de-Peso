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
    "Lleva el control de tu progreso físico y transforma tus porciones en"
    " recetas reales."
)

# --- MENÚ PRINCIPAL DE NAVEGACIÓN ---
opcion = st.sidebar.radio(
    "Selecciona una sección:",
    [
        "📊 Control de Peso y Músculo",
        "🍳 Generador de Recetas",
        "🛒 Lista de Compras",
    ],
)

# Inicializar bases de datos simples en la sesión de Streamlit
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
# MÓDULO 1: CONTROL DE PESO, METAS Y COMPOSICIÓN CORPORAL
# ==========================================
if opcion == "📊 Control de Peso y Músculo":
    st.header("📊 Registro, Diagnóstico y Meta de Peso")
    st.write(
        "Define tu peso objetivo y monitorea tu progreso en tiempo real según"
        " tu nivel de actividad real."
    )

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Ingresar Mediciones y Meta")
        fecha = st.date_input("Fecha")
        genero = st.selectbox("Género", ["Hombre", "Mujer"])
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
            "🎯 Peso Meta (kg)",
            min_value=30.0,
            max_value=200.0,
            value=70.0,
            step=0.1,
        )

        actividad = st.selectbox(
            "Nivel de Actividad Física diario:",
            [
                "Sedentario (Oficina / Trabajo de escritorio)",
                "Ligero (Oficina + Caminata diaria ligera)",
                "Mixto 50/50 (Oficina + Trabajo de campo / Mantenimiento)",
                "Activo (Trabajo físico pesado o ejercicio diario)",
                "Muy Activo (Trabajo pesado + Ejercicio intenso)",
            ],
            index=2,
        )

        # 1. CÁLCULO DE IMC Y DIAGNÓSTICO OMS
        estatura_m = estatura_cm / 100
        imc = peso / (estatura_m**2)

        if imc < 18.5:
            diagnostico_imc = "Bajo peso"
            color_diag = "warning"
        elif 18.5 <= imc < 25.0:
            diagnostico_imc = "Peso normal / Saludable"
            color_diag = "success"
        elif 25.0 <= imc < 30.0:
            diagnostico_imc = "Sobrepeso"
            color_diag = "warning"
        elif 30.0 <= imc < 35.0:
            diagnostico_imc = "Obesidad Clase I"
            color_diag = "error"
        else:
            diagnostico_imc = "Obesidad Clase II / III"
            color_diag = "error"

        # 2. CÁLCULO DE GRASA Y MÚSCULO (Fórmula de Deurenberg)
        val_genero = 1 if genero == "Hombre" else 0
        pct_grasa = (1.20 * imc) + (0.23 * edad) - (10.8 * val_genero) - 5.4
        pct_grasa = max(5.0, min(pct_grasa, 60.0))
        pct_musculo = 100.0 - pct_grasa

        # 3. CÁLCULO DE KILOS RESTANTES
        kilos_faltantes = peso - peso_meta

        # 4. CÁLCULO DE CALORÍAS (Mifflin-St Jeor + Factor Actividad)
        mult_act = {
            "Sedentario (Oficina / Trabajo de escritorio)": 1.2,
            "Ligero (Oficina + Caminata diaria ligera)": 1.375,
            "Mixto 50/50 (Oficina + Trabajo de campo / Mantenimiento)": 1.55,
            "Activo (Trabajo físico pesado o ejercicio diario)": 1.725,
            "Muy Activo (Trabajo pesado + Ejercicio intenso)": 1.9,
        }

        if genero == "Hombre":
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) + 5
        else:
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) - 161

        tdee = tmb * mult_act[actividad]
        meta_deficit = tdee * 0.80  # Déficit moderado del 20%

        # 5. CÁLCULO DE HIDRATACIÓN PERSONALIZADA (Ajuste Colima / Campo)
        agua_base = (peso * 35) / 1000  # Litros base por peso
        agua_oficina = agua_base + 0.5   # Litros para días de oficina en Colima
        agua_campo = agua_base + 1.2     # Litros para días de campo/calor en Colima

        # DESPLEGAR RESULTADOS Y DIAGNÓSTICO
        st.markdown("---")
        st.markdown("#### 📐 Estado Actual:")

        if color_diag == "success":
            st.success(f"**Diagnóstico IMC:** {diagnostico_imc} ({imc:.1f})")
        elif color_diag == "warning":
            st.warning(f"**Diagnóstico IMC:** {diagnostico_imc} ({imc:.1f})")
        else:
            st.error(f"**Diagnóstico IMC:** {diagnostico_imc} ({imc:.1f})")

        c_k1, c_k2 = st.columns(2)
        c_k1.metric("Peso Meta", f"{peso_meta:.1f} kg")
        if kilos_faltantes > 0:
            c_k2.metric(
                "Kilos por bajar",
                f"{kilos_faltantes:.1f} kg",
                delta=f"-{kilos_faltantes:.1f} kg",
                delta_color="inverse",
            )
        elif kilos_faltantes == 0:
            c_k2.metric("Estatus", "¡Meta alcanzada! 🎉")
        else:
            c_k2.metric(
                "Estatus", f"Por debajo de la meta ({abs(kilos_faltantes):.1f} kg)"
            )

        c_m1, c_m2 = st.columns(2)
        c_m1.metric("% Grasa Estimada", f"{pct_grasa:.1f}%")
        c_m2.metric("% Masa Magra", f"{pct_musculo:.1f}%")

        st.info(
            f"🎯 **Meta Calórica Diaria (-20%):** {int(meta_deficit)} kcal/día"
        )

        # SECCIÓN DE HIDRATACIÓN Y ELECTROLI TOS EN COLIMA
        st.markdown("---")
        st.markdown("#### 💧 Meta de Hidratación (Ajustada a Colima):")
        
        c_h1, c_h2 = st.columns(2)
        c_h1.metric("🏢 Día de Oficina", f"{agua_oficina:.1f} Litros/día")
        c_h2.metric("🛠️ Día de Campo / Mantenimiento", f"{agua_campo:.1f} Litros/día")

        st.warning(
            "💡 **Tip para el calor de Colima:** En días de campo, lleva un termo térmico de 1.5L. "
            "Si sudas mucho, añade a tu agua una pizca de sal marina y limón (o electrolitos sin azúcar) "
            "para evitar calambres y fatiga sin romper tu déficit calórico."
        )

        if st.button("💾 Guardar Registro"):
            nuevo_registro = pd.DataFrame(
                [[
                    fecha,
                    peso,
                    peso_meta,
                    round(kilos_faltantes, 1),
                    round(imc, 1),
                    diagnostico_imc,
                    round(pct_grasa, 1),
                    round(pct_musculo, 1),
                    int(meta_deficit),
                ]],
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
                ],
            )
            st.session_state.registro_progreso = pd.concat(
                [st.session_state.registro_progreso, nuevo_registro],
                ignore_index=True,
            )
            st.success("¡Registro guardado con éxito!")

    with col2:
        st.subheader("Tu Histórico y Progreso hacia la Meta")

        if not st.session_state.registro_progreso.empty:
            peso_inicial = st.session_state.registro_progreso.iloc[0]["Peso (kg)"]
            peso_actual = st.session_state.registro_progreso.iloc[-1]["Peso (kg)"]

            total_a_bajar = peso_inicial - peso_meta
            bajado_hasta_ahora = peso_inicial - peso_actual

            if total_a_bajar > 0:
                porcentaje_avance = min(
                    1.0, max(0.0, bajado_hasta_ahora / total_a_bajar)
                )
                st.write(
                    f"**Progreso de pérdida de peso:** {int(porcentaje_avance * 100)}%"
                )
                st.progress(porcentaje_avance)

            st.dataframe(
                st.session_state.registro_progreso, use_container_width=True
            )

            fig = px.line(
                st.session_state.registro_progreso,
                x="Fecha",
                y=["Peso (kg)", "Meta (kg)"],
                markers=True,
                title="Evolución del Peso vs. Peso Meta",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(
                "Aún no has añadido registros. Ingresa tus datos en el"
                " formulario de la izquierda."
            )

# ==========================================
# MÓDULO 2: GENERADOR DE RECETAS Y LICUADOS EXPRESS
# ==========================================
elif opcion == "🍳 Generador de Recetas":
    st.header("🍳 Generador de Recetas y Licuados Express")
    st.write(
        "Planifica tus comidas o genera licuados al instante al despertar según tus frutas disponibles."
    )

    # Matriz de porciones basada en la tabla de Intervención Nutricional
    PLAN_NUTRICIONAL = {
        "Al despertar (Licuado Express)": {
            "Lácteos": 1,
            "Grasas c/ Prot": 1,
            "Sugerencia Horario": "5:10 AM (Antes de salir a campo)",
        },
        "Desayuno": {
            "Verduras": 1,
            "Frutas": 1,
            "Cereales": 2,
            "AOA (Proteína)": 2.5,
            "Grasas s/ Prot": 1,
            "Sugerencia Horario": "7:00 AM (Inicio de Turno)",
        },
        "Colación 1": {
            "Frutas": 1,
            "Grasas c/ Prot": 1,
            "Sugerencia Horario": "10:30 AM",
        },
        "Comida": {
            "Verduras": 1,
            "Cereales": 3,
            "AOA (Proteína)": 5,
            "Grasas s/ Prot": 2,
            "Sugerencia Horario": "2:00 PM",
        },
        "Colación 2": {
            "Frutas": 1,
            "Sugerencia Horario": "5:00 PM",
        },
        "Cena": {
            "Verduras": 1,
            "Cereales": 3,
            "AOA (Proteína)": 2.5,
            "Grasas s/ Prot": 1,
            "Sugerencia Horario": "7:30 PM (Al terminar turno)",
        },
    }

    st.subheader("⏰ Configuración de Rutina")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tiempo_comida = st.selectbox(
            "Selecciona el tiempo de comida o licuado:", list(PLAN_NUTRICIONAL.keys())
        )
    with col_t2:
        modalidad_trabajo = st.selectbox(
            "Modalidad de tu día:",
            [
                "Normal / En casa / Oficina",
                "🛠️ Día de Campo / Para llevar en Hielera/Tupper",
            ],
        )

    # Cargar porciones automáticamente
    datos_comida = PLAN_NUTRICIONAL[tiempo_comida].copy()
    sugerencia_h = datos_comida.pop("Sugerencia Horario")

    st.markdown(f"#### 📊 Porciones para **{tiempo_comida}** *(Horario: {sugerencia_h})*:")
    cols = st.columns(len(datos_comida))
    for idx, (grupo, cant) in enumerate(datos_comida.items()):
        cols[idx].metric(grupo, f"{cant} porc.")

    st.markdown("---")

    # ENFOQUE DEDICADO PARA "AL DESPERTAR" (LICUADOS CON FRUTAS DISPONIBLES)
    if tiempo_comida == "Al despertar (Licuado Express)":
        st.subheader("🥤 Generador de Licuados Rápidos (5:10 AM)")
        frutas_disponibles = st.text_input(
            "🍓 Frutas que tienes disponibles hoy (separadas por coma):",
            "Manzana, papaya, fresas congeladas, pera, plátano",
        )
        base_liquida = st.selectbox(
            "🥛 Base para tu licuado (1 Porción de Lácteo/Sustituto):",
            ["Leche entera", "Leche descremada", "Leche de almendras", "Yogurt natural"],
        )
        grasa_saludable = st.selectbox(
            "🥜 Grasa saludable con proteína (1 Porción):",
            ["Crema de cacahuate", "Almendras (10 piezas)", "Nueces (4 mitades)", "Semillas de chía / linaza"],
        )

        if st.button("⚡ Crear Licuado Express"):
            try:
                prompt = f"""
                Actúa como un Nutriólogo Experto. Crea una combinación de licuado súper rápida (preparación en menos de 3 minutos) para el usuario que se levanta a las 5:10 AM.

                RESTRICCIONES Y ESTRUCTURA DE LA NUTRIÓLOGA:
                - 1 Porción de Lácteo: Usar {base_liquida}.
                - 1 Porción de Grasa con Proteína: Usar {grasa_saludable}.
                - Fruta: Combinar adecuadamente usando SOLO de estas opciones disponibles: {frutas_disponibles}.

                FORMATO DE RESPUESTA REQUERIDO (En Markdown exacto):
                📌 **Nombre del Licuado**
                
                🥤 **Ingredientes Exactos para la Licuadora**:
                - Cantidad exacta de {base_liquida}
                - Cantidad exacta de {grasa_saludable}
                - Cantidad/porción exacta de la(s) fruta(s) seleccionada(s)
                
                ⏱️ **Instrucciones de Preparación Express (2 pasos)**:
                1. Pasos...
                
                ⚡ **Beneficio Nutricional para tu jornada**:
                [Breve explicación del aporte de energía para arrancar el turno]
                """

                with st.spinner("Mezclando tu licuado mañanero..."):
                    response = client.models.generate_content(
                        model="gemini-2.5-flash", contents=prompt
                    )
                    receta_texto = response.text

                st.session_state["ultima_receta"] = receta_texto
                st.session_state["receta_tiempo"] = "Licuado Express 5:10 AM"

            except Exception as e:
                st.error(f"Error al conectar con Gemini: {e}")

    # ENFOQUE ESTÁNDAR PARA OTRAS COMIDAS (DESAYUNO, COMIDA, CENA)
    else:
        st.subheader("⚙️ Gustos y Restricciones")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            alimentos_favoritos = st.text_input(
                "💚 Alimentos que te GUSTAN (separados por coma):",
                "Pollo, aguacate, tortillas de maíz, queso panela, jitomate, atún",
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
                Actúa como un Chef y Nutriólogo Experto. Crea una receta adaptada a las porciones exactas.

                TIEMPO DE COMIDA: '{tiempo_comida}'
                PORCIONES STRICTAS DE LA NUTRIÓLOGA: {porciones_str}.
                MODALIDAD: '{modalidad_trabajo}' (Si es día de campo, considerar resistencia al calor de Colima y empaque).

                PREFERENCIAS PERSONALIZADAS:
                - Preferidos: {alimentos_favoritos}.
                - Prohibidos: {alimentos_no_gustan}.

                FORMATO DE RESPUESTA:
                📌 **Nombre de la Receta**
                🥗 **Ingredientes y Cantidades Exactas**
                👩‍🍳 **Pasos de Preparación**
                🧊 **Tip de Empaque / Conservación**
                """

                with st.spinner("Diseñando receta..."):
                    response = client.models.generate_content(
                        model="gemini-2.5-flash", contents=prompt
                    )
                    receta_texto = response.text

                st.session_state["ultima_receta"] = receta_texto
                st.session_state["receta_tiempo"] = tiempo_comida

            except Exception as e:
                st.error(f"Error al conectar con Gemini: {e}")

    # Desplegar receta generada
    if "ultima_receta" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["ultima_receta"])

        if st.button("🛒 Agregar Ingredientes a la Lista de Compras"):
            st.session_state.lista_compras.append(
                f"Ingredientes de {st.session_state['receta_tiempo']}"
            )
            st.success("¡Ingredientes agregados a tu lista de compras!")

# ==========================================
# MÓDULO 3: LISTA DE COMPRAS
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