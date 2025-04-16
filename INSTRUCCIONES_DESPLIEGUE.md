# Instrucciones para Desplegar la Aplicación Comparador de Muestras

Estas instrucciones te guiarán paso a paso para desplegar permanentemente la aplicación Comparador de Muestras en Streamlit Community Cloud.

## Requisitos Previos
- Una cuenta de GitHub (gratuita)
- Conexión a internet

## Paso 1: Crear un Nuevo Repositorio en GitHub

1. Inicia sesión en tu cuenta de GitHub (https://github.com)
2. Haz clic en el botón "+" en la esquina superior derecha y selecciona "New repository"
3. Completa la información del repositorio:
   - Nombre del repositorio: `comparador-muestras` (o el nombre que prefieras)
   - Descripción (opcional): "Aplicación para comparar muestras entre Excel y PDF"
   - Visibilidad: Público (para usar Streamlit Community Cloud gratis)
   - No inicialices el repositorio con README, .gitignore o licencia
4. Haz clic en "Create repository"

## Paso 2: Subir los Archivos al Repositorio

1. En la página del repositorio vacío, verás instrucciones para subir archivos
2. Haz clic en el enlace "uploading an existing file"
3. Arrastra y suelta todos los archivos de la carpeta que has descomprimido (app.py, requirements.txt, README.md, icon.svg)
4. Escribe un mensaje de commit como "Versión inicial de la aplicación"
5. Haz clic en "Commit changes"

## Paso 3: Crear una Cuenta en Streamlit Community Cloud

1. Ve a https://streamlit.io/cloud
2. Haz clic en "Sign up" o "Get started"
3. Selecciona la opción para iniciar sesión con GitHub
4. Autoriza a Streamlit para acceder a tu cuenta de GitHub
5. Completa el proceso de registro si es necesario

## Paso 4: Desplegar la Aplicación

1. Una vez dentro de Streamlit Community Cloud, haz clic en "New app"
2. Selecciona tu repositorio `comparador-muestras` de la lista
3. En la configuración de la aplicación:
   - Branch: main (o master, dependiendo de cómo se llame tu rama principal)
   - Main file path: app.py
   - Deja las demás opciones con sus valores predeterminados
4. Haz clic en "Deploy"
5. Espera unos minutos mientras Streamlit despliega tu aplicación

## Paso 5: Acceder a la Aplicación

1. Una vez completado el despliegue, Streamlit te proporcionará una URL pública para tu aplicación
2. La URL tendrá un formato como: https://username-comparador-muestras-app.streamlit.app
3. Puedes compartir esta URL con cualquier persona que necesite usar la aplicación
4. La aplicación estará disponible permanentemente en esta URL

## Solución de Problemas

Si encuentras algún problema durante el despliegue:

1. Verifica que todos los archivos se hayan subido correctamente a GitHub
2. Asegúrate de que el archivo principal se llame "app.py"
3. Revisa los logs de error en Streamlit Community Cloud
4. Si el problema persiste, puedes contactar con el soporte de Streamlit o consultar su documentación

## Actualizar la Aplicación en el Futuro

Si necesitas actualizar la aplicación en el futuro:

1. Edita los archivos en tu repositorio de GitHub
2. Streamlit Community Cloud detectará los cambios automáticamente
3. La aplicación se actualizará con los nuevos cambios

¡Listo! Tu aplicación Comparador de Muestras ahora está desplegada permanentemente y accesible desde cualquier dispositivo con conexión a internet.
