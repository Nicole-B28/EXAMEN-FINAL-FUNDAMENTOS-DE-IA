"""Fuentes Open-Meteo. Valores sin modificar, unidades y URL verificables.

Un pronóstico es una estimación meteorológica; no es una observación futura.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta, datetime, timezone
from urllib.parse import urlencode
import math
import pandas as pd
import requests

FORECAST_URL = 'https://api.open-meteo.com/v1/forecast'
ARCHIVE_URL = 'https://archive-api.open-meteo.com/v1/archive'
GEOCODE_URL = 'https://geocoding-api.open-meteo.com/v1/search'
VARS = 'precipitation_sum,temperature_2m_max,temperature_2m_min,et0_fao_evapotranspiration'

LUGARES = {
    'Ibarra · Imbabura': (0.3517, -78.1223),
    'Otavalo · Imbabura': (0.2346, -78.2625),
    'Quito · Pichincha': (-0.1807, -78.4678),
    'Cayambe · Pichincha': (0.0408, -78.1450),
    'Machachi · Pichincha': (-0.5141, -78.5660),
    'Latacunga · Cotopaxi': (-0.9352, -78.6155),
    'Ambato · Tungurahua': (-1.2491, -78.6167),
    'Riobamba · Chimborazo': (-1.6636, -78.6546),
    'Cuenca · Azuay': (-2.9001, -79.0059),
    'Loja · Loja': (-3.9931, -79.2042),
    'Guaranda · Bolívar': (-1.5926, -79.0009),
    'Tulcán · Carchi': (0.8119, -77.7173),
    'Santo Domingo · Santo Domingo': (-0.2522, -79.1719),
    'Quevedo · Los Ríos': (-1.0286, -79.4635),
    'Babahoyo · Los Ríos': (-1.8022, -79.5344),
    'Daule · Guayas': (-1.8622, -79.9787),
    'Guayaquil · Guayas': (-2.1709, -79.9224),
    'Machala · El Oro': (-3.2581, -79.9554),
    'Portoviejo · Manabí': (-1.0546, -80.4544),
    'Santa Elena · Santa Elena': (-2.2267, -80.8587),
    'Esmeraldas · Esmeraldas': (0.9682, -79.6517),
    'Tena · Napo': (-0.9938, -77.8129),
    'Puyo · Pastaza': (-1.4929, -77.9969),
    'Nueva Loja · Sucumbíos': (0.0864, -76.8913),
}

class FuenteNoDisponible(RuntimeError):
    pass

@dataclass
class Consulta:
    pasado: pd.DataFrame
    futuro: pd.DataFrame
    zona: str
    url: str
    consultado_utc: str
    lat_peticion: float
    lon_peticion: float
    lat_modelo: float | None
    lon_modelo: float | None
    altitud_modelo: float | None
    unidades: str
    verificacion: str
    api_7d: float
    calculo_7d: float


def _validar_coordenadas(lat: float, lon: float):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError('La latitud o longitud está fuera del rango permitido.')


def parametros_pronostico(lat: float, lon: float, dias: int=14) -> dict:
    _validar_coordenadas(lat, lon)
    return {
        'latitude': round(float(lat), 4), 'longitude': round(float(lon), 4),
        'daily': VARS, 'past_days': 35, 'forecast_days': int(dias),
        'timezone': 'auto', 'precipitation_unit': 'mm', 'temperature_unit': 'celsius',
    }


def enlace_datos(lat: float, lon: float, dias: int=14) -> str:
    # La página usa exactamente los mismos parámetros para consultar y auditar.
    return FORECAST_URL + '?' + urlencode(parametros_pronostico(lat, lon, dias))


def _solicitud(url: str, parametros: dict) -> dict:
    try:
        resp = requests.get(url, params=parametros, timeout=(8, 32),
            headers={'User-Agent':'SiembraVerdeIA/2.0 (proyecto academico; fuentes verificables)'})
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout as exc:
        raise FuenteNoDisponible('La consulta meteorológica agotó el tiempo de espera. Vuelve a intentar.') from exc
    except requests.HTTPError as exc:
        code = exc.response.status_code if exc.response is not None else '?'
        raise FuenteNoDisponible(f'El servidor meteorológico respondió HTTP {code}.') from exc
    except (requests.RequestException, ValueError) as exc:
        raise FuenteNoDisponible('No fue posible conectarse con Open-Meteo.') from exc
    if not isinstance(data, dict):
        raise FuenteNoDisponible('Open-Meteo no devolvió un objeto JSON válido.')
    if data.get('error'):
        raise FuenteNoDisponible('Open-Meteo rechazó la consulta: ' + str(data.get('reason','motivo no informado')))
    return data


def _a_diario(payload: dict) -> pd.DataFrame:
    diario=payload.get('daily')
    if not isinstance(diario,dict) or 'time' not in diario or 'precipitation_sum' not in diario:
        raise FuenteNoDisponible('La respuesta no incluye precipitación diaria.')
    unidades=payload.get('daily_units') or {}
    if unidades.get('precipitation_sum','mm') != 'mm':
        raise FuenteNoDisponible('La precipitación no está expresada en milímetros; no se calcularán resultados erróneos.')
    try:
        df=pd.DataFrame(diario)
    except ValueError as exc:
        raise FuenteNoDisponible('La fuente devolvió columnas de diferente longitud.') from exc
    df['fecha']=pd.to_datetime(df['time'],errors='coerce').dt.normalize()
    for col in ('precipitation_sum','temperature_2m_max','temperature_2m_min','et0_fao_evapotranspiration'):
        if col not in df: df[col] = float('nan')
        df[col] = pd.to_numeric(df[col],errors='coerce')
    df=df.rename(columns={'precipitation_sum':'lluvia_mm','temperature_2m_max':'tmax_c',
        'temperature_2m_min':'tmin_c','et0_fao_evapotranspiration':'et0_mm'})
    df=df[['fecha','lluvia_mm','tmax_c','tmin_c','et0_mm']]
    if df.fecha.isna().any() or df.fecha.duplicated().any() or df.lluvia_mm.dropna().lt(0).any():
        raise FuenteNoDisponible('La fuente devolvió fechas inválidas o precipitación negativa.')
    return df.sort_values('fecha').reset_index(drop=True)


def _es_continuo(df:pd.DataFrame)->bool:
    return bool(len(df)>0 and df.fecha.diff().dropna().eq(pd.Timedelta(days=1)).all())


def consultar_pronostico(lat:float,lon:float,dias:int=14)->Consulta:
    params=parametros_pronostico(lat,lon,dias)
    recibido=datetime.now(timezone.utc)
    data=_solicitud(FORECAST_URL,params)
    df=_a_diario(data)
    segundos=int(data.get('utc_offset_seconds',0))
    fecha_local=pd.Timestamp((recibido+timedelta(seconds=segundos)).date())
    pasado=df.loc[df.fecha<fecha_local].copy()
    futuro=df.loc[df.fecha>=fecha_local].head(dias).copy().reset_index(drop=True)
    if len(futuro)<7 or futuro.lluvia_mm.iloc[:7].isna().any() or not _es_continuo(futuro):
        raise FuenteNoDisponible('Faltan fechas consecutivas o datos de lluvia para los próximos siete días.')
    bruto=pd.DataFrame(data['daily'])
    bruto['fecha']=pd.to_datetime(bruto['time'],errors='coerce').dt.normalize()
    original=bruto.loc[bruto.fecha>=fecha_local].head(7)['precipitation_sum'].astype(float)
    suma_original=round(float(original.sum()),4)
    suma_proyecto=round(float(futuro.lluvia_mm.head(7).sum()),4)
    if not math.isclose(suma_original,suma_proyecto,rel_tol=0,abs_tol=.0001):
        raise FuenteNoDisponible('No coincide el acumulado original con el calculado por la aplicación.')
    return Consulta(
        pasado=pasado,futuro=futuro,zona=str(data.get('timezone','auto')),
        url=FORECAST_URL+'?'+urlencode(params),consultado_utc=recibido.isoformat(timespec='seconds'),
        lat_peticion=float(lat),lon_peticion=float(lon),
        lat_modelo=data.get('latitude'),lon_modelo=data.get('longitude'),
        altitud_modelo=data.get('elevation'),unidades='mm',
        verificacion='COINCIDEN',api_7d=suma_original,calculo_7d=suma_proyecto,
    )


def pronostico_y_pasado(lat: float,lon:float,dias:int=14):
    """Compatibilidad con el código y pruebas originales."""
    c=consultar_pronostico(lat,lon,dias)
    return c.pasado,c.futuro,c.zona


def historico(lat:float,lon:float,anos:int=4)->pd.DataFrame:
    """Datos de reanálisis. Una falla no debe convertirse en predicción inventada."""
    _validar_coordenadas(lat,lon)
    fin=date.today()-timedelta(days=12)
    inicio=fin-timedelta(days=round(365.25*anos))
    base={'latitude':round(float(lat),4),'longitude':round(float(lon),4),
          'start_date':inicio.isoformat(),'end_date':fin.isoformat(),
          'daily':VARS,'timezone':'auto'}
    errores=[]
    # Si el producto ERA5-Land no sirve en esta ubicación/fecha, probar ERA5.
    for producto in ('era5_land','era5'):
        try:
            datos=_solicitud(ARCHIVE_URL,{**base,'models':producto})
            df=_a_diario(datos)
            df=df.dropna(subset=['lluvia_mm','tmax_c','et0_mm'])
            if len(df)<500 or not _es_continuo(df):
                raise FuenteNoDisponible('historial incompleto o con fechas faltantes')
            df.attrs['producto_reanalisis']=producto
            return df
        except FuenteNoDisponible as exc:
            errores.append(f'{producto}: {exc}')
    raise FuenteNoDisponible('No se consiguió historial suficiente. '+' | '.join(errores))


def enlace_historico(lat:float,lon:float,anos:int=4,modelo:str='era5')->str:
    """URL reproducible del producto histórico utilizado para entrenamiento."""
    _validar_coordenadas(lat,lon)
    fin=date.today()-timedelta(days=12)
    inicio=fin-timedelta(days=round(365.25*anos))
    return ARCHIVE_URL+'?'+urlencode({'latitude':round(float(lat),4),
        'longitude':round(float(lon),4),'start_date':inicio.isoformat(),
        'end_date':fin.isoformat(),'daily':VARS,'timezone':'auto','models':modelo})


def buscar_lugar(nombre:str,solo_ecuador:bool=True)->list[dict]:
    if len(nombre.strip())<3: raise ValueError('Escribe por lo menos tres caracteres para buscar.')
    params={'name':nombre.strip()[:80],'count':8,'language':'es'}
    if solo_ecuador: params['countryCode']='EC'
    data=_solicitud(GEOCODE_URL,params)
    return [dict(nombre=', '.join(v for v in [x.get('name'),x.get('admin1'),x.get('country')] if v),
                lat=x['latitude'],lon=x['longitude']) for x in data.get('results',[])
            if x.get('latitude') is not None and x.get('longitude') is not None]
