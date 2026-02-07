import streamlit as st
import docx
from PyPDF2 import PdfReader
import google.generativeai as genai

# ============================================================
# CONFIGURACIÓN DE GEMINI
# ============================================================
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

modelo = genai.GenerativeModel("gemini-2.0-flash")

# ============================================================
# FUNCIONES PARA LEER PDF / DOCX
# ============================================================
def leer_pdf(file):
    try:
        reader = PdfReader(file)
        texto = ""
        for page in reader.pages:
            extraido = page.extract_text()
            if extraido:
                texto += extraido + "\n"
        return texto
    except Exception:
        return ""

def leer_docx_file(file):
    try:
        doc = docx.Document(file)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""

# ============================================================
# PROCESAMIENTO DE ARCHIVOS SUBIDOS
# ============================================================
def procesar_archivos(archivos):
    corpus = ""
    for archivo in archivos:
        nombre = archivo.name.lower()

        if nombre.endswith(".pdf"):
            corpus += leer_pdf(archivo)

        elif nombre.endswith(".docx"):
            corpus += leer_docx_file(archivo)

    # Límite seguro para Gemini
    return corpus[:12000]

# ============================================================
# STREAMLIT UI
# ============================================================
st.title("🎓 Simulador Examen de Grado – Derecho U. de Chile")
st.write("Simulador con generación de preguntas y evaluación automática usando Gemini.")

st.sidebar.header("Carga tus apuntes")
archivos = st.sidebar.file_uploader(
    "Sube tus apuntes (PDF / DOCX)",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if st.sidebar.button("Procesar apuntes"):
    if not archivos:
        st.error("Debes subir al menos un archivo.")
        st.stop()

    st.session_state["corpus"] = procesar_archivos(archivos)
    st.success("📘 Apuntes cargados correctamente.")

if "corpus" not in st.session_state:
    st.warning("Sube apuntes para continuar.")
    st.stop()

corpus = st.session_state["corpus"]

# ============================================================
# SELECCIÓN DE ÁREA
# ============================================================
area = st.selectbox(
    "Selecciona un área:",
    ["Derecho Constitucional", "Derecho Civil", "Derecho Procesal Civil"]
)

# ============================================================
# GENERAR PREGUNTA CON GEMINI
# ============================================================
if st.button("Generar pregunta"):
    prompt = f"""
    Eres un profesor de examen de grado de la Universidad de Chile.
    Usa EXCLUSIVAMENTE este corpus de apuntes (no inventes nada externo):

    --- APUNTES ---
    {corpus}
    ----------------

    Genera UNA sola pregunta de examen:

    - Área: {area}
    - Muy difícil
    - Breve pero exigente
    - 100% basada en los apuntes
    """

    respuesta = modelo.generate_content(prompt)
    st.session_state["pregunta"] = respuesta.text

    st.success("Pregunta generada.")

# Mostrar pregunta
if "pregunta" in st.session_state:
    st.subheader("🛑 Pregunta de examen")
    st.write(st.session_state["pregunta"])

# ============================================================
# RESPUESTA DEL ESTUDIANTE
# ============================================================
respuesta_alumno = st.text_area("✍️ Escribe tu respuesta:", height=250)

# ============================================================
# EVALUACIÓN CON GEMINI
# ============================================================
if st.button("Evaluar respuesta"):
    if respuesta_alumno.strip() == "":
        st.error("Debes escribir una respuesta.")
        st.stop()

    prompt_eval = f"""
    Eres un PRESIDENTE DE COMISIÓN DE EXAMEN DE GRADO de la U. de Chile.

    Evalúa la siguiente respuesta basándote SOLO en los apuntes entregados.
    NO inventes doctrina o artículos que no estén en los apuntes.

    --- PREGUNTA ---
    {st.session_state["pregunta"]}

    --- RESPUESTA DEL ALUMNO ---
    {respuesta_alumno}

    --- APUNTES ---
    {corpus}
    ----------------

    Debes entregar:

    1) Una NOTA del 1.0 al 7.0, estrictamente siguiendo el estándar del examen de grado.
    2) Un análisis crítico detallado, señalando aciertos, omisiones y errores.
    3) La respuesta correcta, basada SOLO en el corpus.

    Entrega en formato:

    **Nota:** X.X  
    **Análisis:** ...  
    **Respuesta correcta:** ...
    """

    evaluacion = modelo.generate_content(prompt_eval)

    st.subheader("📄 Evaluación")
    st.write(evaluacion.text)

    st.success("Evaluación generada exitosamente.")