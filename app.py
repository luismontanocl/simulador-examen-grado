import streamlit as st
import docx
from PyPDF2 import PdfReader
import google.generativeai as genai
import time

# ============================================================
# CONFIGURACIÓN DE GEMINI
# ============================================================
genai.configure(api_key="AIzaSyCHXN3iQptZoYuc9jpKboQ1MepxZ_4RyBI")  
modelo = genai.GenerativeModel("gemini-1.5-pro")

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
    return corpus

# ============================================================
# RESUMEN SEGURO – ANTI RESOURCE EXHAUSTED
# ============================================================

def resumir_chunk(chunk, idx):
    prompt = f"""
    Resume este fragmento en un máximo de 250 palabras.
    NO inventes nada.

    --- Fragmento {idx} ---
    {chunk}
    ------------------------
    """

    for intento in range(3):
        try:
            r = modelo.generate_content(
                prompt,
                generation_config={"max_output_tokens": 512}
            )
            return r.text
        except:
            time.sleep(1.5 * (intento + 1))

    return ""


def reducir_corpus(corpus):
    # Corpus pequeño → no resumir
    if len(corpus) < 8000:
        return corpus

    CHUNK = 5000  # chunks seguros
    chunks = [corpus[i:i+CHUNK] for i in range(0, len(corpus), CHUNK)]

    resúmenes = []

    for i, ch in enumerate(chunks, start=1):
        r = resumir_chunk(ch, i)
        if r:
            resúmenes.append(r)

        # límite de seguridad para no explotar el modelo
        if len(resúmenes) >= 12:
            break

    texto_compacto = "\n".join(resúmenes)

    prompt_final = f"""
    A partir de estos resúmenes parciales,
    genera un meta-resumen académico en menos de 500 palabras.
    NO inventes nada.

    {texto_compacto}
    """

    meta = modelo.generate_content(
        prompt_final,
        generation_config={"max_output_tokens": 800}
    ).text

    return meta

# ============================================================
# INTERFAZ
# ============================================================
st.title("🎓 Simulador Examen de Grado – Derecho U. de Chile")
st.write("Compatible con apuntes grandes (120+ páginas).")

# Carga de archivos
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
# SELECCIÓN DE ÁREA
# ============================================================
area = st.selectbox(
    "Selecciona área:",
    ["Derecho Constitucional", "Derecho Civil", "Derecho Procesal Civil"]
)

# ============================================================
# GENERAR PREGUNTA
# ============================================================
if st.button("Generar pregunta"):
    prompt = f"""
    Genera una pregunta de examen de grado (muy difícil)
    basada SOLO en este meta-resumen compacto:

    {corpus}

    Área: {area}

    Debe ser una pregunta dura, conceptual y doctrinal.
    """

    r = modelo.generate_content(
        prompt,
        generation_config={"max_output_tokens": 500}
    ).text

    st.session_state["pregunta"] = r
    st.success("Pregunta generada.")

# Mostrar pregunta
if "pregunta" in st.session_state:
    st.subheader("❓ Pregunta de examen")
    st.write(st.session_state["pregunta"])

# ============================================================
# RESPUESTA DEL ALUMNO
# ============================================================
respuesta = st.text_area("✍ Tu respuesta:")

# ============================================================
# EVALUACIÓN
# ============================================================
if st.button("Evaluar respuesta"):
    if not respuesta.strip():
        st.error("Debes escribir una respuesta.")
        st.stop()

    prompt_eval = f"""
    Evalúa la respuesta según estándar de examen de grado U. de Chile.
    Usa exclusivamente este meta-resumen reducido:

    {corpus}

    --- PREGUNTA ---
    {st.session_state["pregunta"]}

    --- RESPUESTA DEL ALUMNO ---
    {respuesta}

    Entrega:
    - Nota (1.0 a 7.0)
    - Análisis crítico detallado
    - Respuesta correcta basada solo en el meta-resumen
    """

    e = modelo.generate_content(
        prompt_eval,
        generation_config={"max_output_tokens": 700}
    ).text

    st.subheader("📄 Evaluación")
    st.write(e)
    st.success("Evaluación generada.")