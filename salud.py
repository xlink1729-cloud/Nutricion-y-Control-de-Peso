# --- CONTROL DE SESIÓN ESTILO "FINSMART CARD" ---
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    # --- CSS ESTILO TARJETA FINSMART ---
    st.markdown(
        """
        <style>
        #MainMenu, footer, header {visibility: hidden;}
        
        /* FONDO AZUL DEGRADADO DE LA PANTALLA GENERAL */
        .stApp {
            background: linear-gradient(135deg, #4b738e 0%, #2b4659 100%) !important;
            background-attachment: fixed !important;
        }
        
        /* CONTENEDOR ANCHO TIPO TARJETA */
        .main .block-container {
            max-width: 420px !important;
            padding-top: 2rem !important;
            padding-bottom: 2rem !important;
            margin: 0 auto !important;
        }

        /* TARJETA DE FONDO TIPO FINSMART */
        .login-card-bg {
            background: rgba(110, 147, 172, 0.65) !important;
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 28px !important;
            padding: 2.2rem 2rem 2.5rem 2rem !important;
            box-shadow: 0 15px 35px rgba(0, 0, 0, 0.3) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            margin-bottom: 0rem;
        }

        /* TÍTULO PRINCIPAL DENTRO DE LA TARJETA */
        .app-title-login {
            color: #ffffff !important;
            font-size: 2rem !important;
            font-weight: 800 !important;
            text-align: center !important;
            letter-spacing: 1px !important;
            margin-bottom: 1.5rem !important;
            font-family: 'sans-serif';
        }

        /* LOGO PEQUEÑO DENTRO DE LA TARJETA (SI EXISTE) */
        .logo-card-container {
            display: flex;
            justify-content: center;
            align-items: center;
            margin-bottom: 1rem;
            width: 100%;
        }
        .logo-card img {
            max-width: 140px;
            height: auto;
            display: block;
            object-fit: contain;
            border-radius: 12px;
        }

        /* PESTAÑAS (INICIAR SESIÓN / CREAR CUENTA) */
        .stTabs [data-baseweb="tab-list"] {
            gap: 15px;
            background-color: transparent !important;
            padding: 0px;
            margin-bottom: 1.5rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2) !important;
            width: 100% !important;
        }

        .stTabs [data-baseweb="tab"],
        .stTabs [data-baseweb="tab"] *,
        .stTabs [data-testid="stMarkdownContainer"] p {
            color: rgba(255, 255, 255, 0.7) !important;
            -webkit-text-fill-color: rgba(255, 255, 255, 0.7) !important;
            font-size: 0.95rem !important;
            font-weight: 600 !important;
        }

        /* PESTAÑA ACTIVA CON LÍNEA INFERIOR ROJA / NARANJA */
        .stTabs [aria-selected="true"] {
            background-color: transparent !important;
            border-bottom: 3px solid #ff5a52 !important;
            border-radius: 0px !important;
        }

        .stTabs [aria-selected="true"] *,
        .stTabs [aria-selected="true"] [data-testid="stMarkdownContainer"] p {
            color: #ff5a52 !important;
            -webkit-text-fill-color: #ff5a52 !important;
            font-weight: 700 !important;
        }

        .stTabs [data-baseweb="tab-highlight-title"],
        .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }

        /* FORMULARIO TRANSPARENTE */
        [data-testid="stForm"] {
            background: transparent !important;
            border: none !important;
            padding: 0px !important;
            box-shadow: none !important;
        }

        /* ETIQUETAS VISIBLES CON TEXTO BLANCO */
        [data-testid="stWidgetLabel"] label, 
        .stTextInput label {
            color: #ffffff !important;
            font-weight: 700 !important;
            font-size: 0.95rem !important;
            margin-bottom: 4px !important;
            display: block !important;
        }

        /* CAJAS DE TEXTO AZUL OSCURO ESTILO FINSMART */
        .stTextInput input,
        div[data-baseweb="input"] input {
            background-color: #213144 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 1px solid #1a2533 !important;
            border-radius: 10px !important;
            padding: 10px 14px !important;
            height: 44px !important;
            font-size: 0.95rem !important;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
        }

        div[data-baseweb="input"] {
            background-color: #213144 !important;
            border-radius: 10px !important;
            border: 1px solid #1a2533 !important;
        }

        .stTextInput input::placeholder {
            color: #7f94a8 !important;
            -webkit-text-fill-color: #7f94a8 !important;
        }

        /* AUTOCOMPLETADO */
        .stTextInput input:-webkit-autofill,
        .stTextInput input:-webkit-autofill:hover, 
        .stTextInput input:-webkit-autofill:focus {
            -webkit-text-fill-color: #ffffff !important;
            -webkit-box-shadow: 0 0 0px 1000px #213144 inset !important;
            transition: background-color 5000s ease-in-out 0s;
        }

        /* BOTÓN DE LOGIN EN NEGRO / AZUL MUY OSCURO */
        div.stButton > button,
        div[data-testid="stFormSubmitButton"] > button {
            width: 100% !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            letter-spacing: 1px !important;
            background: #121921 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 1px solid #000000 !important;
            height: 46px !important;
            padding: 0px 15px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4) !important;
            transition: all 0.2s ease !important;
            margin-top: 12px !important;
        }

        div.stButton > button:hover,
        div.stButton > button:focus,
        div.stButton > button:active,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:focus,
        div[data-testid="stFormSubmitButton"] > button:active {
            background: #1c2734 !important;
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
            border: 1px solid #ff5a52 !important;
            transform: translateY(-1px) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # TÍTULO SUPERIOR "VITA COACH"
    st.markdown('<div class="app-title-login">VITA COACH</div>', unsafe_allow_html=True)

    # PESTAÑAS DENTRO DE LA TARJETA
    tab_login, tab_registro, tab_recuperar = st.tabs(
        ["🔑 Iniciar Sesión", "📝 Crear Cuenta", "🔄 Recuperar"]
    )

    # 1. FORMULARIO LOGIN
    with tab_login:
        with st.form("login_form"):
            email_input = st.text_input(
                "👤 Usuario / Correo",
                placeholder="Ingresa tu usuario",
                key="login_email",
            )
            password_input = st.text_input(
                "🔒 Contraseña",
                type="password",
                placeholder="Ingresa tu contraseña",
                key="login_pass",
            )
            submit_login = st.form_submit_button(
                "LOGIN", use_container_width=True
            )

            if submit_login:
                bloqueado, segs = esta_bloqueado("login")
                if bloqueado:
                    st.error(f"Demasiados intentos fallidos. Reintenta en {segs}s.")
                else:
                    usuario_valido = verificar_usuario(email_input, password_input)
                    if usuario_valido:
                        resetear_intentos("login")
                        st.session_state.user = usuario_valido
                        st.rerun()
                    else:
                        registrar_intento_fallido("login")
                        intentos_restantes = MAX_ATTEMPTS - st.session_state.get("login_attempts", 0)
                        if intentos_restantes > 0:
                            st.error(f"Credenciales incorrectas. Intentos restantes: {intentos_restantes}")
                        else:
                            st.error(f"Límite superado. Bloqueado por {LOCKOUT_DURATION}s.")

    # 2. FORMULARIO REGISTRO
    with tab_registro:
        with st.form("registro_form"):
            nombre_nuevo = st.text_input(
                "👤 Nombre completo", placeholder="Tu nombre"
            )
            email_nuevo = st.text_input(
                "📧 Correo electrónico",
                placeholder="ejemplo@correo.com",
                key="reg_email",
            )
            password_nuevo = st.text_input(
                "🔒 Contraseña",
                type="password",
                placeholder="••••••••",
                key="reg_pass",
            )
            pin_nuevo = st.text_input(
                "🔢 PIN de seguridad (4 dígitos)",
                max_chars=4,
                type="password",
                placeholder="1234",
                key="reg_pin",
            )
            submit_registro = st.form_submit_button(
                "REGISTRARME", use_container_width=True
            )

            if submit_registro:
                bloqueado, segs = esta_bloqueado("registro")
                if bloqueado:
                    st.error(f"Límite de solicitudes. Reintenta en {segs}s.")
                else:
                    if nombre_nuevo and email_nuevo and password_nuevo and len(pin_nuevo) == 4:
                        exito, msg = registrar_nuevo_usuario(
                            nombre_nuevo, email_nuevo, password_nuevo, pin_nuevo
                        )
                        if exito:
                            resetear_intentos("registro")
                            st.success("¡Cuenta creada! Ahora puedes iniciar sesión.")
                        else:
                            registrar_intento_fallido("registro")
                            st.error(f"Error al registrar: {msg}")
                    else:
                        registrar_intento_fallido("registro")
                        st.error("Por favor completa todos los campos correctamente.")

    # 3. FORMULARIO RECUPERAR
    with tab_recuperar:
        with st.form("recuperar_form"):
            email_recuperar = st.text_input(
                "📧 Correo electrónico",
                placeholder="ejemplo@correo.com",
                key="rec_email",
            )
            pin_recuperar = st.text_input(
                "🔢 PIN de seguridad",
                max_chars=4,
                type="password",
                placeholder="1234",
                key="rec_pin",
            )
            nueva_pw = st.text_input(
                "🔒 Nueva contraseña",
                type="password",
                placeholder="••••••••",
                key="rec_pw1",
            )
            confirmar_pw = st.text_input(
                "🔒 Confirmar contraseña",
                type="password",
                placeholder="••••••••",
                key="rec_pw2",
            )
            submit_recuperar = st.form_submit_button(
                "ACTUALIZAR CONTRASEÑA", use_container_width=True
            )

            if submit_recuperar:
                bloqueado, segs = esta_bloqueado("recuperar")
                if bloqueado:
                    st.error(f"Bloqueo de seguridad activo. Reintenta en {segs}s.")
                elif nueva_pw != confirmar_pw:
                    st.error("Las contraseñas no coinciden.")
                else:
                    exito, msg = cambiar_password_db(email_recuperar, pin_recuperar, nueva_pw)
                    if exito:
                        resetear_intentos("recuperar")
                        st.success(msg)
                    else:
                        registrar_intento_fallido("recuperar")
                        st.error(msg)

    st.stop()
