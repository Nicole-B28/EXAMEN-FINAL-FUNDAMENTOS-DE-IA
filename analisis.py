"""Alertas de pre-siembra: umbrales transparentes de DEMOSTRACIÓN, NO NORMAS AGRONÓMICAS.
Se evalúan por separado sequedad, precipitación excesiva y frío.
"""
from dataclasses import dataclass
import pandas as pd

UMBRAL_CASI_SECO_MM = 1.0
RACHA_SECA_ATENCION = 3
RACHA_SECA_ALTA = 5
UMBRAL_LLUVIOSO_DIA_MM = 25.0
UMBRAL_LLUVIOSO_DIA_ALTO_MM = 50.0
UMBRAL_SEMANA_LLUVIA_ALTA_MM = 100.0
UMBRAL_HELADA_PRECAUCION_C = 2.0

@dataclass
class Resultado:
    nivel:str
    titular:str
    lluvia_7d:float
    lluvia_14d:float | None
    dias_secos_7d:int
    racha_7d:int
    lluvia_3d:float
    et0_7d:float | None
    fecha_inicio:str
    fecha_fin:str
    motivo:str
    riesgo_seco:str
    riesgo_exceso:str
    riesgo_frio:str
    max_lluvia_dia:float
    dias_lluviosos_7d:int
    temperatura_min:float | None
    dia_max_lluvia:str


def racha_maxima(es_seco)->int:
    actual=mejor=0
    for seco in es_seco:
        actual=actual+1 if bool(seco) else 0
        mejor=max(mejor,actual)
    return mejor


def evaluar_pronostico(prono:pd.DataFrame)->Resultado:
    if len(prono)<7 or prono.iloc[:7].lluvia_mm.isna().any():
        raise ValueError('Se necesitan al menos siete días completos de precipitación.')
    d7=prono.iloc[:7]
    d14=prono.iloc[:14]
    lluvia7=float(d7.lluvia_mm.sum())
    maxdia=float(d7.lluvia_mm.max())
    fecha_mayor=str(d7.loc[d7.lluvia_mm.idxmax(),'fecha'].date())
    secos=d7.lluvia_mm<UMBRAL_CASI_SECO_MM
    racha=racha_maxima(secos)
    primera3=float(d7.lluvia_mm.head(3).sum())
    if racha>=RACHA_SECA_ALTA or lluvia7<5:
        seco='ALTO'
    elif racha>=RACHA_SECA_ATENCION or lluvia7<15 or primera3<3:
        seco='MEDIO'
    else: seco='BAJO'
    dias_intensos=int((d7.lluvia_mm>=UMBRAL_LLUVIOSO_DIA_MM).sum())
    if maxdia>=UMBRAL_LLUVIOSO_DIA_ALTO_MM or lluvia7>=UMBRAL_SEMANA_LLUVIA_ALTA_MM:
        exceso='ALTO'
    elif maxdia>=UMBRAL_LLUVIOSO_DIA_MM or lluvia7>=60:
        exceso='MEDIO'
    else: exceso='BAJO'
    min_temp=(float(d7.tmin_c.min()) if 'tmin_c' in d7 and d7.tmin_c.notna().all() else None)
    frio='ATENCION' if min_temp is not None and min_temp<=UMBRAL_HELADA_PRECAUCION_C else 'SIN_ALERTA'
    total14=round(float(d14.lluvia_mm.sum()),1) if len(d14)==14 and d14.lluvia_mm.notna().all() else None
    et0=round(float(d7.et0_mm.sum()),1) if 'et0_mm' in d7 and d7.et0_mm.notna().all() else None
    if seco=='ALTO' and exceso=='ALTO':
        nivel='ALTO'; titular='Semana variable: posible sequedad y lluvias intensas'
        motivo=f'Hay una racha de {racha} días casi secos y también se estima un día de hasta {maxdia:.1f} mm. Conviene revisar las dos situaciones.'
    elif exceso=='ALTO':
        nivel='ALTO'; titular='Precaución: lluvia intensa o acumulada abundante'
        motivo=f'Se estiman {lluvia7:.1f} mm en siete días y hasta {maxdia:.1f} mm el {fecha_mayor}. Existe la posibilidad de suelo saturado, erosión o encharcamiento; el pronóstico no confirma el estado de la parcela.'
    elif seco=='ALTO':
        nivel='ALTO'; titular='Precaución: varios días con poca lluvia'
        motivo=f'La lluvia total prevista es {lluvia7:.1f} mm y la mayor racha casi seca llega a {racha} días. Si dependes de la lluvia, la humedad podría ser insuficiente para establecer el cultivo.'
    elif exceso=='MEDIO':
        nivel='MEDIO'; titular='Atención: pueden presentarse lluvias importantes'
        motivo=f'El pronóstico suma {lluvia7:.1f} mm en siete días; el día más lluvioso registra {maxdia:.1f} mm. Comprueba la capacidad de drenaje del terreno.'
    elif seco=='MEDIO':
        nivel='MEDIO'; titular='Atención: lluvia escasa o irregular'
        motivo=f'Hay {racha} días consecutivos casi secos, con {lluvia7:.1f} mm en la semana. Revisa la humedad real del suelo.'
    elif frio=='ATENCION':
        nivel='MEDIO'; titular='Atención: posible frío cercano al nivel de precaución'
        motivo=f'La temperatura mínima prevista llega a {min_temp:.1f} °C. La temperatura del aire no confirma una helada ni la temperatura del suelo.'
    else:
        nivel='BAJO'; titular='Sin señales fuertes de sequedad ni lluvia intensa en 7 días'
        motivo=f'Se estiman {lluvia7:.1f} mm esta semana y un máximo de {maxdia:.1f} mm en un día. Esto no certifica que la parcela esté lista para sembrar.'
    if frio=='ATENCION' and 'frío' not in motivo and 'helada' not in motivo:
        motivo+=f' Además, se estima una mínima de {min_temp:.1f} °C: verifica el riesgo local de frío.'
    return Resultado(nivel,titular,round(lluvia7,1),total14,int(secos.sum()),racha,
        round(primera3,1),et0,str(d7.fecha.iloc[0].date()),str(d14.fecha.iloc[-1].date()),
        motivo,seco,exceso,frio,round(maxdia,1),dias_intensos,min_temp,fecha_mayor)


