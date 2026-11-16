# SiembraVerde IA · Versión mejorada

**Aplicación de consulta agrícola para agricultores**, con interfaz verde bosque. No es un informe académico: permite consultar el terreno, conocer la precipitación prevista y recibir precauciones antes de sembrar.

## Qué corrige frente a la versión inicial

- Antes solo se calculaban rachas secas. Ahora se evalúan **por separado** poca lluvia, exceso de precipitación y frío.
- Una semana de 214 mm ya **no** aparece como «lluvias favorables»; genera advertencia de drenaje.
- Consejos adaptados a cultivo, disponibilidad de riego y humedad observada del terreno.
- Resumen que explica qué significa la lluvia en milímetros y por qué la precipitación no garantiza suelo húmedo o apto.
- Consulta exacta a **Open-Meteo**, verificable mediante enlace, valores diarios, sumas, fecha, coordenadas y CSV descargable.
- El análisis histórico con regresión logística, KNN y KMeans es complementario y se ejecuta solo si el usuario lo solicita. Cuando la fuente falla, explica el motivo y **no inventa resultados**.
- Se conservaron bibliotecas y enfoques del módulo: Pandas, Scikit-learn, clasificación, KMeans y Streamlit.

## Instalar en Visual Studio Code (PowerShell, Windows)

Abrir la carpeta `SiembraVerde_IA_Mejorada`, luego:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Si PowerShell bloquea la activación de scripts, **no es necesario activar** el entorno; estos comandos usan Python directamente.

Abrir en navegador la **Local URL** que muestre Streamlit, por ejemplo `http://localhost:8501` (el puerto puede variar si hay otras apps ejecutándose).

## Comprobar con el profesor los valores del API

Desde una segunda terminal, dentro del proyecto:

```powershell
.\.venv\Scripts\python.exe comprobar_fuentes.py
```

El script consulta **en directo** las coordenadas de Quito usadas por defecto y muestra:

1. Dirección API exacta con sus parámetros.
2. Fechas y valores diarios de `precipitation_sum`.
3. Suma de los siete días a partir del JSON.
4. Suma de la aplicación; ambas deben coincidir.

Para verificar otra ubicación:

```powershell
.\.venv\Scripts\python.exe comprobar_fuentes.py --lat 0.3517 --lon -78.1223
```

**Precisión importante:** los números del servicio son **pronósticos meteorológicos auténticos, NO lluvia futura observada**. El hecho de que coincidan con la API comprueba origen y aritmética, **no que necesariamente se cumplan**. Para verificar el acierto deben compararse más tarde con observaciones independientes (estación meteorológica, pluviómetro con mediciones documentadas, etc.). Open-Meteo puede actualizar el pronóstico entre dos consultas; el CSV descargado conserva los resultados de la consulta original.

## Cómo comprobar el análisis IA

En la app, abrir **«Análisis histórico con inteligencia artificial»** y pulsar **«Consultar historial y evaluar IA»**. Se intenta descargar ERA5-Land o ERA5 desde Open-Meteo. Las evaluaciones se separan cronológicamente en entrenamiento, validación y prueba, con margen temporal para no filtrar información futura. Se comparan los clasificadores con un método de referencia. Si faltan clases, hay fallas de conexión o el método no supera la referencia, **no se presenta una señal de IA como confiable**.

El indicador meteorológico principal no depende de que se pueda descargar el archivo histórico. KMeans es una **segmentación descriptiva de semanas**, no un predictor meteorológico.

## Fuentes originales

- [Open-Meteo · Forecast API](https://open-meteo.com/en/docs)
- [Open-Meteo · Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api)
- [Open-Meteo · Licencia de datos CC BY 4.0](https://open-meteo.com/en/license)
- [INAMHI · Servicios meteorológicos de Ecuador](https://servicios.inamhi.gob.ec/)
- [FAO · Impactos de exceso de lluvia en la siembra (anexo 12)](https://www.fao.org/4/i0515e/i0515e19.pdf)
- [FAO · Manejo de encharcamiento y drenaje](https://www.fao.org/4/x8234e/x8234e08.htm)

## Limitaciones que se deben mencionar

- El modelo utiliza celdas meteorológicas, no mediciones dentro de cada finca.
- Umbrales 1/25/50/100 mm y 2 °C son **decisiones operativas educativas**, no normas oficiales ni reglas de siembra validadas para todos los cultivos.
- El estado del suelo lo declara el agricultor. No se mide mediante sensores.
- Que no haya alerta fuerte **no equivale a un permiso automático para sembrar**.
- La segunda semana del pronóstico tiene más incertidumbre.
- La API de Open-Meteo gratuita es para usos **no comerciales** y exige atribución. Si el servicio se usa comercialmente deben revisarse sus condiciones.

## Publicación

- Repositorio GitHub con `app.py`, `analisis.py`, `clima.py`, `modelo.py`, `comprobar_fuentes.py`, `requirements.txt` y `.streamlit/config.toml`.
- Abrir [Streamlit Community Cloud](https://share.streamlit.io/), seleccionar repositorio, rama y `app.py`.
- Validar desde navegador privado y otro dispositivo; verificar API y botones.
- Evitar subir `.venv` (`.gitignore` ya la excluye).

**Control de calidad realizado en el entorno de elaboración:** 21 pruebas automatizadas de la lógica y la integridad de datos simulados/mock. La conexión en vivo a Open-Meteo y el despliegue en Streamlit deberán ejecutarse desde un equipo con acceso a la API. Ningún resultado real de pronóstico se ha fabricado para este paquete.
