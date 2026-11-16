"""ML del módulo: regresión logística y KNN para rachas de >= 3 días casi secos.

Evaluación cronológica con separación (gap) de siete días para reducir fuga
por etiquetas futuras superpuestas. Análisis educativo, no riesgo calibrado.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.dummy import DummyClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import balanced_accuracy_score, f1_score
from analisis import racha_maxima

FEATURES = ["lluvia7", "lluvia14", "dias_secos7", "racha7", "tmax7", "et07", "mes_sin", "mes_cos"]

@dataclass
class EvaluacionModelo:
    modelo: object | None
    nombre: str
    ba: float | None
    f1: float | None
    base_ba: float | None
    probabilidad: float | None
    mensaje: str
    n_muestras: int


def _vector_pasado(pasado: pd.DataFrame, fecha: pd.Timestamp) -> dict:
    ultima7 = pasado.iloc[-7:]
    ultima14 = pasado.iloc[-14:]
    mes = int(fecha.month)
    return {
        "lluvia7": float(ultima7.lluvia_mm.sum()),
        "lluvia14": float(ultima14.lluvia_mm.sum()),
        "dias_secos7": int((ultima7.lluvia_mm < 1).sum()),
        "racha7": racha_maxima(ultima7.lluvia_mm < 1),
        "tmax7": float(ultima7.tmax_c.mean()),
        "et07": float(ultima7.et0_mm.sum()),
        "mes_sin": float(np.sin(2 * np.pi * mes / 12)),
        "mes_cos": float(np.cos(2 * np.pi * mes / 12)),
    }


def construir_dataset(hist: pd.DataFrame) -> pd.DataFrame:
    hist = hist.copy().sort_values("fecha").reset_index(drop=True)
    hist["fecha"] = pd.to_datetime(hist["fecha"])
    hist = hist.dropna(subset=["lluvia_mm", "tmax_c", "et0_mm"])
    filas = []
    for i in range(14, len(hist) - 7):
        pasado = hist.iloc[i-14:i]
        futuro = hist.iloc[i:i+7]
        # No formar muestras donde hay saltos de fechas.
        dias = (futuro.fecha.iloc[-1] - pasado.fecha.iloc[0]).days
        if dias != 20:
            continue
        fila = _vector_pasado(pasado, futuro.fecha.iloc[0])
        fila["fecha"] = futuro.fecha.iloc[0]
        fila["evento_seco"] = int(racha_maxima(futuro.lluvia_mm < 1) >= 3)
        filas.append(fila)
    return pd.DataFrame(filas)


def entrenar_y_estimar(hist: pd.DataFrame, pasado_reciente: pd.DataFrame) -> EvaluacionModelo:
    """Entrena, selecciona en validación y reporta desempeño en prueba posterior.

    Evita seleccionar el mejor modelo usando los mismos datos de prueba.
    La probabilidad de sklearn se considera NO calibrada; no se presenta
    como una estimación meteorológica confiable al usuario.
    """
    from sklearn.base import clone
    try:
        tabla=construir_dataset(hist)
        if len(tabla)<350 or len(pasado_reciente)<14 or tabla.evento_seco.nunique()<2:
            return EvaluacionModelo(None,'',None,None,None,None,'No hay suficiente historial variado para un clasificador verificable.',len(tabla))
        n=len(tabla)
        cv=int(n*.65)
        ct=int(n*.80)
        # Los 7 días de margen evitan que las etiquetas futuras se superpongan.
        train=tabla.iloc[:cv-7]
        valid=tabla.iloc[cv:ct-7]
        test=tabla.iloc[ct:]
        if min(len(train),len(valid),len(test))<35:
            return EvaluacionModelo(None,'',None,None,None,None,'No hay suficientes observaciones en entrenamiento, validación y prueba.',n)
        def xy(tab):
            cols=tab[FEATURES].replace([np.inf,-np.inf],np.nan)
            ok=cols.notna().all(axis=1)
            return cols.loc[ok],tab.loc[ok,'evento_seco']
        Xtr,ytr=xy(train)
        Xva,yva=xy(valid)
        Xte,yte=xy(test)
        if min(ytr.nunique(),yva.nunique(),yte.nunique())<2:
            return EvaluacionModelo(None,'',None,None,None,None,'Una etapa temporal tiene una sola clase (días secos o no secos). No reportaremos una precisión engañosa.',n)
        candidatos={
            'Regresión logística':Pipeline([('escalar',StandardScaler()),('clasificador',LogisticRegression(max_iter=700,class_weight='balanced',random_state=42))]),
            'KNN':Pipeline([('escalar',StandardScaler()),('clasificador',KNeighborsClassifier(n_neighbors=11))]),
        }
        validaciones=[]
        for nombre,alg in candidatos.items():
            alg.fit(Xtr,ytr)
            pred_val=alg.predict(Xva)
            validaciones.append((balanced_accuracy_score(yva,pred_val),f1_score(yva,pred_val,zero_division=0),nombre))
        _,_,nombre=sorted(validaciones,key=lambda x:(x[0],x[1]),reverse=True)[0]
        seleccionado=clone(candidatos[nombre]).fit(Xtr,ytr)
        y_est=seleccionado.predict(Xte)
        ba=float(balanced_accuracy_score(yte,y_est))
        f1=float(f1_score(yte,y_est,zero_division=0))
        ref=DummyClassifier(strategy='most_frequent').fit(Xtr,ytr)
        ba_base=float(balanced_accuracy_score(yte,ref.predict(Xte)))
        if ba<=ba_base+0.02:
            return EvaluacionModelo(seleccionado,nombre,ba,f1,ba_base,None,'El clasificador no superó suficientemente al método de referencia en fechas posteriores. No se muestra una señal confiable.',n)
        Xrec=pasado_reciente.copy().sort_values('fecha').dropna(subset=['lluvia_mm','tmax_c','et0_mm'])
        if len(Xrec)<14:
            return EvaluacionModelo(seleccionado,nombre,ba,f1,ba_base,None,'Faltan datos recientes para aplicar el modelo histórico.',n)
        completoX,completoY=xy(tabla)
        if completoY.nunique()<2:
            return EvaluacionModelo(seleccionado,nombre,ba,f1,ba_base,None,'Sin dos clases en los datos de entrenamiento final.',n)
        final=clone(candidatos[nombre]).fit(completoX,completoY)
        vector=pd.DataFrame.from_records([_vector_pasado(Xrec.iloc[-14:],pd.to_datetime(Xrec.fecha.iloc[-1])+pd.Timedelta(days=1))],columns=FEATURES)
        proba=float(final.predict_proba(vector)[0,list(final.classes_).index(1)])
        return EvaluacionModelo(final,nombre,ba,f1,ba_base,proba,
            'Señal exploratoria para una racha de al menos 3 días casi secos; no es una probabilidad calibrada.',n)
    except (ValueError,KeyError,TypeError) as exc:
        return EvaluacionModelo(None,'',None,None,None,None,'No se pudo evaluar el modelo con el historial recibido.',0)

@dataclass
class PerfilLluvia:
    descripcion: str
    promedio_grupo_mm: float
    promedio_general_mm: float
    cantidad_periodos: int


def agrupar_patrones_historicos(hist: pd.DataFrame, pasado_reciente: pd.DataFrame) -> PerfilLluvia | None:
    """KMeans de semanas meteorológicas. Agrupa; no predice sequía."""
    from sklearn.cluster import KMeans
    hist = hist.sort_values('fecha').dropna(subset=['lluvia_mm']).reset_index(drop=True)
    if len(hist) < 180 or len(pasado_reciente) < 7:
        return None
    grupos = []
    # Semanas no solapadas: evita inflar el número de perfiles casi iguales.
    for i in range(0, len(hist) - 7, 7):
        s = hist.iloc[i:i+7]
        if (pd.to_datetime(s.fecha.iloc[-1])-pd.to_datetime(s.fecha.iloc[0])).days != 6:
            continue
        grupos.append([float(s.lluvia_mm.sum()), float((s.lluvia_mm<1).sum())])
    if len(grupos) < 24:
        return None
    v = np.array(grupos)
    scaler = StandardScaler().fit(v)
    km = KMeans(n_clusters=3, random_state=42, n_init=10).fit(scaler.transform(v))
    actual = pasado_reciente.sort_values('fecha').iloc[-7:]
    a = np.array([[float(actual.lluvia_mm.sum()),float((actual.lluvia_mm<1).sum())]])
    elegido = km.predict(scaler.transform(a))[0]
    media_grupo = float(v[km.labels_==elegido,0].mean())
    media_total = float(v[:,0].mean())
    medias = {k:float(v[km.labels_==k,0].mean()) for k in range(3)}
    orden = sorted(medias,key=medias.get)
    etiquetas = {orden[0]:'históricamente menos lluvioso',orden[1]:'históricamente intermedio',orden[2]:'históricamente más lluvioso'}
    return PerfilLluvia(etiquetas[elegido], round(media_grupo,1),round(media_total,1),len(v))