def recomendaciones(resultado:Resultado,cultivo:str,tiene_riego:str,humedad_suelo:str)->list[str]:
    """Consejos no prescriptivos: se personalizan por riesgos, suelo, riego y cultivo."""
    r=resultado; lista=[]
    if r.riesgo_exceso=='ALTO':
        lista.append(f'ANTES DE SEMBRAR: se prevén hasta {r.max_lluvia_dia:.1f} mm en un día. Revisa que el terreno pueda evacuar el agua; evita labores en parcelas encharcadas o demasiado blandas.')
    elif r.riesgo_exceso=='MEDIO':
        lista.append(f'Se prevén lluvias importantes (máximo {r.max_lluvia_dia:.1f} mm/día). Verifica drenajes y caminos de acceso antes de preparar el suelo.')
    if r.riesgo_seco=='ALTO':
        if tiene_riego=='Sí': lista.append(f'Se prevén {r.racha_7d} días casi secos consecutivos. Antes de sembrar, comprueba que el riego y la fuente de agua puedan mantener húmeda la zona de germinación.')
        else: lista.append(f'Sin riego y con {r.racha_7d} días casi secos previstos, valora esperar lluvias más sostenidas y consulta el pronóstico nuevamente.')
    elif r.riesgo_seco=='MEDIO':
        lista.append('La distribución de lluvia es irregular: verifica la humedad a la profundidad de la semilla, no solo la lluvia total semanal.')
    if r.riesgo_frio=='ATENCION':
        lista.append(f'Se pronostica un mínimo de {r.temperatura_min:.1f} °C. Consulta alertas locales y confirma si tu cultivo o variedad es sensible al frío.')
    if humedad_suelo=='Seco':
        lista.append('Observas el suelo seco: prueba la humedad a la profundidad donde colocarás la semilla; no lo consideres apto solo porque anuncia lluvia.')
    elif humedad_suelo=='Húmedo':
        lista.append('Observas el suelo húmedo: comprueba si está aireado y no saturado antes de entrar con maquinaria o depositar semillas.')
    else:
        lista.append('No conoces la humedad del suelo: revísala directamente en el terreno. Un pronóstico no mide la humedad donde germinarán las semillas.')
    especifico={
        'Fréjol':'Para fréjol, comprueba especialmente el drenaje: el agua estancada alrededor de las semillas puede perjudicar la emergencia.',
        'Maíz':'Para maíz, prioriza humedad suficiente en la zona de siembra sin saturación; confirma variedad y calendario local.',
        'Papa':'Para papa, además de la humedad, revisa drenaje y posibles heladas en tu zona.',
        'Hortalizas':'En hortalizas, las necesidades cambian por especie y etapa: verifica si necesitas semillero, cobertura o drenaje.',
        'Arroz':'Para arroz, determina si el manejo será de secano o inundado; sus requisitos de agua son diferentes.',
        'Otro cultivo':'Consulta las necesidades de establecimiento específicas de la variedad y el tipo de suelo.',
    }
    lista.append(especifico.get(cultivo,especifico['Otro cultivo']))
    if not lista[0].startswith(('ANTES','Se prevén','Sin riego','La distribución')) and r.nivel=='BAJO':
        lista.insert(0,'Puedes planificar el trabajo de campo, pero confirma las condiciones locales antes de fijar la fecha de siembra.')
    lista.append('Antes de invertir o sembrar, contrasta el pronóstico con los avisos del INAMHI y, cuando sea posible, un técnico agrícola local.')
    return lista
