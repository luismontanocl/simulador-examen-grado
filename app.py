import streamlit as st
import os
import datetime
import docx
from PyPDF2 import PdfReader
from crewai import Agent, Task, Crew
from langchain_google_genai import ChatGoogleGenerativeAI

# ============================================================
# CONFIGURACIÓN API KEY (desde Streamlit Secrets)
# ============================================================
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    temperature=0.4,
    google_api_key=GOOGLE_API_KEY,
    verbose=True
)

# ============================================================
# RUTA DE GOOGLE DRIVE (tu carpeta de apuntes)
# ============================================================
RUTA_APUNTES = "/content/drive/MyDrive/ApuntesWikiBello"

# ============================================================
# FUNCIONES PARA LEER PDF Y DOCX
# ============================================================
def leer_pdf(path):
    try:
        reader = PdfReader(path)
        texto = ""
        for page in reader.pages:
            texto += page.extract_text() + "\n"
        return texto
    except Exception as e:
        return ""

def leer_docx(path):
    try:
        doc = docx.Document(path)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as e:
        return ""

def cargar_apuntes():
    corpus = ""
    for archivo in os.listdir(RUTA_APUNTES):
        path = os.path.join(RUTA_APUNTES, archivo)

        if archivo.lower().endswith(".pdf"):
            corpus += leer_pdf(path) + "\n"

        elif archivo.lower().endswith(".docx"):
            corpus += leer_docx(path) + "\n"

    return corpus[:20000]  # límite para el modelo

# ============================================================
# INTERFAZ STREAMLIT
# ============================================================
st.title("🎓 Simulador Examen de Grado – Derecho U. de Chile")
st.write("Simulador completo con generación de preguntas y evaluación automática.")

st.sidebar.header("Configuración")
st.sidebar.write("Carga tus apuntes de Drive antes de comenzar.")

# ============================================================
# BOTÓN PARA CARGAR APUNTES
# ============================================================
if st.sidebar.button("Cargar apuntes desde Drive"):
    st.session_state["corpus"] = cargar_apuntes()
    st.success("📘 Apuntes cargados desde tu Google Drive.")

if "corpus" not in st.session_state:
    st.warning("⚠️ Carga tus apuntes desde el panel lateral para comenzar.")
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
    tarea_pregunta = Task(
        description=f"""
        Usa exclusivamente este material:

        {corpus}

        Genera una pregunta de examen de grado:

        - Del área: {area}
        - Muy difícil
        - Breve
        - Basada SOLO en los apuntes
        """,
        expected_output="Una pregunta de examen.",
        agent=profesor
    )

    pregunta = Crew(
        agents=[profesor],
        tasks=[tarea_pregunta]
    ).kickoff()

    st.session_state["pregunta"] = pregunta
    st.success("Pregunta generada.")

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
        2) Análisis crítico detallado
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

    # ========================================================
    # GUARDAR BITÁCORA EN DRIVE
    # ========================================================
    ruta_bitacora = "/content/drive/MyDrive/Bitacora_Examenes_Derecho.txt"
    fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    with open(ruta_bitacora, "a", encoding="utf-8") as f:
        f.write("\n" + "="*40 + "\n")
        f.write(f"📅 FECHA: {fecha}\n")
        f.write(f"📘 ÁREA: {area}\n")
        f.write(f"❓ PREGUNTA: {st.session_state['pregunta']}\n")
        f.write(f"🗣️ RESPUESTA: {respuesta}\n")
        f.write(f"👨‍⚖️ EVALUACIÓN: {resultado}\n")
        f.write("="*40 + "\n")

    st.success("📝 Bitácora guardada en tu Google Drive.")