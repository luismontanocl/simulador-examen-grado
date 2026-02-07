import streamlit as st
import docx
from PyPDF2 import PdfReader
import google.generativeai as genai

# ============================================================
# CONFIGURACIÓN DE GEMINI
# ============================================================
genai.configure(api_key="AIzaSyCHXN3iQptZoYuc9jpKboQ1MepxZ_4RyBI")
modelo = genai.GenerativeModel("gemini-2.0-flash")

# ============================================================
# LECTORES DE PDF Y DOCX
# ============================================================
def leer_pdf(file):
    try:
        reader = PdfReader(file)
        texto = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texto += t + "\n"
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
# PROCESAR ARCHIVOS A TEXTO CRUDO
# ============================================================
def procesar_archivos(lista):
    corpus = ""
    for archivo in lista:
        nombre = archivo.name.lower()
        if nombre.endswith(".pdf"):
            corpus += leer_pdf(archivo)
        elif nombre.endswith(".docx"):
            corpus += leer_docx(archivo)
    return corpus

# ============================================================
# RESUMEN JERÁRQUICO (para 120+ páginas)
# ============================================================

def resumir_chunk(chunk, idx):
    prompt = f"""
    Resume de forma académica este fragmento extenso de apuntes jurídicos.

    NO inventes nada.
    NO agregues doctrina externa.
    NO cites leyes que no estén dentro.

    --- FRAGMENTO {idx} ---
    {chunk}
    ------------------------

    Resume con:
    - conceptos clave
    - definiciones
    - estructura normativa
    - doctrina mencionada
    - puntos esenciales
    """
    return modelo.generate_content(prompt).text


def reducir_corpus(corpus):
    # Si es muy chico, no resumir
    if len(corpus) < 10000:
        return corpus

    # 1) Dividir el corpus en bloques grandes (chunking)
    chunks = [corpus[i:i+10000] for i in range(0, len(corpus), 10000)]

    resúmenes_parciales = ""

    # 2) Resumir cada chunk individualmente
    for i, ch in enumerate(chunks, start=1):
        r = resumir_chunk(ch, i)
        resúmenes_parciales += r + "\n"

        # Seguridad para no explotar contexto
        if len(resúmenes_parciales) > 35000:
            break

    # 3) Resumen final del resumen (meta–resumen)
    prompt_final = f"""
    A partir de los siguientes resúmenes parciales,
    genera un META-RESUMEN final que concentre solo:

    - conceptos esenciales
    - definiciones jurídicas
    - doctrina citada
    - estructura normativa
    - elementos clave del curso

    NO inventes nada. Usa únicamente la información dada.

    --- RESÚMENES PARCIALES ---
    {resúmenes_parciales}
    --------------------------
    """

    meta = modelo.generate_content(prompt_final).text

    # Limitar a 10k tokens
    return meta[:10000]

# ============================================================
# INTERFAZ
# ============================================================
st.title("🎓 Simulador Examen de Grado – Derecho U. de Chile")
st.write("Compatible con apuntes grandes (120+ páginas).")

st.sidebar.header("Carga de apuntes (PDF o DOCX)")
archivos = st.sidebar.file_uploader(
    "Selecciona tus archivos:",
    type=["pdf", "docx"],
    accept_multiple_files=True
)

if st.sidebar.button("Procesar apuntes"):
    if not archivos:
        st.error("Debes subir archivos.")
        st.stop()

    texto = procesar_archivos(archivos)
    corpus = reducir_corpus(texto)

    st.session_state["corpus"] = corpus
    st.success("📘 Apuntes cargados y compactados correctamente.")

if "corpus" not in st.session_state:
    st.warning("Sube apuntes para comenzar.")
    st.stop()

corpus = st.session_state["corpus"]

# ============================================================
# AREA
# ============================================================
area = st.selectbox(
    "Selecciona área:",
    ["Derecho Constitucional", "Derecho Civil", "Derecho Procesal Civil"]
)

# GENERAR PREGUNTA
if st.button("Generar pregunta"):
    prompt = f"""
    Genera una pregunta de examen de grado (muy difícil)
    basada SOLO en este meta-resumen:

    {corpus}

    Área: {area}
    """
    r = modelo.generate_content(prompt).text
    st.session_state["pregunta"] = r
    st.success("Pregunta generada.")

# Mostrar pregunta
if "pregunta" in st.session_state:
    st.subheader("❓ Pregunta de examen")
    st.write(st.session_state["pregunta"])

# RESPUESTA DEL ALUMNO
respuesta = st.text_area("✍ Tu respuesta:")

# EVALUACIÓN
if st.button("Evaluar respuesta"):
    if not respuesta.strip():
        st.error("Debes escribir una respuesta.")
        st.stop()

    prompt_eval = f"""
    Evalúa la respuesta según estándar de examen de grado U. de Chile.
    Usa exclusivamente este meta-resumen:

    {corpus}

    --- PREGUNTA ---
    {st.session_state["pregunta"]}

    --- RESPUESTA DEL ALUMNO ---
    {respuesta}

    Entrega:
    - Nota (1.0 a 7.0)
    - Análisis crítico
    - Respuesta correcta basada solo en el meta-resumen
    """

    e = modelo.generate_content(prompt_eval).text

    st.subheader("📄 Evaluación")
    st.write(e)
    st.success("Evaluación generada.")