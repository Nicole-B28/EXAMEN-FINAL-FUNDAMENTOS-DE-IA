"""SiembraVerde IA · Aplicación pública de apoyo a decisiones agrícolas.

Abrir: python -m streamlit run app.py
Datos: Open-Meteo (pronósticos y reanálisis), crédito en el pie.
"""
from __future__ import annotations
from datetime import datetime
from io import StringIO
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from clima import LUGARES, FuenteNoDisponible, buscar_lugar, historico, consultar_pronostico, enlace_historico
from analisis import evaluar_pronostico, recomendaciones
from modelo import entrenar_y_estimar, agrupar_patrones_historicos

st.set_page_config(page_title="SiembraVerde IA | Tu campo, mejor preparado", page_icon="🌱", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
[data-testid="stAppViewContainer"] {background:#f5f8f3;color:#173c2c}
[data-testid="stHeader"] {background:#f5f8f3}
.block-container{max-width:1100px;padding-top:1.8rem;padding-bottom:4rem}
h1,h2,h3,p{color:#173c2c}
h1{font-weight:800!important;letter-spacing:-.045em!important}
h2{letter-spacing:-.025em!important}
.stButton>button[kind="primary"], [data-testid="stBaseButton-primary"] {
background:#236348!important;color:white!important;border:1px solid #236348!important;
border-radius:12px!important;font-weight:750!important;min-height:3.3rem;
}
.stButton>button[kind="primary"]:hover {background:#164834!important}
.stButton>button[kind="primary"] *, [data-testid="stBaseButton-primary"] * {color:white!important}
[data-testid="stMetric"] {background:white;border:1px solid #dbe8db;border-radius:16px;padding:15px 18px}
[data-testid="stMetricLabel"] {color:#56725e!important}
[data-testid="stMetricValue"] {color:#163d2b!important}
[data-testid="stSelectbox"]>div, [data-testid="stTextInput"]>div {border-radius:11px}
[data-testid="stExpander"]{background:white;border:1px solid #dce6d9;border-radius:12px}
a{color:#1b694d!important}
.hero{background:linear-gradient(115deg,#103a2c 0%,#18543e 55%,#377653 100%);color:white;
padding:37px 42px;border-radius:23px;position:relative;overflow:hidden;margin-bottom:22px}
.hero h1{color:white!important;font-size:2.65rem!important;margin:.25rem 0 .7rem!important}
.hero p{color:#e1f1e4!important;font-size:1.03rem;max-width:720px;line-height:1.55;margin-bottom:.15rem}
.hero .eyebrow{font-size:.77rem;letter-spacing:.17em;font-weight:800;color:#badfbd}
.steps{background:#eaf2e8;border:1px solid #d6e5d4;border-radius:13px;padding:13px 20px;margin-bottom:25px;color:#315843;font-size:.94rem}
.sect{color:#163d2b;font-size:1.42rem;font-weight:800;letter-spacing:-.02em;margin:12px 0 4px}
.hint{color:#617767;font-size:.9rem;margin:0 0 10px}
.panel{background:white;border:1px solid #dae7d9;border-radius:16px;padding:18px 21px;margin:10px 0 15px}
.risk{border-radius:17px;padding:21px 24px;margin:16px 0 16px;border:1px solid transparent}
.risk strong{font-size:1.33rem;display:block;margin-bottom:6px}
.risk p{margin:0;line-height:1.6}
.risk-ALTO{background:#fff4de;border-color:#e9cb8c;color:#67460c}
.risk-ALTO strong,.risk-ALTO p{color:#67460c!important}
.risk-MEDIO{background:#f9f2d9;border-color:#e6d8aa;color:#5a531e}
.risk-MEDIO strong,.risk-MEDIO p{color:#5a531e!important}
.risk-BAJO{background:#e4f3e7;border-color:#b8dabe;color:#205837}
.risk-BAJO strong,.risk-BAJO p{color:#205837!important}
.disclaimer{font-size:.84rem;color:#697e70;line-height:1.5}
.action{background:#f0f6ed;border-left:4px solid #367852;border-radius:10px;padding:11px 16px;margin:9px 0;color:#244e36}
.footer{border-top:1px solid #dbe5da;padding:20px 0 0;margin-top:30px;color:#607a69;font-size:.83rem;line-height:1.7}
@media (max-width:700px){.hero{padding:26px 22px}.hero h1{font-size:2rem!important}.block-container{padding-top:.7rem}}
</style>""", unsafe_allow_html=True)

@st.cache_data(ttl=1800, show_spinner=False)
def cargar_pronostico(lat: float, lon: float):
    return consultar_pronostico(lat, lon, 14)

@st.cache_data(ttl=86400, show_spinner=False)
def cargar_historico(lat: float, lon: float):
    return historico(lat, lon, 4)

@st.cache_data(ttl=86400, show_spinner=False)
def perfil_zona(lat: float, lon: float, pasado: pd.DataFrame):
    return agrupar_patrones_historicos(cargar_historico(lat,lon), pasado)

@st.cache_data(ttl=86400, show_spinner=False)
def evaluar_modelos(lat: float, lon: float, pasado: pd.DataFrame):
    return entrenar_y_estimar(cargar_historico(lat,lon), pasado)

@st.cache_data(ttl=3600, show_spinner=False)
def resolver_busqueda(nombre: str, solo_ec: bool):
    return buscar_lugar(nombre, solo_ec)

st.markdown('''<div class="hero"><div class="eyebrow">🌿 EL CAMPO DECIDE MEJOR CON INFORMACIÓN</div>
<h1>SiembraVerde IA</h1><p>¿Vas a sembrar pronto? Descubre si se prevén días secos, lluvias intensas o frío; consulta qué revisar antes de sembrar. Claro, sencillo y pensado para el campo.</p></div>''', unsafe_allow_html=True)
st.markdown('''<div class="steps">📍 <b>1. Indica tu terreno</b> &nbsp;&nbsp; → &nbsp;&nbsp; 🌽 <b>2. Elige tu cultivo</b> &nbsp;&nbsp; → &nbsp;&nbsp; 🌧️ <b>3. Consulta y decide mejor</b></div>''', unsafe_allow_html=True)
st.markdown('<div class="sect">Conoce las condiciones de tu terreno</div><p class="hint">No necesitas saber de meteorología. Completa los campos y presiona el botón verde.</p>', unsafe_allow_html=True)

ubicacion_modo = st.radio("¿Cómo quieres indicar la ubicación?", ["Elegir localidad", "Buscar otra localidad", "Coordenadas del terreno"], horizontal=True, key="ubicacion_modo")
lat = lon = None
lugar_nombre = None
if ubicacion_modo == "Elegir localidad":
    lugar_nombre = st.selectbox("¿Dónde está tu terreno?", list(LUGARES), index=0)
    lat, lon = LUGARES[lugar_nombre]
elif ubicacion_modo == "Buscar otra localidad":
    c1,c2 = st.columns([3,1])
    with c1:
        texto = st.text_input("Escribe ciudad, parroquia o localidad", placeholder="Ejemplo: Pimampiro, Imbabura")
    with c2:
        solo_ec = st.toggle("Solo Ecuador", value=True, help="Desactívalo si necesitas consultar un lugar de otro país.")
    if st.button("🔎 Buscar localidades", disabled=len(texto.strip())<3):
        try:
            st.session_state["lugares_buscados"] = resolver_busqueda(texto, solo_ec)
            st.session_state["ultima_busqueda"] = texto
        except (FuenteNoDisponible, ValueError) as exc:
            st.error(str(exc))
    encontrados = st.session_state.get("lugares_buscados", [])
    if encontrados and st.session_state.get("ultima_busqueda") == texto:
        opcion = st.selectbox("Selecciona la ubicación correcta", range(len(encontrados)), format_func=lambda i: encontrados[i]["nombre"])
        lugar_nombre, lat, lon = encontrados[opcion]["nombre"], encontrados[opcion]["lat"], encontrados[opcion]["lon"]
    else:
        st.info("Escribe una localidad y presiona «Buscar localidades». También puedes utilizar coordenadas.")
else:
    c1,c2=st.columns(2)
    with c1: lat=st.number_input("Latitud (°)",min_value=-90.0,max_value=90.0,value=0.3517,format="%.5f",help="Se puede obtener de Google Maps tocando tu parcela.")
    with c2: lon=st.number_input("Longitud (°)",min_value=-180.0,max_value=180.0,value=-78.1223,format="%.5f")
    lugar_nombre = f"Terreno {lat:.4f}, {lon:.4f}"

c1,c2,c3=st.columns([1.2,1,1])
with c1:
    cultivo=st.selectbox("¿Qué quieres sembrar?",["Maíz","Fréjol","Papa","Hortalizas","Arroz","Otro cultivo"], help="Se usa para orientar los consejos. El riesgo de poca lluvia se calcula igual para todos los cultivos.")
with c2:
    riego=st.selectbox("¿Tienes acceso a riego?",["No","Sí"],help="El riego cambia las recomendaciones, no el pronóstico de lluvia.")
with c3:
    suelo=st.selectbox("¿Cómo está el suelo ahora?",["No sé","Seco","Húmedo"],help="Responde según observación del terreno; la app no mide directamente la humedad del suelo.")

consultar = st.button("🌱 Consultar mi terreno", type="primary", use_container_width=True, disabled=lat is None or lon is None)
if consultar:
    st.session_state.pop("resultado_consulta",None)
    with st.spinner("Consultando el pronóstico meteorológico…"):
        try:
            consulta = cargar_pronostico(float(lat),float(lon))
            resultado = evaluar_pronostico(consulta.futuro)
            st.session_state["resultado_consulta"] = dict(lat=float(lat),lon=float(lon),nombre=lugar_nombre,cultivo=cultivo,riego=riego,suelo=suelo,consulta=consulta,resultado=resultado)
        except (FuenteNoDisponible, ValueError) as exc:
            st.error(f"No pudimos consultar la lluvia de este terreno. {exc}")
            st.info("No mostramos predicciones inventadas. Verifica tu conexión o consulta el pronóstico agroclimático del INAMHI.")
            st.markdown("[Consultar INAMHI](https://servicios.inamhi.gob.ec/pronostico-agroclimatico-decadal/)")

if 'resultado_consulta' in st.session_state:
    q=st.session_state['resultado_consulta']
    res=q['resultado']
    consulta=q['consulta']
    futuro=consulta.futuro
    pasado=consulta.pasado
    st.divider()
    st.markdown('## 🌿 Resultado para tu terreno')
    st.write(f'**Ubicación:** {q["nombre"]} · **Cultivo:** {q["cultivo"]} · **Riego:** {q["riego"]} · **Suelo observado:** {q["suelo"]}')
    st.caption(f'Pronóstico desde {res.fecha_inicio} hasta {res.fecha_fin} · Fuente: Open-Meteo · Zona horaria: {consulta.zona}. La evaluación principal cubre 7 días.')
    icono={'ALTO':'⚠️','MEDIO':'🔎','BAJO':'🌱'}[res.nivel]
    st.markdown(f'<div class="risk risk-{res.nivel}"><strong>{icono} {res.titular}</strong><p>{res.motivo}</p></div>',unsafe_allow_html=True)

    # Etiquetas cortas para móviles y pantallas pequeñas.
    # La explicación de cada indicador se conserva en el icono de ayuda.
    def etiqueta(nivel):
        return {'ALTO':'Precaución','MEDIO':'Vigilar','BAJO':'Sin alerta',
                'ATENCION':'Vigilar','SIN_ALERTA':'Sin alerta'}[nivel]
    col1,col2,col3=st.columns(3)
    col1.metric('Poca lluvia',etiqueta(res.riesgo_seco),help='Riesgo de días casi secos. Se evalúa por separado de las lluvias fuertes.')
    col2.metric('Mucha lluvia',etiqueta(res.riesgo_exceso),help='Revisa precipitación diaria y acumulada. El umbral es orientativo, no oficial.')
    col3.metric('Frío',etiqueta(res.riesgo_frio),help='Usa temperatura mínima del aire. No es una medición en el terreno.')

    st.markdown('### 🌧️ ¿Cuánta agua podría caer?')
    a,b,c=st.columns(3)
    a.metric('Precipitación de los próximos 7 días',f'{res.lluvia_7d:.1f} mm',help='Suma de los primeros siete valores diarios de precipitation_sum de Open-Meteo.')
    b.metric('Día de lluvia más intensa',f'{res.max_lluvia_dia:.1f} mm',help=f'Fecha: {res.dia_max_lluvia}. Es cantidad prevista en un solo día.')
    c.metric('Racha máxima casi seca',f'{res.racha_7d} días',help='Días consecutivos con menos de 1 mm diario; umbral operativo educativo.')
    if res.lluvia_14d is not None:
        st.caption(f'En 14 días se estiman **{res.lluvia_14d:.1f} mm**. Ten en cuenta que la segunda semana es menos confiable que la primera.')
    else:
        st.caption('La fuente no entregó los 14 días completos: no se calcula ese acumulado.')

    st.markdown('### 💬 ¿Qué significan estos resultados?')
    st.write(f'**1 mm de precipitación representa aproximadamente 1 litro de agua sobre cada metro cuadrado.** Si los {res.lluvia_7d:.1f} mm previstos cayeran tal como se pronostican, equivaldrían a {res.lluvia_7d:.1f} litros por metro cuadrado a lo largo de una semana. Eso NO quiere decir que toda esa agua quede almacenada en el suelo: una parte puede escurrir, filtrarse o evaporarse.')
    if res.riesgo_exceso=='ALTO':
        st.warning(f'**Atención al exceso de agua.** Aunque no haya días secos, {res.lluvia_7d:.1f} mm en siete días y un máximo de {res.max_lluvia_dia:.1f} mm en una jornada pueden complicar la preparación del terreno. Revisa drenajes, pendiente, infiltración y encharcamiento antes de sembrar. Los umbrales son orientativos.')
    elif res.riesgo_seco=='ALTO':
        st.warning(f'**Atención a la falta de agua.** La mayor racha de {res.racha_7d} días con menos de 1 mm puede dificultar el establecimiento si no hay humedad o riego suficiente. Confirma la humedad real del suelo.')
    elif res.nivel=='BAJO':
        st.success('**Sin alerta meteorológica fuerte en este indicador.** Esto no equivale a una recomendación automática de sembrar: la humedad del suelo, el drenaje y la variedad son determinantes.')
    else:
        st.info('**Situación para revisar:** hay factores que aconsejan comprobar el terreno. Las cifras son pronósticos y no mediciones de tu parcela.')
    if res.et0_7d is not None:
        with st.expander('¿Qué es la evapotranspiración (ET₀)?'):
            st.write(f'Open-Meteo estima **{res.et0_7d:.1f} mm de ET₀** durante los próximos siete días. Es una referencia de la demanda atmosférica de evaporación y transpiración de una superficie estándar de pasto bien regado, **no** el agua exacta que necesitará tu cultivo ni la humedad medida de tu terreno.')

    st.markdown('### ✅ Qué puedes revisar antes de sembrar')
    for i, texto in enumerate(recomendaciones(res,q['cultivo'],q['riego'],q['suelo']),1):
        st.markdown(f'<div class="action"><b>{i}.</b> {texto}</div>',unsafe_allow_html=True)

    st.markdown('### 📊 Lluvia prevista día por día')
    st.caption('Arena: menos de 1 mm · Verde: entre 1 y 25 mm · Azul: al menos 25 mm. Son rangos visuales de esta aplicación, no alertas oficiales.')
    colores=['#c59b58' if x<1 else ('#3f7da5' if x>=25 else '#43845a') for x in futuro.lluvia_mm.fillna(0)]
    graf=go.Figure()
    graf.add_bar(x=futuro.fecha,y=futuro.lluvia_mm,marker_color=colores,
        customdata=futuro[['tmin_c','tmax_c']].to_numpy(),
        hovertemplate='%{x|%d/%m/%Y}<br>Precipitación: %{y:.1f} mm<br>Temperatura mín.: %{customdata[0]:.1f} °C<br>Temperatura máx.: %{customdata[1]:.1f} °C<extra></extra>')
    if len(futuro)>=8:
        graf.add_vrect(x0=futuro.fecha.iloc[7]-pd.Timedelta(hours=12),x1=futuro.fecha.iloc[-1]+pd.Timedelta(hours=12),
            fillcolor='#d8e1d5',opacity=.25,line_width=0)
    graf.update_layout(height=360,margin=dict(l=8,r=8,t=12,b=12),plot_bgcolor='white',paper_bgcolor='rgba(0,0,0,0)',
        showlegend=False,xaxis_title='Fecha',yaxis_title='Precipitación prevista (mm)',font=dict(color='#174532'))
    graf.update_yaxes(gridcolor='#e1ebe0',rangemode='tozero')
    st.plotly_chart(graf,use_container_width=True,config={'displayModeBar':False})
    st.caption('El gráfico utiliza directamente la serie diaria de la API; la semana sombreada es menos confiable. Las lluvias intensas en zonas montañosas pueden diferir mucho entre la celda del modelo y una finca específica.')

    st.markdown('### 🔍 Comprueba los datos originales')
    st.write('La aplicación **no inventa las lluvias**. Consulta Open-Meteo y recalcula su suma. Puedes abrir la misma consulta y comprobar cada día, columna por columna.')
    va,vb=st.columns(2)
    va.metric('Suma de la respuesta original',f'{consulta.api_7d:.1f} mm')
    vb.metric('Suma calculada por la app',f'{consulta.calculo_7d:.1f} mm')
    st.success('✅ Comprobación automática: los dos acumulados coinciden.')
    st.link_button('Abrir datos originales en Open-Meteo ↗', consulta.url)
    st.caption(f'Consultado: {consulta.consultado_utc} (UTC) · Coordenadas solicitadas: {consulta.lat_peticion:.4f}, {consulta.lon_peticion:.4f} · Celda del modelo: {consulta.lat_modelo}, {consulta.lon_modelo} · Altitud modelada: {consulta.altitud_modelo} m.')
    with st.expander('Ver tabla diaria y descargar datos'):
        tabla=futuro[['fecha','lluvia_mm','tmin_c','tmax_c','et0_mm']].copy()
        tabla.columns=['Fecha','Precipitación (mm)','Temperatura mínima (°C)','Temperatura máxima (°C)','ET₀ (mm)']
        st.dataframe(tabla,hide_index=True,use_container_width=True)
        st.download_button('⬇️ Descargar CSV de esta consulta',tabla.to_csv(index=False).encode('utf-8-sig'),
            file_name='SiembraVerde_pronostico_OpenMeteo.csv',mime='text/csv')
        st.caption('La API puede actualizar sus predicciones; si la abres después, podrían variar los números. El CSV conserva los datos de la consulta mostrada.')

    with st.expander('🧠 Análisis histórico con inteligencia artificial (complementario)'):
        st.write('Este análisis utiliza **regresión logística, KNN y KMeans**, estudiados en Fundamentos de IA. Se aplica a series históricas de reanálisis y **no es la fuente de la precipitación prevista**. La IA solo aparece si podemos evaluarla con datos posteriores a los de entrenamiento.')
        st.caption('KMeans agrupa semanas similares; no pronostica la lluvia futura. El clasificador explora rachas de al menos 3 días con menos de 1 mm en los siguientes 7 días.')
        if st.button('Consultar historial y evaluar IA',key='ejecutar_ia'):
            with st.spinner('Obteniendo historial ERA5/ERA5-Land y evaluando modelos…'):
                try:
                    hist=cargar_historico(q['lat'],q['lon'])
                    ai=entrenar_y_estimar(hist,pasado)
                    perfil=agrupar_patrones_historicos(hist,pasado)
                    st.session_state['ia_evaluada']={'coordenadas':(q['lat'],q['lon']),'ai':ai,'perfil':perfil,'fuente':hist.attrs.get('producto_reanalisis','ERA5')}
                except FuenteNoDisponible as exc:
                    st.session_state.pop('ia_evaluada',None)
                    st.warning('El pronóstico en tiempo real sigue funcionando, pero no se consiguió el historial para entrenar la IA.')
                    st.caption('Diagnóstico de conexión/servicio: '+str(exc))
        ia_datos=st.session_state.get('ia_evaluada')
        if ia_datos and ia_datos['coordenadas']==(q['lat'],q['lon']):
            ai=ia_datos['ai']; perfil=ia_datos['perfil']
            st.caption(f'Historial: Open-Meteo, producto {ia_datos["fuente"]}; separación cronológica de entrenamiento y prueba.')
            st.link_button('Ver el JSON histórico de este terreno ↗',enlace_historico(q['lat'],q['lon'],modelo=ia_datos['fuente']))
            if ai.ba is not None:
                st.write(f'**Clasificador evaluado:** {ai.nombre} · Exactitud equilibrada de prueba: **{ai.ba:.2f}**, método básico: **{ai.base_ba:.2f}** · F1: **{ai.f1:.2f}**.')
            if ai.probabilidad is None:
                st.info(ai.mensaje)
            else:
                st.write('**Señal exploratoria de IA:** '+('el patrón reciente sugiere vigilar períodos casi secos.' if ai.probabilidad>=.5 else 'el patrón reciente no presenta una señal fuerte de período casi seco.'))
                st.caption('No es una probabilidad meteorológica calibrada; para decidir se utiliza el pronóstico diario de Open-Meteo y la observación del terreno.')
            if perfil:
                st.write(f'**KMeans:** la semana reciente se asemeja al grupo {perfil.descripcion}; las semanas similares acumularon en promedio {perfil.promedio_grupo_mm:.1f} mm en el historial.')
        st.markdown('[Consultar los datos históricos ERA5/ERA5-Land](https://open-meteo.com/en/docs/historical-weather-api)')

    with st.expander('📚 Cómo leer las alertas y de dónde vienen los criterios'):
        st.markdown('''- **Día casi seco:** menos de 1 mm de precipitación. Una racha de 5 días se considera señal importante en este **prototipo educativo**.
- **Lluvia importante:** a partir de 25 mm en un día se aconseja revisar drenaje; 50 mm en un día o 100 mm acumulados en una semana activa precaución mayor. **No son umbrales oficiales de Ecuador ni recomendaciones validadas para todos los cultivos.**
- **Frío:** mínima del aire de 2 °C o menos activa una revisión, **no confirma heladas**.
- **Cultivo, riego y humedad:** cambian los consejos, pero no cambian los milímetros que predice el servicio meteorológico.
- **Resultado verificable:** los números vienen del API. Su *acierto futuro* no puede confirmarse hasta que transcurran los días; para evaluarlo se necesitan observaciones independientes.
- **Terreno:** temperatura, lluvias y elevación son valores aproximados de una celda meteorológica; no sustituyen sensores ni inspección del suelo.''')
        st.markdown('[Documentación de la API Open-Meteo](https://open-meteo.com/en/docs) · [INAMHI](https://servicios.inamhi.gob.ec/) · [FAO, manejo del agua](https://www.fao.org/land-water/water/water-management/en/)')

st.markdown('''<div class="footer">🌳 <b>SiembraVerde IA</b> · Herramienta educativa de orientación previa a la siembra, no recomendación definitiva de fecha ni diagnóstico de sequía. Los umbrales son experimentales y requieren validación agronómica local.<br>Pronóstico y reanálisis: <a href="https://open-meteo.com/" target="_blank">Open-Meteo</a> (CC BY 4.0). Información oficial complementaria: <a href="https://servicios.inamhi.gob.ec/" target="_blank">INAMHI Ecuador</a>. Antes de sembrar, revisa directamente tu suelo y las alertas locales.</div>''',unsafe_allow_html=True)
