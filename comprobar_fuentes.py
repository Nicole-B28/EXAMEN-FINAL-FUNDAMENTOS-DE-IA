"""Prueba en vivo para realizar ante el profesor, desde una computadora con internet.
Ejecutar: python comprobar_fuentes.py
Comprueba la API y aritmética, NO la precisión futura.
"""
import argparse
from clima import consultar_pronostico,FuenteNoDisponible


def ejecutar(lat,lon):
    c=consultar_pronostico(lat,lon,14)
    print('\nSIEMBRAVERDE IA — AUDITORÍA DE DATOS OPEN-METEO')
    print('Fuente pública: https://open-meteo.com/en/docs')
    print('URL de la consulta exacta:')
    print(c.url)
    print('Consulta UTC:',c.consultado_utc)
    print('Zona horaria:',c.zona)
    print('Coordenadas solicitadas:',c.lat_peticion,c.lon_peticion)
    print('Celda del modelo:',c.lat_modelo,c.lon_modelo,'altura',c.altitud_modelo,'m')
    print('\nPrimeros siete valores diarios originales (mm):')
    for _,r in c.futuro.head(7).iterrows():
        print(r.fecha.strftime('%Y-%m-%d'),f'{r.lluvia_mm:.2f} mm')
    print('\nSuma del JSON Open-Meteo:',f'{c.api_7d:.2f} mm')
    print('Suma de SiembraVerde:',f'{c.calculo_7d:.2f} mm')
    print('COMPROBACIÓN:',c.verificacion)
    print('\nACLARACIÓN: datos auténticos de una API, pero son PRONÓSTICOS;')
    print('solo se podrá verificar cuánto llovió realmente después de esos días,')
    print('comparando con estaciones u otras observaciones independientes.')


if __name__=='__main__':
    p=argparse.ArgumentParser(description='Comparación directa con Open-Meteo')
    p.add_argument('--lat',type=float,default=-0.1807,help='Latitud (Quito por defecto)')
    p.add_argument('--lon',type=float,default=-78.4678,help='Longitud (Quito por defecto)')
    args=p.parse_args()
    try: ejecutar(args.lat,args.lon)
    except (FuenteNoDisponible,ValueError) as e:
        print('NO VERIFICADO: imposible consultar la fuente actual. Motivo:',e)
        raise SystemExit(1)
