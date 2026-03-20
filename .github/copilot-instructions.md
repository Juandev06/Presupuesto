# Instrucciones Base del Espacio de Trabajo (Workspace Instructions)

Estas son las convenciones y directrices para el agente de IA que trabaje en este proyecto.

## Contexto del Proyecto
- **Propósito**: Aplicación para la generación de presupuestos de acometidas para "SERVICIUDAD E.S.P."
- **Stack Tecnológico**: Python 3, Streamlit (UI web), Pandas (procesamiento de datos), ReportLab (generación de PDFs).
- **Estructura**: La aplicación principal está en `v3/app_streamlit_presupuesto_v3.py`.
- **Archivos Clave**:
  - Configuración base en CSV: `v3/config_presupuesto_acometidas_v3.csv`
  - Estado del consecutivo (ID): `v3/consecutivo_state.json`
  - Assets estáticos: Imágenes (`logo.jpg`, `serviciudad_pdf_header.png`, `serviciudad_pdf_footer.jpg`).
  - Directorio de salida: `v3/salidas_pdf/`

## Convenciones de Código y Arquitectura
- **Rutas Relativas**: Mantener siempre el uso de `pathlib.Path` para gestión de rutas (como ya se hace para `OUTPUT_DIR`), garantizando que los archivos estáticos y configuraciones se resuelvan correctamente.
- **UI/UX**: Modificaciones a la interfaz deben seguir utilizando la paleta de colores inyectada vía CSS personalizados en `app_streamlit_presupuesto_v3.py`.
- **Generación de PDFs**: Para cualquier cambio en la salida (ReportLab), mantener un espaciado consistente y probar la visualización de logotipos para que encajen adecuadamente.

## Comandos Útiles e Infraestructura Local
- **Entorno Virtual**: Ubicado en `.venv`. Al abrir una nueva terminal debe estar activado.
- **Instalación de dependencias**: 
  ```bash
  pip install -r v3/requirements_v3.txt
  ```
- **Ejecución del aplicativo en desarrollo**:
  ```bash
  streamlit run v3/app_streamlit_presupuesto_v3.py
  ```

## Anti-patrones a evitar
- Evitar usar rutas absolutas "hard-codeadas" (ej. `C:/Users/...`) ya que romperían la funcionalidad en ambientes compartidos.
- No modificar el estado JSON manualmente si la app está en ejecución concurrente sin validaciones previas.
- No sobreescribir estilos base de Streamlit que rompan el diseño en temas Dark/Light nativos, intentar siempre usar las variables propias declaradas en cabecera.
