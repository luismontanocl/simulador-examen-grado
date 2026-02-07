import os
import streamlit as st
import datetime
import docx
from PyPDF2 import PdfReader
from crewai import Agent, Task, Crew
import google.generativeai as genai

# ============================================================
# CONFIG API KEY
# ============================================================
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

# MODELO GEMINI NATIVO (COMPATIBLE CON CREWAI)
llm = genai.GenerativeModel("gemini-2.0-flash")

# ============================================================
# LECTURA PDF / DOCX
# ============================================================
def leer_pdf(file):
    try:
        reader = PdfReader(file)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() + "\n"
        return texto
    except:
        return ""

def leer_docx(file):
    try:
        doc = docx.Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    except:
        return ""

# ============================================================
# PROCESAR ARCHIVOS
# ============================================================
def procesar_archivos(lista):
    corpus = ""
    for archivo in lista:
        nombre = archivo.name.lower()

        if nombre.endswith(".pdf"):
            corpus += leer_pdf(archivo)

        elif nombre.endswith(".docx"):
            corpus += leer_docx(archivo)

    # Límite seguro para evitar fallos
    return corpus[:10000]

# ============================================================
# STREAMLIT UI
# ============================================================
st.title("🎓 Simulador Examen de Grado – Derecho U. de Chile")

st.sidebar.header("Carga tus apuntes")
archivos = st.sidebar.file_uploader(
    "Sube tus apuntes (PDF o DOCX):",
    type=["pdf","docx"],
    accept_multiple_files=True
)

if st.sidebar.button("Procesar apuntes"):
    if not archivos:
        st.error("Debes subir al menos un archivo.")
        st.stop()

    st.session_state["corpus"] = procesar_archivos(archivos)
    st.success("📘 Apuntes cargados.")

if "corpus" not in st.session_state:
    st.warning("Sube apuntes para continuar.")
    st.stop()

corpus = st.session_state["corpus"]

# ============================================================
# ÁREA
# ============================================================
area = st.selectbox(
    "Selecciona un área:",
    ["Derecho Constitucional","Derecho Civil","Derecho Procesal Civil"]
)

# ============================================================
# AGENTES
# ============================================================
def wrapper(prompt):
    """Convierte Gemini nativo en interfaz simple para CrewAI."""
    respuesta = llm.generate_content(prompt)
    return respuesta.text

profesor = Agent(
    role=f"Profesor de {area}",
    goal="Formular preguntas muy difíciles usando solo los apuntes.",
    backstory="Profesor de examen de grado de la U. de Chile.",
    llm=wrapper
)

presidente = Agent(
    role="Presidente de Comisión",
    goal="Evaluar la respuesta del alumno con nota y análisis crítico.",
    backstory="Miembro de comisión examen de grado UCH.",
    llm=wrapper
)


# ============================================================
# GENERAR PREGUNTA
# ============================================================
if st.button("Generar pregunta"):
    tarea = Task(
        description=f"""
        Usa este material:

        {corpus}

        Genera una pregunta:
        - Área: {area}
        - Muy difícil
        - Breve
        - Basada exclusivamente en los apuntes
        """,
        expected_output="Una pregunta de examen.",
        agent=profesor
    )

    pregunta = Crew(
        agents=[profesor],
        tasks=[tarea]
    ).kickoff()

    st.session_state["pregunta"] = pregunta
    st.success("Pregunta generada.")

# Mostrar pregunta
if "pregunta" in st.session_state:
    st.subheader("🛑 Pregunta de examen")
    st.write(st.session_state["pregunta"])

# ============================================================
# RESPUESTA DEL ALUMNO
# ============================================================
respuesta = st.text_area("✍️ Escribe tu respuesta:")

# ============================================================
# EVALUAR
# ============================================================
if st.button("Evaluar respuesta"):
    if respuesta.strip() == "":
        st.error("Debes escribir algo.")
        st.stop()

    tarea_eval = Task(
        description=f"""
        Evalúa examen U. Chile:

        Pregunta:
        {st.session_state["pregunta"]}

        Respuesta del alumno:
        {respuesta}

        Basado únicamente en:
        {corpus}

        Entrega:
        - Nota de 1.0 a 7.0
        - Análisis crítico
        - Respuesta correcta con doctrina y artículos
        """,
        expected_output="Evaluación completa.",
        agent=presidente
    )

    evaluacion = Crew(
        agents=[presidente],
        tasks=[tarea_eval]
    ).kickoff()

    st.subheader("📄 Evaluación")
    st.write(evaluacion)

    st.success("Evaluación generada.")
    