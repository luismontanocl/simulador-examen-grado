import os
import streamlit as st
import datetime
import docx
from PyPDF2 import PdfReader
from crewai import Agent, Task, Crew
from langchain_google_genai import ChatGoogleGenerativeAI

# ============================================================
# CONFIGURACIÓN API KEY (Streamlit Secrets)
# ============================================================
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",,
    temperature=0.4,
    google_api_key=GOOGLE_API_KEY,
    verbose=True
)

# ============================================================
# FUNCIONES PARA LEER PDF Y DOCX
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
# LECTURA DE ARCHIVOS SUBIDOS POR EL USUARIO
# ============================================================
def procesar_archivos(lista_archivos):
    corpus = ""
    for archivo in lista_archivos:
        nombre = archivo.name.lower()

        if nombre.endswith(".pdf"):
            corpus += leer_pdf(archivo) + "\n"

        elif nombre.endswith(".docx"):
            corpus += leer_docx(archivo) + "\n"

    return corpus[:30000]  # límite para el modelo

# ============================================================
# INTERFAZ STREAMLIT
# ============================================================
st.title("🎓 Simulador Examen de Grado – Derecho U. de Chile")
st.write("Simulador con generación de preguntas y evaluación automática.")

st.sidebar.header("Configuración")
st.sidebar.write("Sube tus apuntes para comenzar:")

# ============================================================
# SUBIR ARCHIVOS
# ============================================================
archivos = st.sidebar.file_uploader(
    "Selecciona tus apuntes (PDF o DOCX):",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if st.sidebar.button("Procesar apuntes"):
    if not archivos:
        st.error("Debes subir al menos un archivo.")
        st.stop()

    st.session_state["corpus"] = procesar_archivos(archivos)
    st.success("📘 Apuntes procesados correctamente.")

# avisar si falta corpus
if "corpus" not in st.session_state:
    st.warning("⚠️ Sube tus apuntes desde el panel lateral para comenzar.")
    st.stop()

corpus = st.session_state["corpus"]

# ============================================================
# SELECCIÓN DEL ÁREA DE EXAMEN
# ============================================================
area = st.selectbox(
    "Selecciona un área de examen:",
    ["Derecho Constitucional", "Derecho Civil", "Derecho Procesal Civil"]
)

# ============================================================
# AGENTES CREWAI
# ============================================================
profesor = Agent(
    role=f"Profesor de {area}",
    goal="Formular preguntas extremadamente difíciles usando solo los apuntes.",
    backstory="Profesor de examen de grado de la Universidad de Chile.",
    llm=llm
)

presidente = Agent(
    role="Presidente de Comisión",
    goal="Evaluar la respuesta del alumno con nota y análisis crítico.",
    backstory="Miembro de comisión de examen de grado.",
    llm=llm
)

# ============================================================
# GENERACIÓN DE PREGUNTA
# ============================================================
if st.button("Generar pregunta"):
    tarea = Task(
        description=f"""
        Usa exclusivamente este material:

        {corpus}

        Genera una pregunta de examen de grado:

        - Área: {area}
        - Muy difícil
        - Breve
        - Basada SOLO en los apuntes
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

# mostrar pregunta
if "pregunta" in st.session_state:
    st.subheader("🛑 Pregunta de examen")
    st.write(st.session_state["pregunta"])

# ============================================================
# RESPUESTA DEL ALUMNO
# ============================================================
respuesta = st.text_area("✍️ Escribe tu respuesta aquí:", height=250)

# ============================================================
# EVALUACIÓN
# ============================================================
if st.button("Evaluar respuesta"):
    if respuesta.strip() == "":
        st.error("Debes escribir una respuesta.")
        st.stop()

    tarea_eval = Task(
        description=f"""
        Evalúa según examen de grado U. de Chile:

        PREGUNTA:
        {st.session_state["pregunta"]}

        RESPUESTA:
        {respuesta}

        Usa SOLO los apuntes:

        {corpus}

        Entrega:
        1) Nota (1.0 a 7.0)
        2) Análisis crítico
        3) Respuesta correcta con doctrina y artículos
        """,
        expected_output="Evaluación completa.",
        agent=presidente
    )

    resultado = Crew(
        agents=[presidente],
        tasks=[tarea_eval]
    ).kickoff()

    st.subheader("📄 Evaluación del examen")
    st.write(resultado)

    st.success("Evaluación generada exitosamente.")
    