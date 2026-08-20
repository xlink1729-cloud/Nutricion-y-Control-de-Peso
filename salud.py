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

# --- BARRA LATERAL: API KEY ---
st.sidebar.header("🔑 Configuración")
api_key = st.sidebar.text_input("Ingresa tu Gemini API Key:", type="password")

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
# MÓDULO 1: CONTROL DE PESO Y MÚSCULO
# ==========================================
if opcion == "📊 Control de Peso y Músculo":
    st.header("📊 Registro de Peso y Masa Muscular")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Añadir nuevo registro")
        fecha = st.date_input("Fecha")
        peso = st.number_input(
            "Peso actual (kg)", min_value=30.0, max_value=200.0, value=70.0, step=0.1
        )
        musculo = st.number_input(
            "Masa muscular (%)", min_value=5.0, max_value=70.0, value=30.0, step=0.1
        )
        grasa = st.number_input(
            "Porcentaje de grasa (%)", min_value=5.0, max_value=60.0, value=20.0, step=0.1
        )

        if st.button("Guardar Registro"):
            nuevo_registro = pd.DataFrame(
                [[fecha, peso, musculo, grasa]],
                columns=["Fecha", "Peso (kg)", "Músculo (%)", "Grasa (%)"],
            )
            st.session_state.registro_progreso = pd.concat(
                [st.session_state.registro_progreso, nuevo_registro],
                ignore_index=True,
            )
            st.success("¡Registro guardado con éxito!")

    with col2:
        st.subheader("Tu Histórico y Gráfica")
        if not st.session_state.registro_progreso.empty:
            st.dataframe(st.session_state.registro_progreso, use_container_width=True)

            # Gráfica interactiva con Plotly
            fig = px.line(
                st.session_state.registro_progreso,
                x="Fecha",
                y=["Peso (kg)", "Músculo (%)", "Grasa (%)"],
                markers=True,
                title="Evolución Físico-Nutricional",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aún no has añadido registros. Ingresa tus datos en el formulario de la izquierda.")

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
        if not api_key:
            st.error("Por favor ingresa tu API Key de Gemini en la barra lateral.")
        else:
            try:
                client = genai.Client(api_key=api_key)

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

                # Opción para agregar ingredientes a la lista de compras
                if st.button("➕ Agregar ingredientes a la Lista de Compras"):
                    st.session_state.lista_compras.append(
                        f"Ingredientes para receta de {tiempo_comida} ({p_prot} Prot, {p_carb} Carb, {p_gras} Gras)"
                    )
                    st.success("¡Agregado a tu lista de compras!")

            except Exception as e:
                st.error(f"Ocurrió un error al conectar con Gemini: {e}")

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
