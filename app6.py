import streamlit as st
import google.generativeai as genai
import json
import random
import time

# --- Configuración de la Página y API Key ---
st.set_page_config(
    page_title="Quiz para practicar", # Título actualizado
    page_icon="💡", # Icono actualizado
    layout="centered"
)

# Cargar la API Key (sin cambios)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    API_KEY_CONFIGURED = True
except (KeyError, FileNotFoundError):
    st.error("🚨 Error: API Key de Google AI no encontrada.")
    st.error("Por favor, añade tu API Key de Google AI en el archivo `.streamlit/secrets.toml`.")
    st.markdown("Obtén tu clave en [Google AI Studio](https://aistudio.google.com/app/apikey).")
    st.markdown("El archivo `secrets.toml` debe contener:")
    st.code("""
GOOGLE_API_KEY="TU_CLAVE_AQUI"
    """)
    API_KEY_CONFIGURED = False
    st.stop()

# --- Modelo de IA y Configuraciones --- (sin cambios)
# Usamos gemini-1.5-flash para mejor rendimiento y capacidad de seguir instrucciones.
# Asegúrate de que tu API Key tenga acceso a este modelo si usas una gratuita.
# Si no, puedes probar con gemini-1.0-pro, aunque puede ser menos consistente con JSON.
model = genai.GenerativeModel(
    model_name="gemini-2.0-flash-lite-001", # Usando gemini-1.5-flash
    generation_config={
        "response_mime_type": "application/json",
        "temperature": 1 # Añadir temperatura para algo de variabilidad
    },
    safety_settings=[ # Añadir settings de seguridad si es necesario
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
)

# --- Funciones ---

def generate_crypto_question_google():
    """Llama a la API de Google Gemini para generar una pregunta con explicación."""
    prompt = f"""
        Genera una única pregunta de quiz sobre los Fundamentos de la teoría de conjuntos (conjuntos por comprensión, conjuntos por extensión, inclusión).
        La pregunta debe venir acompañada con un escenario teórico (máximo 1-2 párrafos) relacionado con la pregunta. 
        La pregunta debe ser de tipo selección múltiple ('mc') con 5 opciones.
        Responde ÚNICAMENTE con un objeto JSON válido que se adhiera ESTRICTAMENTE al siguiente formato, sin texto adicional antes o después del JSON.

        Formato Requerido:
        {{
          "question": "Escenario teórico y, seguido de un salto de línea, Texto de la pregunta (en negritas)",
          "type": "mc" | "tf",
          "options": ["Opción A", "Opción B", "Opción Correcta", "Opción D", "Opcion E"],
          "answer": "Texto de la Opción Correcta",
          "difficulty": "Fácil" | "Intermedio" | "Difícil",
          "explanation": "Explicación detallada (2-4 frases) de por qué la respuesta es correcta y, opcionalmente, contexto relevante o por qué las otras opciones son incorrectas."
        }}

        Asegúrate de que para 'mc', el valor de 'answer' sea la respuesta correcta y coincida exactamente con uno de los strings en el array 'options'.
        La explicación debe ser clara, concisa y educacional.
        La pregunta debe ser totalmente diferente a las preguntas generadas anteriormente en esta sesión de quiz. Si es similar, debes generar otra. 
        Preguntas ya usadas (últimas 10 para contexto): {list(st.session_state.get('asked_questions_set', set()))[-10:]}
    """
    try:
        # st.write("... Llamando a Google AI para pregunta+explicación ...") # Debug
        response = model.generate_content(prompt)
        json_text = response.text

        # --- Robustecer la limpieza del JSON ---
        # A veces, el modelo puede añadir caracteres extra. Intentamos limpiarlo.
        json_text = json_text.strip()
        if json_text.startswith("```json"):
            json_text = json_text[7:].strip()
        if json_text.endswith("```"):
            json_text = json_text[:-3].strip()
        # --- Fin limpieza ---

        question_data = json.loads(json_text)

        # <<< MODIFICADO: Validación para incluir 'explanation' >>>
        required_keys = ["question", "type", "options", "answer", "difficulty", "explanation"]
        if not all(key in question_data for key in required_keys):
            # Intentar obtener más info del error si es posible
            missing_keys = [key for key in required_keys if key not in question_data]
            raise ValueError(f"JSON generado no contiene todas las claves requeridas. Faltan: {missing_keys}")
        # Resto de validaciones (sin cambios)
        if not isinstance(question_data["options"], list):
             raise ValueError("El campo 'options' debe ser una lista.")
        if question_data["type"] == "mc" and question_data["answer"] not in question_data["options"]:
             raise ValueError("La respuesta ('answer') no está en las opciones ('options') para tipo 'mc'.")
        if question_data["type"] == "tf" and question_data["answer"] not in ["Verdadero", "Falso"]:
             raise ValueError("La respuesta ('answer') debe ser 'Verdadero' o 'Falso' para tipo 'tf'.")
        # Validación mejorada para explicación
        explanation = question_data.get("explanation", "")
        if not isinstance(explanation, str) or len(explanation) < 20: # Aumentar longitud mínima
             st.warning(f"La explicación generada parece muy corta o inválida ({len(explanation)} caracteres).")
             # Podríamos intentar regenerar si es crítica, pero por ahora solo avisamos.
             # Optionally, set a default explanation if too short:
             # question_data['explanation'] = "Explicación no disponible o demasiado corta."


        if question_data["type"] == 'mc':
             random.shuffle(question_data["options"])

        return question_data

    except json.JSONDecodeError as e:
        st.error(f"😥 Error al decodificar JSON de la IA: {e}")
        st.text_area("Texto recibido (para depuración):", json_text, height=150) # Mostrar el texto recibido
        try: st.text_area("Detalles del Response (si disponibles):", str(response), height=100) # type: ignore
        except: pass
        return None
    except ValueError as e:
        st.error(f"😥 Error de validación en JSON generado: {e}")
        try: st.json(question_data) # type: ignore # Mostrar el JSON (si existe)
        except: st.text_area("Datos generados (no JSON válido):", str(question_data))
        return None
    except Exception as e:
        st.error(f"😥 Error general al generar pregunta con Google AI: {e}")
        try: st.error(f"Detalles adicionales: {response.prompt_feedback}") # type: ignore
        except: pass
        return None

# --- Inicialización del Estado de la Sesión ---
if 'current_question' not in st.session_state:
    st.session_state.current_question = None
    st.session_state.question_requested = False
    st.session_state.user_answer = None
    st.session_state.submitted = False
    st.session_state.feedback = None
    st.session_state.correct_count = 0
    st.session_state.total_questions = 0 # Number of questions answered so far
    st.session_state.max_questions = 10 # <<< NUEVO: Total de preguntas en el quiz
    st.session_state.quiz_finished = False # <<< NUEVO: Bandera para saber si el quiz terminó
    st.session_state.asked_questions_set = set() # To keep track of questions asked in this session

# --- Diseño de la Interfaz ---
with st.container():
    st.title("Quiz para practicar") # Título actualizado
    st.markdown(f"Responde **{st.session_state.max_questions} preguntas** aleatorias y pon a prueba tus conocimientos.") # Desc actualizada
    #st.divider()

main_interaction_area = st.container(border=True)
score_area = st.container()

# --- Lógica Principal de la App ---

# --- Display Principal (Pregunta/Feedback o Resultado Final) ---
with main_interaction_area:
    # --- Estado 1: Quiz NO terminado ---
    if not st.session_state.quiz_finished:
        # 1. Generar nueva pregunta si es necesario
        # Genera solo si no hay pregunta actual, no se ha pedido ya una, y el quiz NO ha terminado
        if st.session_state.current_question is None and not st.session_state.question_requested:
            if st.session_state.total_questions < st.session_state.max_questions: # Check if we still need questions
                st.session_state.question_requested = True
                with st.spinner("🧠 Generando pregunta única y explicación..."): # Texto spinner actualizado
                    new_question = None
                    max_attempts = 5
                    attempts = 0
                    while attempts < max_attempts:
                        attempts += 1
                        generated_data = generate_crypto_question_google()
                        if generated_data:
                            question_text = generated_data['question']
                            # Check if the question text itself has been asked before
                            if question_text not in st.session_state.asked_questions_set:
                                new_question = generated_data
                                # Add only the question text to the set to avoid large state size
                                st.session_state.asked_questions_set.add(question_text)
                                break
                            else:
                                # If question is a duplicate, wait briefly before retrying
                                time.sleep(0.5)
                        else:
                             # If generation failed completely, wait longer before retrying
                            time.sleep(1)

                    if new_question:
                        st.session_state.current_question = new_question
                        st.session_state.user_answer = None
                        st.session_state.submitted = False
                        st.session_state.feedback = None
                        st.session_state.question_requested = False
                        st.rerun() # Rerun to display the new question immediately
                    else:
                        st.error(f"❌ No se pudo generar una pregunta ÚNICA y válida después de {max_attempts} intentos.")
                        st.session_state.question_requested = False # Allow retry? Or just stop? Let's stop for now.

            # If total_questions has reached max_questions but quiz_finished is still False, transition to finish state
            elif st.session_state.total_questions == st.session_state.max_questions and not st.session_state.quiz_finished:
                 st.session_state.quiz_finished = True
                 st.session_state.current_question = None # Clear question display
                 st.session_state.user_answer = None
                 st.session_state.submitted = False
                 st.session_state.feedback = None
                 st.session_state.question_requested = False
                 st.rerun() # Rerun to display final score state


        # 2. Mostrar Pregunta/Opciones O Feedback/Explicación (Solo si hay current_question y quiz_finished is False)
        if st.session_state.current_question:
            q_data = st.session_state.current_question

            # ---- Estado: Mostrando Pregunta ----
            if not st.session_state.submitted:
                st.subheader(f"Pregunta {st.session_state.total_questions + 1} de {st.session_state.max_questions}") # Mostrar contador
                st.markdown(f"{q_data['question']}")
                st.caption(f"Dificultad: {q_data.get('difficulty', 'No especificada')}")

                options = q_data['options']
                user_answer = st.radio(
                    "Elige tu respuesta:", options, index=None,
                    key=f"q_{st.session_state.total_questions}", # Unique key for each question
                    label_visibility="collapsed"
                )
                st.session_state.user_answer = user_answer

                col1, col2, col3 = st.columns([1,2,1])
                with col2:
                    submit_button_disabled = (user_answer is None)
                    if st.button("✔️ Enviar Respuesta", disabled=submit_button_disabled, use_container_width=True):
                        st.session_state.submitted = True
                        correct_answer = q_data['answer']
                        if st.session_state.user_answer == correct_answer:
                            st.session_state.feedback = "✅ ¡Correcto!"
                            st.session_state.correct_count += 1
                        else:
                            st.session_state.feedback = f"❌ Incorrecto." # Más corto, la explicación dará detalles
                        st.session_state.total_questions += 1 # Increment answered count *after* submitting
                        st.rerun() # Rerun to show feedback and explanation

            # ---- Estado: Mostrando Feedback y Explicación ----
            elif st.session_state.submitted and st.session_state.feedback:
                # Mostrar feedback básico (Correcto/Incorrecto)
                if "✅" in st.session_state.feedback:
                    st.success(st.session_state.feedback, icon="🎉")
                else:
                    # Si es incorrecto, mostrar la respuesta correcta antes de la explicación
                    st.error(f"{st.session_state.feedback} La respuesta correcta era: **{q_data['answer']}**", icon="🤔")

                # Mostrar la Explicación
                explanation = q_data.get("explanation", "No se pudo generar una explicación para esta pregunta.")
                with st.container(border=True):
                    st.markdown(f"**Explicación:**")
                    st.markdown(explanation)

                # Botón siguiente
                col1, col2, col3 = st.columns([1,1,1])
                with col2:
                     # <<< MODIFICADO: Comprobar si hemos llegado al final >>>
                    if st.session_state.total_questions < st.session_state.max_questions:
                        # Mostrar botón "Siguiente Pregunta" si no hemos llegado al límite
                        if st.button("➡️ Siguiente Pregunta", use_container_width=True):
                            st.session_state.current_question = None # Clear current to trigger new question generation
                            st.session_state.user_answer = None
                            st.session_state.submitted = False
                            st.session_state.feedback = None
                            st.session_state.question_requested = False # Allow requesting new question
                            st.rerun()
                    else:
                        # Mostrar botón "Ver Resultados Finales" si hemos llegado al límite
                        if st.button("🏆 Ver Resultados Finales", use_container_width=True):
                            st.session_state.quiz_finished = True # Set flag to true
                            st.session_state.current_question = None # Clear question area
                            st.session_state.user_answer = None
                            st.session_state.submitted = False
                            st.session_state.feedback = None
                            # question_requested remains False
                            st.rerun()

        # Message if no question is loaded yet (initial state or generating)
        elif API_KEY_CONFIGURED and st.session_state.current_question is None and not st.session_state.question_requested:
             # This state is briefly shown before generation starts or if generation failed
             st.info("Haz click en 'Reiniciar Quiz' o espera a que se genere la primera pregunta.")

    # --- Estado 2: Quiz TERMINADO ---
    elif st.session_state.quiz_finished:
        st.subheader("🥳 ¡Quiz Terminado!")
        st.balloons() # Celebración

        final_score = st.session_state.correct_count
        total_possible = st.session_state.max_questions
        final_accuracy = (final_score / total_possible * 100) if total_possible > 0 else 0

        st.markdown(f"Has completado las {total_possible} preguntas.")
        st.markdown(f"Tu resultado final es:")

        col_score, col_accuracy = st.columns(2)
        with col_score:
            st.metric("Aciertos", final_score, delta_color="normal") # delta_color="off" or "normal"
        with col_accuracy:
             st.metric("Porcentaje de Aciertos", f"{final_accuracy:.1f}%", delta_color="normal")


        st.markdown("¿Quieres intentarlo de nuevo?")

        # Botón para Reiniciar el Quiz
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            if st.button("🔁 Reiniciar Quiz", use_container_width=True):
                # Reset ALL relevant session state variables to initial state
                st.session_state.current_question = None
                st.session_state.question_requested = False
                st.session_state.user_answer = None
                st.session_state.submitted = False
                st.session_state.feedback = None
                st.session_state.correct_count = 0
                st.session_state.total_questions = 0
                # st.session_state.max_questions stays 10
                st.session_state.quiz_finished = False
                st.session_state.asked_questions_set = set() # Clear history for a fresh start!
                st.rerun() # Rerun to start the quiz over


# 3. Mostrar Marcador (visible durante el quiz)
with score_area:
     #st.divider() # Optional separator
     # Only show score area if quiz is not finished
     if not st.session_state.quiz_finished:
         col1, col2 = st.columns(2)
         with col1:
             # Show current progress towards max questions
             st.metric("Preguntas Contestadas", f"{st.session_state.total_questions} / {st.session_state.max_questions}")
         with col2:
             accuracy = (st.session_state.correct_count / st.session_state.total_questions * 100) if st.session_state.total_questions > 0 else 0
             st.metric("Aciertos", f"{st.session_state.correct_count}", f"{accuracy:.1f}%")
         # st.caption(f"Preguntas únicas generadas (sesión): {len(st.session_state.get('asked_questions_set', set()))}") # Optional debug metric

# --- Footer --- (sin cambios)
st.caption("Aplicación creada usando la librería Streamlit de Python y la API de Google AI Studio (Gemini).")
