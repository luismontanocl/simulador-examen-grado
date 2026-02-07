import streamlit as st
import docx
from PyPDF2 import PdfReader
import google.generativeai as genai
import time

# ============================================================
# CONFIGURACIÓN DE GEMINI
# ============================================================
genai.configure(api_key="AIzaSyCHXN3iQptZoYuc9jpKboQ1MepxZ_4RyBI")   # <-- REEMPLAZAR
modelo = genai.GenerativeModel("gemini-pro")  # MODELO SEGURO PARA STREAMLIT CLOUD

# ============================================================
# LECTORES PDF / DOCX
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
# PROCESAR ARCHIVOS SUBIDOS
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
# RESUMIR CHUNK – SEGURO
# ============================================================
def resumir_chunk(chunk, idx):
    prompt = f"""
    Resume este fragmento jurídico en un máximo de 150 palabras.
    NO inventes nada.

    --- Fragmento {idx} ---
    {chunk}
    """

    for intento in range(3):
        try:
            r = modelo.generate_content(
                prompt,
                generation_config={"max_output_tokens": 350}
            )
            return r.text
        except Exception:
            time.sleep(1.5 * (intento + 1))

    return ""

# ============================================================
# REDUCIR CORPUS COMPLETO – META RESUMEN
# ============================================================
def reducir_corpus(corpus):
    if len(corpus) < 8000:
        return corpus

    CHUNK = 3500  # chunk pequeño para gemini-pro
    chunks = [corpus[i:i+CHUNK] for i in range(0, len(corpus), CHUNK)]

    resúmenes = []

    for i, ch in enumerate(chunks, start=1):
        r = resumir_chunk(ch, i)
        if r:
            resúmenes.append(r)

        if len(resúmenes) >= 15:  # seguridad
            break

    texto_compacto = "\n".join(resúmenes)

    prompt_final = f"""
    A partir de estos resúmenes parciales,
    genera un META-RESUMEN académico (máximo 350 palabras).
    NO inventes nada.
    
    {texto_compacto}
    """

    meta = modelo.generate_content(
        prompt_final,
        generation_config={"max_output_tokens": 550}
    ).text

    return meta

# ============================================================
# INTERFAZ DE USUARIO
# ============================================================
st.title("🎓 Simulador Examen de Grado – Derecho U. de Chile")
st.write("Compatible con apuntes extensos (100+ páginas).")

st.sidebar.header("Cargar apuntes (PDF o DOCX)")
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
    st.success("📘 Apuntes cargados, resumidos y compactados correctamente.")

if "corpus" not in st.session_state:
    st.warning("Sube tus apuntes para comenzar.")
    st.stop()

corpus = st.session_state["corpus"]

# ============================================================
# SELECCIÓN DE ÁREA
# ============================================================
area = st.selectbox(
    "Selecciona el área:",
    ["Derecho Constitucional", "Derecho Civil", "Derecho Procesal Civil"]
)

# ============================================================
# GENERAR PREGUNTA
# ============================================================
if st.button("Generar pregunta"):
    prompt = f"""
    Genera una pregunta de examen de grado (MUY difícil),
    basada exclusivamente en este meta-resumen:

    {corpus}

    Área: {area}

    Debe ser conceptual, doctrinal y típica de examen de profesor.
    """

    r = modelo.generate_content(
        prompt,
        generation_config={"max_output_tokens": 450}
    ).text

    st.session_state["pregunta"] = r
    st.success("Pregunta generada.")

if "pregunta" in st.session_state:
    st.subheader("❓ Pregunta del examen")
    st.write(st.session_state["pregunta"])

# ============================================================
# RESPUESTA DEL ALUMNO
# ============================================================
respuesta = st.text_area("✍ Escribe tu respuesta:")

# ============================================================
# EVALUACIÓN
# ============================================================
if st.button("Evaluar respuesta"):
    if not respuesta.strip():
        st.error("Debes escribir una respuesta.")
        st.stop()

    prompt_eval = f"""
    Evalúa la respuesta con estándar de Examen de Grado U. de Chile.
    Usa exclusivamente este meta-resumen:

    {corpus}

    --- Pregunta ---
    {st.session_state["pregunta"]}

    --- Respuesta del alumno ---
    {respuesta}

    Entrega:
    - Nota (1.0 a 7.0)
    - Análisis crítico
    - Respuesta correcta basada SOLO en el meta-resumen
    """

    e = modelo.generate_content(
        prompt_eval,
        generation_config={"max_output_tokens": 700}
    ).text

    st.subheader("📄 Evaluación")
    st.write(e)
    st.success("Evaluación generada correctamente.")