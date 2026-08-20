from google import genai
import pandas as pd
import plotly.express as px
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="NutriTrack & Recetas", page_icon="🥗", layout="wide"
)

st.title("🥗 NutriTrack & Generador de Recetas")
st.write("Lleva el control de tu progreso físico y transforma tus porciones en recetas reales.")

# Inicializar cliente de Gemini usando el Secret de Streamlit
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

# --- MENÚ PRINCIPAL DE NAVEGACIÓN ---
opcion = st.sidebar.radio(
    "Selecciona una sección:",
    ["📊 Control de Peso y Músculo", "🍳 Generador de Recetas", "🛒 Lista de Compras"],
)

# Inicializar bases de datos simples en la sesión de Streamlit
if "registro_progreso" not in st.session_state:
    st.session_state.registro_progreso = pd.DataFrame(
        columns=["Fecha", "Peso (kg)", "Músculo (%)", "Grasa (%)"]
    )

if "lista_compras" not in st.session_state:
    st.session_state.lista_compras = []

# ==========================================
# MÓDULO 1: CONTROL DE PESO, METAS Y COMPOSICIÓN CORPORAL
# ==========================================
if opcion == "📊 Control de Peso y Músculo":
    st.header("📊 Registro, Diagnóstico y Meta de Peso")
    st.write(
        "Define tu peso objetivo y monitorea tu progreso en tiempo real."
    )

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Ingresar Mediciones y Meta")
        fecha = st.date_input("Fecha")
        genero = st.selectbox("Género", ["Hombre", "Mujer"])
        edad = st.number_input("Edad", min_value=10, max_value=120, value=28)
        estatura_cm = st.number_input(
            "Estatura (cm)", min_value=100.0, max_value=250.0, value=170.0, step=1.0
        )
        peso = st.number_input(
            "Peso actual (kg)", min_value=30.0, max_value=200.0, value=84.0, step=0.1
        )
        peso_meta = st.number_input(
            "🎯 Peso Meta (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1
        )
        actividad = st.selectbox(
            "Nivel de Actividad Física",
            [
                "Sedentario (Poco o ningún ejercicio)",
                "Lijero (Ejercicio 1-3 días/semana)",
                "Moderado (Ejercicio 3-5 días/semana)",
                "Fuerte (Ejercicio 6-7 días/semana)",
            ],
        )

        # 1. CÁLCULO DE IMC Y DIAGNÓSTICO
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

        # 2. CÁLCULO DE GRASA Y MÚSCULO (Deurenberg)
        val_genero = 1 if genero == "Hombre" else 0
        pct_grasa = (1.20 * imc) + (0.23 * edad) - (10.8 * val_genero) - 5.4
        pct_grasa = max(5.0, min(pct_grasa, 60.0))
        pct_musculo = 100.0 - pct_grasa

        # 3. CÁLCULO DE AVANCE Y METAS
        kilos_faltantes = peso - peso_meta
        
        # 4. CÁLCULO DE CALORÍAS (Mifflin-St Jeor)
        if genero == "Hombre":
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) + 5
        else:
            tmb = (10 * peso) + (6.25 * estatura_cm) - (5 * edad) - 161

        mult_act = {
            "Sedentario (Poco o ningún ejercicio)": 1.2,
            "Lijero (Ejercicio 1-3 días/semana)": 1.375,
            "Moderado (Ejercicio 3-5 días/semana)": 1.55,
            "Fuerte (Ejercicio 6-7 días/semana)": 1.725,
        }
        tdee = tmb * mult_act[actividad]
        meta_deficit = tdee * 0.80  # Déficit del 20%

        # DESPLEGAR RESULTADOS Y DIAGNÓSTICO
        st.markdown("---")
        st.markdown("#### 📐 Estado Actual:")

        if color_diag == "success":
            st.success(f"**Diagnóstico IMC:** {diagnostico_imc} ({imc:.1f})")
        elif color_diag == "warning":
            st.warning(f"**Diagnóstico IMC:** {diagnostico_imc} ({imc:.1f})")
        else:
            st.error(f"**Diagnóstico IMC:** {diagnostico_imc} ({imc:.1f})")

        # Tarjetas de progreso hacia la meta
        c_k1, c_k2 = st.columns(2)
        c_k1.metric("Peso Meta", f"{peso_meta:.1f} kg")
        if kilos_faltantes > 0:
            c_k2.metric("Kilos por bajar", f"{kilos_faltantes:.1f} kg", delta=f"-{kilos_faltantes:.1f} kg", delta_color="inverse")
        elif kilos_faltantes == 0:
            c_k2.metric("Estatus", "¡Meta alcanzada! 🎉")
        else:
            c_k2.metric("Estatus", f"Por debajo de la meta ({abs(kilos_faltantes):.1f} kg)")

        c_m1, c_m2 = st.columns(2)
        c_m1.metric("% Grasa Estimada", f"{pct_grasa:.1f}%")
        c_m2.metric("% Masa Magra", f"{pct_musculo:.1f}%")

        st.info(
            f"🎯 **Meta Calórica Diaria (-20%):** {int(meta_deficit)} kcal/día"
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
        
        # BARRA DE PROGRESO VISUAL SI HAY AL MENOS UN REGISTRO HISTÓRICO
        if not st.session_state.registro_progreso.empty:
            # Obtener el primer peso registrado para calcular el progreso total acumulado
            peso_inicial = st.session_state.registro_progreso.iloc[0]["Peso (kg)"]
            peso_actual = st.session_state.registro_progreso.iloc[-1]["Peso (kg)"]
            
            total_a_bajar = peso_inicial - peso_meta
            bajado_hasta_ahora = peso_inicial - peso_actual

            if total_a_bajar > 0:
                porcentaje_avance = min(1.0, max(0.0, bajado_hasta_ahora / total_a_bajar))
                st.write(f"**Progreso de pérdida de peso:** {int(porcentaje_avance * 100)}%")
                st.progress(porcentaje_avance)
            
            st.dataframe(
                st.session_state.registro_progreso, use_container_width=True
            )

            # Gráfica interactiva con línea de meta
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
# MÓDULO 2: GENERADOR DE RECETAS POR PORCIONES
# ==========================================
elif opcion == "🍳 Generador de Recetas":
    st.header("🍳 Generador de Recetas según tu Hoja de Porciones")
    st.write(
        "Ingresa los equivalentes/porciones que te asignó tu nutrióloga para crear una receta fácil y deliciosa."
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        p_prot = st.number_input("Porciones Proteína", min_value=0, value=2)
    with c2:
        p_carb = st.number_input("Porciones Carbohidratos", min_value=0, value=2)
    with c3:
        p_gras = st.number_input("Porciones Grasa", min_value=0, value=1)
    with c4:
        p_verd = st.number_input("Porciones Verdura", min_value=0, value=2)

    ingredientes_disponibles = st.text_input(
        "Ingredientes que tienes en casa (separados por coma):",
        "Pollo, tortillas de maíz, aguacate, jitomate, cebolla",
    )
    tiempo_comida = st.selectbox("Tiempo de comida:", ["Desayuno", "Almuerzo", "Cena", "Snack"])

    if st.button("🍳 Crear Receta Personalizada"):
        try:
            prompt = f"""
            Actúa como un Chef y Nutriólogo Experto. Crea una receta deliciosa, sencilla de cocinar y práctica para el tiempo de comida '{tiempo_comida}'.
            
            ESPECIFICACIONES DE PORCIONES ESTRICTAS (Hoja de Nutrióloga):
            - Proteína: {p_prot} porciones
            - Carbohidratos: {p_carb} porciones
            - Grasa: {p_gras} porciones
            - Verduras: {p_verd} porciones
            
            Ingredientes disponibles preferentes: {ingredientes_disponibles}.
            
            Responde en formato Markdown claro con las siguientes secciones:
            1. 📌 **Nombre del Platillo**
            2. 🥗 **Desglose de Ingredientes con cantidades exactas para cumplir las porciones**
            3. 👩‍🍳 **Pasos de Preparación rápidos (máximo 5 pasos)**
            4. 💡 **Tip del Chef para mejor sabor sin añadir calorías extra**
            """

            with st.spinner("Diseñando tu receta según tus porciones..."):
                response = client.models.generate_content(
                    model="gemini-2.5-flash", contents=prompt
                )
                receta_texto = response.text

            st.markdown("---")
            st.markdown(receta_texto)

            if st.button("➕ Agregar ingredientes a la Lista de Compras"):
                st.session_state.lista_compras.append(
                    f"Ingredientes para receta de {tiempo_comida} ({p_prot}"
                    f" Prot, {p_carb} Carb, {p_gras} Gras)"
                )
                st.success("¡Agregado a tu lista de compras!")

        except Exception as e:
            st.error(
                "Ocurrió un error al conectar con Gemini. Revisa que el"
                f" Secret GEMINI_API_KEY esté bien configurado. Detalles: {e}"
            )

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
            st.experimental_rerun()
    else:
        st.info("Tu lista de compras está vacía.")
