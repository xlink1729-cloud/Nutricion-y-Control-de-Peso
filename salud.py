# --- CONTROL DE SESIÓN ESTILO EXACTO "MEMBER LOGIN" ---
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    # --- CSS MINIMALISTA AJUSTADO A ANCHO ESTRICTO (320px) ---
    st.markdown(
        """
        <style>
        #MainMenu, footer, header {visibility: hidden;}
        
        /* FONDO EN DEGRADADO RADIAL VERDE VIVO A VERDE OSCURO */
        .stApp {
            background: radial-gradient(circle at 50% 35%, #76a048 0%, #3e6d30 45%, #183318 100%) !important;
            background-attachment: fixed !important;
        }
        
        /* RESTRICCIÓN DE ANCHO CENTRAL PARA TODO EL CONTENIDO */
        .main .block-container {
            max-width: 340px !important;
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            margin: 0 auto !important;
        }

        /* LOGO PROPORCIONADO Y CENTRADO */
        .logo-card-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 0.8rem;
            width: 100%;
        }
        .logo-card {
            background: rgba(255, 255, 255, 0.9) !important;
            padding: 8px 12px !important;
            border-radius: 16px !important;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25) !important;
            width: 100%;
            max-width: 220px !important; /* Tamaño legible para el logo */
            text-align: center;
        }
        .logo-card img {
            width: 100%;
            height: auto;
            max-height: 110px !important;
            display: block;
            object-fit: contain;
        }

        /* PESTAÑAS (INICIAR SESIÓN / REGISTRARSE / RECUPERAR) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 6px !important;
            background-color: transparent !important;
            padding: 0px !important;
            margin-bottom: 1.2rem !important;
            border: none !important;
            justify-content: center !important;
            width: 100% !important;
        }

        .stTabs [data-baseweb="tab"],
        .stTabs [data-baseweb="tab"] *,
        .stTabs [data-testid="stMarkdownContainer"] p {
            color: rgba(255, 255, 255, 0.85) !important;
            -webkit-text-fill-color: rgba(255, 255, 255, 0.85) !important;
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.3px;
        }

        /* PESTAÑA SELECCIONADA CON SUBRAYADO BLANCO */
        .stTabs [aria-selected="true"] {
            background-color: transparent !important;
            border-bottom: 2px solid #ffffff !important;
            border-radius: 0px !important;
            box-shadow: none !important;
        }

        .stTabs [aria-selected="true"] *,
        .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            font-weight: 700 !important;
            opacity: 1 !important;
        }

        .stTabs [data-baseweb="tab-highlight-title"],
        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }

        /* FORMULARIO Y BARRAS DE TEXTO */
        [data-testid="stForm"] {
            background: transparent !important;
            border: none !important;
            padding: 0px !important;
            box-shadow: none !important;
            width: 100% !important;
        }

        /* OCULTAR ETIQUETAS SUPERIORES DE LOS CAMPOS */
        [data-testid="stWidgetLabel"] label, 
        .stTextInput label {
            display: none !important;
        }

        /* BARRAS DE TEXTO COMPACTAS REDONDEADAS (ESTILO MEMBER LOGIN) */
        .stTextInput input,
        div[data-baseweb="input"] input {
            background-color: #ffffff !important;
            color: #333333 !important;
            -webkit-text-fill-color: #333333 !important;
            border: none !important;
            border-radius: 8px !important; /* Esquinas ligeramente redondeadas como en la imagen */
            padding: 10px 16px !important;
            height: 44px !important;
            font-size: 0.95rem !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        }

        div[data-baseweb="input"] {
            border-radius: 8px !important;
            background-color: #ffffff !important;
            margin-bottom: 6px !important;
        }

        .stTextInput input::placeholder {
            color: #9E9E9E !important;
            -webkit-text-fill-color: #9E9E9E !important;
        }

        /* BOTÓN PRINCIPAL VERDE LIMA DESTACADO */
        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            border-radius: 8px !important;
            font-weight: 800 !important;
            font-size: 0.95rem !important;
            letter-spacing: 1px !important;
            background: #a6ce39 !important; /* Verde lima idéntico a la imagen */
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: none !important;
            height: 46px !important;
            padding: 0px 15px !important;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.25) !important;
            transition: all 0.2s ease !important;
            margin-top: 10px !important;
            
            -webkit-appearance: none !important;
            -moz-appearance: none !important;
            appearance: none !important;
            -webkit-tap-highlight-color: transparent !important;
        }

        div.stButton > button:hover,
        div.stButton > button:focus,
        div.stButton > button:active,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:focus,
        div[data-testid="stFormSubmitButton"] > button:active {
            background: #93b92e !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            box-shadow: 0 6px 18px rgba(0, 0, 0, 0.35) !important;
            transform: translateY(-1px) !important;
        }

        div.stButton > button *,
        div[data-testid="stFormSubmitButton"] > button * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    
    # RENDERIZADO DEL LOGO
    try:
        with open("static/vitacoach.jpg", "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()
        logo_html = f'<div class="logo-card-container"><div class="logo-card"><img src="data:image/jpeg;base64,{img_b64}" alt="VITA COACH"></div></div>'
    except Exception:
        logo_html = ""

    st.markdown(logo_html, unsafe_allow_html=True)

    tab_login, tab_registro, tab_recuperar = st.tabs(
        ["INICIAR SESIÓN", "REGISTRARSE", "RECUPERAR"]
    )

    # 1. FORMULARIO LOGIN
    with tab_login:
        with st.form("login_form"):
            email_input = st.text_input(
                "Correo electrónico",
                placeholder="email",
                key="login_email",
            )
            password_input = st.text_input(
                "Contraseña",
                type="password",
                placeholder="password",
                key="login_pass",
            )
            submit_login = st.form_submit_button(
                "SIGN IN", use_container_width=True
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
                "Nombre completo", placeholder="nombre", key="reg_nombre"
            )
            email_nuevo = st.text_input(
                "Correo electrónico",
                placeholder="email",
                key="reg_email",
            )
            password_nuevo = st.text_input(
                "Contraseña",
                type="password",
                placeholder="password",
                key="reg_pass",
            )
            pin_nuevo = st.text_input(
                "PIN de seguridad (4 dígitos)",
                max_chars=4,
                type="password",
                placeholder="PIN de 4 dígitos",
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
                placeholder="email",
                key="rec_email",
            )
            pin_recuperar = st.text_input(
                "PIN de seguridad",
                max_chars=4,
                type="password",
                placeholder="PIN",
                key="rec_pin",
            )
            nueva_pw = st.text_input(
                "Nueva contraseña",
                type="password",
                placeholder="nueva contraseña",
                key="rec_pw1",
            )
            confirmar_pw = st.text_input(
                "Confirmar contraseña",
                type="password",
                placeholder="confirmar contraseña",
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

    st.stop()
