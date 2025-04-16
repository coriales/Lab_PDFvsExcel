import streamlit as st
import pandas as pd
import PyPDF2
import re
import os
import sys
import difflib
import logging
from datetime import datetime
from pathlib import Path
import tempfile
import io

# Configuración de la página
st.set_page_config(
    page_title="Comparador de Muestras - BRAUT EIX AMBIENTAL",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #0D47A1;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .success-text {
        color: #4CAF50;
        font-weight: bold;
    }
    .warning-text {
        color: #FF9800;
        font-weight: bold;
    }
    .error-text {
        color: #F44336;
        font-weight: bold;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .result-box {
        background-color: #F5F5F5;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-top: 1rem;
    }
    .footer {
        text-align: center;
        margin-top: 3rem;
        color: #757575;
        font-size: 0.8rem;
    }
    /* Hacer que los botones de carga de archivos sean más grandes y visibles */
    .stButton>button {
        width: 100%;
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
    }
    /* Estilo para el botón de comparación */
    .stButton.compare-button>button {
        background-color: #4CAF50;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown("<h1 class='main-header'>Comparador de Muestras</h1>", unsafe_allow_html=True)
st.markdown("<div class='info-box'>Esta aplicación compara muestras entre un archivo Excel y un PDF de factura, identificando discrepancias y generando un informe detallado.</div>", unsafe_allow_html=True)

# Clase para el comparador de muestras
class ComparadorMuestras:
    """Clase principal para comparar muestras entre Excel y PDF."""
    
    def __init__(self, excel_file, pdf_file):
        """
        Inicializa el comparador con los archivos.
        
        Args:
            excel_file: Archivo Excel cargado
            pdf_file: Archivo PDF cargado
        """
        self.excel_file = excel_file
        self.pdf_file = pdf_file
        
        # Inicializar variables para almacenar datos
        self.excel_data = None
        self.pdf_data = None
        self.resultados_comparacion = {
            'coincidencias': [],
            'excel_no_factura': [],
            'factura_no_excel': [],
            'duplicados_factura': [],
            'coincidencias_parciales': []
        }
    
    def procesar_excel(self):
        """
        Procesa el archivo Excel para extraer información de muestras.
        
        Returns:
            bool: True si el procesamiento fue exitoso, False en caso contrario
        """
        try:
            # Leer el archivo Excel
            xls = pd.ExcelFile(self.excel_file)
            
            # Obtener la primera hoja
            sheet_name = xls.sheet_names[0]
            df = pd.read_excel(xls, sheet_name=sheet_name)
            
            # Buscar la fila de encabezados (normalmente entre las filas 1-5)
            header_row = None
            for i in range(5):
                if 'Ref.' in df.iloc[i].values or 'Mostra' in df.iloc[i].values:
                    header_row = i
                    break
            
            if header_row is None:
                st.error("No se encontró la fila de encabezados en el Excel")
                return False
            
            # Reemplazar encabezados
            df.columns = df.iloc[header_row]
            df = df.iloc[header_row+1:].reset_index(drop=True)
            
            # Normalizar nombres de columnas
            column_mapping = {
                'Ref.': 'ref',
                'Instal·lació': 'instalacion',
                'Procedència': 'procedencia',
                'Mostra': 'muestra',
                'Codi Eix': 'codiEix',
                'Anàlisis': 'analisis'
            }
            
            # Renombrar columnas si existen
            for old_name, new_name in column_mapping.items():
                if old_name in df.columns:
                    df = df.rename(columns={old_name: new_name})
            
            # Verificar que tenemos las columnas necesarias
            required_columns = ['muestra', 'codiEix', 'analisis']
            for col in required_columns:
                if col not in df.columns:
                    st.error(f"Columna requerida '{col}' no encontrada en el Excel")
                    return False
            
            # Limpiar y normalizar datos
            df = df.fillna('')
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype(str).str.strip()
            
            # Normalizar códigos de muestra (eliminar espacios, puntos, etc.)
            df['muestra_norm'] = df['muestra'].apply(self._normalizar_codigo)
            
            # Convertir a lista de diccionarios para facilitar la comparación
            self.excel_data = df.to_dict('records')
            
            return True
            
        except Exception as e:
            st.error(f"Error al procesar el archivo Excel: {str(e)}")
            return False
    
    def procesar_pdf(self):
        """
        Procesa el archivo PDF para extraer información de muestras.
        
        Returns:
            bool: True si el procesamiento fue exitoso, False en caso contrario
        """
        try:
            # Extraer texto del PDF
            pdf_text = self._extraer_texto_pdf()
            if not pdf_text:
                st.error("No se pudo extraer texto del PDF")
                return False
            
            # Extraer muestras del texto del PDF
            muestras = self._extraer_muestras_pdf(pdf_text)
            
            if not muestras:
                st.error("No se encontraron muestras en el PDF")
                return False
            
            self.pdf_data = muestras
            
            return True
            
        except Exception as e:
            st.error(f"Error al procesar el archivo PDF: {str(e)}")
            return False
    
    def _extraer_texto_pdf(self):
        """
        Extrae todo el texto del archivo PDF.
        
        Returns:
            str: Texto extraído del PDF
        """
        try:
            text = ""
            pdf_reader = PyPDF2.PdfReader(self.pdf_file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            st.error(f"Error al extraer texto del PDF: {str(e)}")
            return ""
    
    def _extraer_muestras_pdf(self, pdf_text):
        """
        Extrae información de muestras del texto del PDF.
        
        Args:
            pdf_text (str): Texto extraído del PDF
        
        Returns:
            list: Lista de diccionarios con información de muestras
        """
        muestras = []
        
        # Patrones para identificar muestras en el formato de factura de TeleTest
        # Buscamos líneas que contengan códigos de muestra y análisis
        lineas = pdf_text.split('\n')
        
        # Patrones para identificar códigos de muestra y análisis
        patron_muestra = r'(\d{8})'  # Patrón para códigos de muestra (8 dígitos)
        patron_codiEix = r'(M-\d{2}-\d{4})'  # Patrón para códigos Eix (M-XX-XXXX)
        
        for i, linea in enumerate(lineas):
            # Buscar códigos de muestra
            match_muestra = re.search(patron_muestra, linea)
            if match_muestra:
                muestra = match_muestra.group(1)
                
                # Buscar código Eix en la misma línea o en las siguientes
                codiEix = ""
                analisis = ""
                
                # Buscar en la línea actual
                match_codiEix = re.search(patron_codiEix, linea)
                if match_codiEix:
                    codiEix = match_codiEix.group(1)
                
                # Si no se encontró en la línea actual, buscar en las siguientes
                if not codiEix and i+1 < len(lineas):
                    match_codiEix = re.search(patron_codiEix, lineas[i+1])
                    if match_codiEix:
                        codiEix = match_codiEix.group(1)
                
                # Extraer descripción del análisis (resto de la línea después del código Eix)
                if codiEix and codiEix in linea:
                    analisis = linea.split(codiEix, 1)[1].strip()
                elif i+1 < len(lineas) and codiEix and codiEix in lineas[i+1]:
                    analisis = lineas[i+1].split(codiEix, 1)[1].strip()
                
                # Si no se encontró análisis, usar el resto de la línea actual
                if not analisis:
                    # Intentar extraer después del código de muestra
                    if muestra in linea:
                        analisis = linea.split(muestra, 1)[1].strip()
                
                # Extraer referencia e instalación si están disponibles
                ref = ""
                instalacion = ""
                
                # Buscar en líneas anteriores
                for j in range(max(0, i-3), i):
                    if "Ref." in lineas[j]:
                        ref_line = lineas[j]
                        ref_match = re.search(r'Ref\.\s*(\d+)', ref_line)
                        if ref_match:
                            ref = ref_match.group(1)
                    
                    if "Instal·lació" in lineas[j] or "Instalación" in lineas[j]:
                        instalacion = lineas[j].split(":", 1)[1].strip() if ":" in lineas[j] else ""
                
                # Crear registro de muestra
                muestra_record = {
                    'ref': ref,
                    'instalacion': instalacion,
                    'muestra': muestra,
                    'muestra_norm': self._normalizar_codigo(muestra),
                    'codiEix': codiEix,
                    'analisis': analisis
                }
                
                muestras.append(muestra_record)
        
        return muestras
    
    def _normalizar_codigo(self, codigo):
        """
        Normaliza un código eliminando espacios, puntos, etc.
        
        Args:
            codigo (str): Código a normalizar
        
        Returns:
            str: Código normalizado
        """
        if not codigo:
            return ""
        
        # Convertir a string si no lo es
        codigo = str(codigo)
        
        # Eliminar espacios, puntos, guiones, etc.
        return re.sub(r'[^a-zA-Z0-9]', '', codigo)
    
    def comparar_muestras(self):
        """
        Compara las muestras entre el Excel y el PDF.
        
        Returns:
            bool: True si la comparación fue exitosa, False en caso contrario
        """
        try:
            if not self.excel_data or not self.pdf_data:
                st.error("No hay datos para comparar. Asegúrese de procesar primero los archivos.")
                return False
            
            # Crear diccionarios para facilitar la búsqueda
            excel_dict = {m['muestra_norm']: m for m in self.excel_data}
            
            # Identificar muestras duplicadas en la factura
            pdf_muestras = [m['muestra_norm'] for m in self.pdf_data]
            duplicados = {m for m in pdf_muestras if pdf_muestras.count(m) > 1}
            
            # Procesar cada muestra del PDF
            pdf_procesadas = set()
            
            for pdf_muestra in self.pdf_data:
                muestra_norm = pdf_muestra['muestra_norm']
                
                # Verificar si es un duplicado
                if muestra_norm in duplicados and muestra_norm in pdf_procesadas:
                    self.resultados_comparacion['duplicados_factura'].append(pdf_muestra)
                    continue
                
                pdf_procesadas.add(muestra_norm)
                
                # Verificar si la muestra está en el Excel
                if muestra_norm in excel_dict:
                    excel_muestra = excel_dict[muestra_norm]
                    
                    # Verificar si hay coincidencia completa o parcial
                    coincidencia_completa = True
                    
                    # Verificar código Eix
                    if excel_muestra['codiEix'] != pdf_muestra['codiEix']:
                        coincidencia_completa = False
                    
                    # Verificar análisis (coincidencia parcial)
                    analisis_coincide = self._comparar_analisis(
                        excel_muestra['analisis'], 
                        pdf_muestra['analisis']
                    )
                    
                    if not analisis_coincide:
                        coincidencia_completa = False
                    
                    if coincidencia_completa:
                        self.resultados_comparacion['coincidencias'].append({
                            'excel': excel_muestra,
                            'pdf': pdf_muestra
                        })
                    else:
                        self.resultados_comparacion['coincidencias_parciales'].append({
                            'excel': excel_muestra,
                            'pdf': pdf_muestra
                        })
                else:
                    self.resultados_comparacion['factura_no_excel'].append(pdf_muestra)
            
            # Identificar muestras del Excel que no están en la factura
            pdf_muestras_set = {m['muestra_norm'] for m in self.pdf_data}
            
            for excel_muestra in self.excel_data:
                if excel_muestra['muestra_norm'] not in pdf_muestras_set:
                    self.resultados_comparacion['excel_no_factura'].append(excel_muestra)
            
            return True
            
        except Exception as e:
            st.error(f"Error al comparar muestras: {str(e)}")
            return False
    
    def _comparar_analisis(self, analisis_excel, analisis_pdf):
        """
        Compara descripciones de análisis para determinar si son equivalentes.
        
        Args:
            analisis_excel (str): Descripción del análisis en el Excel
            analisis_pdf (str): Descripción del análisis en el PDF
        
        Returns:
            bool: True si los análisis son equivalentes, False en caso contrario
        """
        if not analisis_excel or not analisis_pdf:
            return False
        
        # Normalizar textos
        analisis_excel = analisis_excel.lower()
        analisis_pdf = analisis_pdf.lower()
        
        # Verificar si uno contiene al otro
        if analisis_excel in analisis_pdf or analisis_pdf in analisis_excel:
            return True
        
        # Calcular similitud
        similarity = difflib.SequenceMatcher(None, analisis_excel, analisis_pdf).ratio()
        
        # Si la similitud es alta, considerar equivalentes
        return similarity > 0.7
    
    def obtener_estadisticas(self):
        """
        Calcula estadísticas de la comparación.
        
        Returns:
            dict: Diccionario con estadísticas
        """
        total_excel = len(self.excel_data)
        total_pdf = len(self.pdf_data)
        total_coincidencias = len(self.resultados_comparacion['coincidencias'])
        total_parciales = len(self.resultados_comparacion['coincidencias_parciales'])
        total_excel_no_factura = len(self.resultados_comparacion['excel_no_factura'])
        total_factura_no_excel = len(self.resultados_comparacion['factura_no_excel'])
        total_duplicados = len(self.resultados_comparacion['duplicados_factura'])
        
        # Determinar estado general
        if total_excel_no_factura == 0 and total_factura_no_excel == 0 and total_duplicados == 0 and total_parciales == 0:
            estado = "CORRECTO"
            color_estado = "success-text"
        elif total_excel_no_factura > 0 or total_factura_no_excel > 0 or total_duplicados > 0:
            estado = "DISCREPANCIAS IMPORTANTES"
            color_estado = "error-text"
        else:
            estado = "COINCIDENCIAS PARCIALES"
            color_estado = "warning-text"
        
        return {
            'total_excel': total_excel,
            'total_pdf': total_pdf,
            'total_coincidencias': total_coincidencias,
            'total_parciales': total_parciales,
            'total_excel_no_factura': total_excel_no_factura,
            'total_factura_no_excel': total_factura_no_excel,
            'total_duplicados': total_duplicados,
            'estado': estado,
            'color_estado': color_estado
        }

# Función principal de la aplicación Streamlit
def main():
    # Sidebar con información
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/000000/compare.png", width=100)
        st.title("Comparador de Muestras")
        st.markdown("### BRAUT EIX AMBIENTAL")
        st.markdown("---")
        st.markdown("""
        Esta aplicación compara muestras entre:
        - Archivo Excel de muestras enviadas
        - PDF de factura recibida
        
        Identifica:
        - Muestras no facturadas
        - Muestras facturadas incorrectamente
        - Muestras duplicadas
        """)
        st.markdown("---")
        st.markdown("Desarrollado con Streamlit")
    
    # Crear pestañas para las diferentes secciones
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Cargar Archivos", "Excel", "Factura", "Comparativa", "Discrepancias"])
    
    # Pestaña 1: Cargar Archivos
    with tab1:
        st.markdown("<h2 class='sub-header'>Cargar Archivos</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Archivo Excel de Muestras")
            excel_file = st.file_uploader("Seleccione el archivo Excel", type=['xlsx', 'xls'])
            if excel_file:
                st.success(f"Archivo Excel cargado: {excel_file.name}")
        
        with col2:
            st.markdown("### Archivo PDF de Factura")
            pdf_file = st.file_uploader("Seleccione el archivo PDF", type=['pdf'])
            if pdf_file:
                st.success(f"Archivo PDF cargado: {pdf_file.name}")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Botón para iniciar la comparación
        if st.button("COMPARAR ARCHIVOS", type="primary", use_container_width=True):
            if not excel_file or not pdf_file:
                st.error("Por favor, cargue ambos archivos (Excel y PDF) antes de comparar.")
            else:
                # Mostrar barra de progreso
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Iniciar el proceso de comparación
                status_text.text("Iniciando comparación...")
                progress_bar.progress(10)
                
                # Crear instancia del comparador
                comparador = ComparadorMuestras(excel_file, pdf_file)
                
                # Procesar Excel
                status_text.text("Procesando archivo Excel...")
                progress_bar.progress(30)
                if not comparador.procesar_excel():
                    st.error("Error al procesar el archivo Excel. Verifique el formato.")
                    return
                
                # Procesar PDF
                status_text.text("Procesando archivo PDF...")
                progress_bar.progress(50)
                if not comparador.procesar_pdf():
                    st.error("Error al procesar el archivo PDF. Verifique el formato.")
                    return
                
                # Comparar muestras
                status_text.text("Comparando muestras...")
                progress_bar.progress(70)
                if not comparador.comparar_muestras():
                    st.error("Error al comparar las muestras.")
                    return
                
                # Calcular estadísticas
                status_text.text("Generando resultados...")
                progress_bar.progress(90)
                estadisticas = comparador.obtener_estadisticas()
                
                # Completar
                progress_bar.progress(100)
                status_text.text("¡Comparación completada!")
                
                # Guardar resultados en la sesión
                st.session_state.excel_data = comparador.excel_data
                st.session_state.pdf_data = comparador.pdf_data
                st.session_state.resultados = comparador.resultados_comparacion
                st.session_state.estadisticas = estadisticas
                
                # Mostrar resumen
                st.markdown("<h3 class='sub-header'>Resumen de Resultados</h3>", unsafe_allow_html=True)
                st.markdown(f"""
                <div class='result-box'>
                    <p>Total muestras en Excel: <b>{estadisticas['total_excel']}</b></p>
                    <p>Total muestras en Factura: <b>{estadisticas['total_pdf']}</b></p>
                    <p>Coincidencias exactas: <span class='success-text'>{estadisticas['total_coincidencias']}</span> ({estadisticas['total_coincidencias']/estadisticas['total_excel']*100:.1f}% del Excel)</p>
                    <p>Coincidencias parciales: <span class='warning-text'>{estadisticas['total_parciales']}</span> ({estadisticas['total_parciales']/estadisticas['total_excel']*100:.1f}% del Excel)</p>
                    <p>Muestras del Excel no encontradas en factura: <span class='error-text'>{estadisticas['total_excel_no_factura']}</span> ({estadisticas['total_excel_no_factura']/estadisticas['total_excel']*100:.1f}% del Excel)</p>
                    <p>Muestras de la factura no encontradas en Excel: <span class='error-text'>{estadisticas['total_factura_no_excel']}</span></p>
                    <p>Muestras duplicadas en la factura: <span class='error-text'>{estadisticas['total_duplicados']}</span></p>
                    <p>ESTADO GENERAL: <span class='{estadisticas["color_estado"]}'>{estadisticas["estado"]}</span></p>
                </div>
                """, unsafe_allow_html=True)
                
                # Indicar que se revisen las otras pestañas
                st.info("Revise las pestañas 'Excel', 'Factura', 'Comparativa' y 'Discrepancias' para ver los detalles.")
    
    # Pestaña 2: Excel
    with tab2:
        st.markdown("<h2 class='sub-header'>Datos del Excel</h2>", unsafe_allow_html=True)
        
        if 'excel_data' in st.session_state:
            # Convertir a DataFrame para mostrar
            df_excel = pd.DataFrame(st.session_state.excel_data)
            
            # Seleccionar columnas relevantes
            columns_to_show = ['muestra', 'codiEix', 'analisis']
            df_display = df_excel[columns_to_show] if all(col in df_excel.columns for col in columns_to_show) else df_excel
            
            # Mostrar tabla
            st.dataframe(df_display, use_container_width=True)
            
            # Opción para descargar
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar datos Excel como CSV",
                data=csv,
                file_name='datos_excel.csv',
                mime='text/csv',
            )
        else:
            st.info("Cargue los archivos y realice la comparación para ver los datos del Excel.")
    
    # Pestaña 3: Factura
    with tab3:
        st.markdown("<h2 class='sub-header'>Datos de la Factura (PDF)</h2>", unsafe_allow_html=True)
        
        if 'pdf_data' in st.session_state:
            # Convertir a DataFrame para mostrar
            df_pdf = pd.DataFrame(st.session_state.pdf_data)
            
            # Seleccionar columnas relevantes
            columns_to_show = ['muestra', 'codiEix', 'analisis']
            df_display = df_pdf[columns_to_show] if all(col in df_pdf.columns for col in columns_to_show) else df_pdf
            
            # Mostrar tabla
            st.dataframe(df_display, use_container_width=True)
            
            # Opción para descargar
            csv = df_display.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Descargar datos Factura como CSV",
                data=csv,
                file_name='datos_factura.csv',
                mime='text/csv',
            )
        else:
            st.info("Cargue los archivos y realice la comparación para ver los datos de la factura.")
    
    # Pestaña 4: Comparativa
    with tab4:
        st.markdown("<h2 class='sub-header'>Comparativa de Muestras</h2>", unsafe_allow_html=True)
        
        if 'resultados' in st.session_state:
            # Mostrar coincidencias exactas
            st.markdown("<h3>Coincidencias Exactas</h3>", unsafe_allow_html=True)
            
            if st.session_state.resultados['coincidencias']:
                # Crear DataFrame para mostrar
                coincidencias_data = []
                for item in st.session_state.resultados['coincidencias']:
                    coincidencias_data.append({
                        'Muestra': item['excel']['muestra'],
                        'Código Eix': item['excel']['codiEix'],
                        'Análisis': item['excel']['analisis']
                    })
                
                df_coincidencias = pd.DataFrame(coincidencias_data)
                st.dataframe(df_coincidencias, use_container_width=True)
            else:
                st.warning("No se encontraron coincidencias exactas.")
            
            # Mostrar coincidencias parciales
            st.markdown("<h3>Coincidencias Parciales</h3>", unsafe_allow_html=True)
            
            if st.session_state.resultados['coincidencias_parciales']:
                # Crear DataFrame para mostrar
                parciales_data = []
                for item in st.session_state.resultados['coincidencias_parciales']:
                    parciales_data.append({
                        'Muestra': item['excel']['muestra'],
                        'Código Eix (Excel)': item['excel']['codiEix'],
                        'Código Eix (Factura)': item['pdf']['codiEix'],
                        'Análisis (Excel)': item['excel']['analisis'],
                        'Análisis (Factura)': item['pdf']['analisis']
                    })
                
                df_parciales = pd.DataFrame(parciales_data)
                st.dataframe(df_parciales, use_container_width=True)
                
                # Opción para descargar
                csv = df_parciales.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar coincidencias parciales como CSV",
                    data=csv,
                    file_name='coincidencias_parciales.csv',
                    mime='text/csv',
                )
            else:
                st.warning("No se encontraron coincidencias parciales.")
        else:
            st.info("Cargue los archivos y realice la comparación para ver la comparativa.")
    
    # Pestaña 5: Discrepancias
    with tab5:
        st.markdown("<h2 class='sub-header'>Discrepancias Encontradas</h2>", unsafe_allow_html=True)
        
        if 'resultados' in st.session_state:
            # 1. Muestras del Excel no encontradas en factura
            st.markdown("<h3>Muestras del Excel no encontradas en factura</h3>", unsafe_allow_html=True)
            
            if st.session_state.resultados['excel_no_factura']:
                # Crear DataFrame para mostrar
                excel_no_factura_data = []
                for item in st.session_state.resultados['excel_no_factura']:
                    excel_no_factura_data.append({
                        'Muestra': item['muestra'],
                        'Código Eix': item['codiEix'],
                        'Análisis': item['analisis']
                    })
                
                df_excel_no_factura = pd.DataFrame(excel_no_factura_data)
                st.dataframe(df_excel_no_factura, use_container_width=True)
                
                # Opción para descargar
                csv = df_excel_no_factura.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar muestras no facturadas como CSV",
                    data=csv,
                    file_name='muestras_no_facturadas.csv',
                    mime='text/csv',
                )
            else:
                st.success("Todas las muestras del Excel están en la factura.")
            
            # 2. Muestras de la factura no encontradas en Excel
            st.markdown("<h3>Muestras de la factura no encontradas en Excel</h3>", unsafe_allow_html=True)
            
            if st.session_state.resultados['factura_no_excel']:
                # Crear DataFrame para mostrar
                factura_no_excel_data = []
                for item in st.session_state.resultados['factura_no_excel']:
                    factura_no_excel_data.append({
                        'Muestra': item['muestra'],
                        'Código Eix': item['codiEix'],
                        'Análisis': item['analisis']
                    })
                
                df_factura_no_excel = pd.DataFrame(factura_no_excel_data)
                st.dataframe(df_factura_no_excel, use_container_width=True)
                
                # Opción para descargar
                csv = df_factura_no_excel.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar muestras facturadas no en Excel como CSV",
                    data=csv,
                    file_name='muestras_facturadas_no_en_excel.csv',
                    mime='text/csv',
                )
            else:
                st.success("Todas las muestras de la factura están en el Excel.")
            
            # 3. Muestras duplicadas en la factura
            st.markdown("<h3>Muestras duplicadas en la factura</h3>", unsafe_allow_html=True)
            
            if st.session_state.resultados['duplicados_factura']:
                # Crear DataFrame para mostrar
                duplicados_data = []
                for item in st.session_state.resultados['duplicados_factura']:
                    duplicados_data.append({
                        'Muestra': item['muestra'],
                        'Código Eix': item['codiEix'],
                        'Análisis': item['analisis']
                    })
                
                df_duplicados = pd.DataFrame(duplicados_data)
                st.dataframe(df_duplicados, use_container_width=True)
                
                # Opción para descargar
                csv = df_duplicados.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Descargar muestras duplicadas como CSV",
                    data=csv,
                    file_name='muestras_duplicadas.csv',
                    mime='text/csv',
                )
            else:
                st.success("No hay muestras duplicadas en la factura.")
        else:
            st.info("Cargue los archivos y realice la comparación para ver las discrepancias.")
    
    # Pie de página
    st.markdown("<div class='footer'>© 2025 BRAUT EIX AMBIENTAL - Comparador de Muestras v1.0</div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
