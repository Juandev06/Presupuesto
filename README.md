# Presupuesto Acometidas - SERVICIUDAD E.S.P. 💧

Aplicación web diseñada para automatizar la generación de presupuestos para acometidas (acueducto, alcantarillado, etc.). Permite la captura de datos de obra, el cálculo automático de costos y la generación de un documento PDF oficial.

## 🚀 Tecnologías Principales

- **Python 3:** Lenguaje base del proyecto.
- **[Streamlit](https://streamlit.io/):** Framework para construir y desplegar la interfaz web (Frontend) puramente con Python.
- **Pandas:** Utilizado para la lectura, consulta y manipulación del archivo de configuración (base de datos CSV).
- **ReportLab & PyPDF2:** Librerías encargadas de renderizar y construir los reportes finales en formato PDF.
- **Pillow (PIL):** Procesamiento de las imágenes y logotipos institucionales.

## 📂 Estructura del Proyecto

El proyecto está organizado de la siguiente manera:

```text
📁 Proyecto (Raíz)
├── 📄 app_streamlit_presupuesto_v3.py      # Script principal. Contiene toda la lógica de la UI, los cálculos y la creación del PDF.
├── 📄 config_presupuesto_acometidas_v3.csv # Actúa como la Base de Datos. Contiene listas, parámetros, porcentajes (IVA, ADM) y precios base.
├── 📄 consecutivo_state.json               # Archivo de persistencia local. Guarda el último número (ID) de presupuesto generado (ej. PR-2026: 28).
├── 📄 requirements_v3.txt                  # Lista de todas las dependencias/librerías necesarias para correr el proyecto.
├── 📁 salidas_pdf/                         # Directorio dinámico donde se guardan temporalmente los PDFs generados.
├── 🖼️ logo.jpg                             # Imagen del logo principal usado en la interfaz de usuario.
├── 🖼️ serviciudad_pdf_header.png           # Imagen de la cabecera para los reportes PDF.
└── 🖼️ serviciudad_pdf_footer.jpg           # Imagen del pie de página para los reportes PDF.
```

## 🎨 ¿Cómo está hecho el Frontend (Interfaz de Usuario)?

El frontend NO utiliza HTML o frameworks de JavaScript como React o Angular de forma tradicional. Está construido de la siguiente manera:
1. **Componentes con Streamlit:** Se usan comandos en Python como `st.text_input`, `st.selectbox` y `st.button` para generar automáticamente los formularios y controles en la pantalla.
2. **Estilizado Avanzado (CSS Injection):** Para que no luzca como una aplicación genérica de Streamlit, en las primeras líneas de `app_streamlit_presupuesto_v3.py` se inyecta un bloque de código CSS personalizado (`st.markdown("<style>...</style>")`).
3. **Efecto Glassmorphism:** El CSS inyectado contiene efectos de desenfoque (`backdrop-filter: blur`), bordes semitransparentes y gradientes oscuros para lograr un aspecto moderno y traslúcido.

## 💻 Instrucciones de Uso (Local)

1. Activa el entorno virtual.
2. Instala las dependencias: `pip install -r v3/requirements_v3.txt` (Asegúrate de apuntar al archivo correcto).
3. Ejecuta la aplicación:
   ```bash
   streamlit run v3/app_streamlit_presupuesto_v3.py
   ```
