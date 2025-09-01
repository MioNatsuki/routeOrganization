import pandas as pd
import re

def limpiar_campo(texto):
    """Limpia un campo de texto"""
    if pd.isna(texto):
        return texto
    
    texto = str(texto).strip().title()
    
    # Remover múltiples espacios
    texto = re.sub(r'\s+', ' ', texto)
    
    # Correcciones comunes
    correcciones = {
        'Av ': 'Av. ',
        'Av.': 'Av.',
        'Calle ': 'Cll. ',
        'Cll': 'Cll.',
        'Cra ': 'Cra. ',
        'Cra': 'Cra.',
        'Num ': 'No. ',
        'Num': 'No.',
        'Núm ': 'No. ',
        'Núm': 'No.',
        'Col ': 'Col. ',
        'Col': 'Col.',
        '#': 'No. '
    }
    
    for viejo, nuevo in correcciones.items():
        texto = texto.replace(viejo, nuevo)
    
    return texto

def limpiar_direcciones_csv(archivo_entrada: str, archivo_salida: str):
    """Limpia y estandariza las direcciones antes de la geocodificación"""
    df = pd.read_csv(archivo_entrada)
    
    # Estandarizar nombres de columnas
    df.columns = df.columns.str.strip().str.title()
    
    # Limpiar cada campo
    if 'Domicilio' in df.columns:
        df['Domicilio'] = df['Domicilio'].apply(limpiar_campo)
    
    if 'Colonia' in df.columns:
        df['Colonia'] = df['Colonia'].apply(limpiar_campo)
    
    if 'Cp' in df.columns:
        df['Cp'] = df['Cp'].astype(str).str.strip()
        # Asegurar que CP tenga 5 dígitos
        df['Cp'] = df['Cp'].apply(lambda x: x.zfill(5) if x.isdigit() and len(x) < 5 else x)
    
    df.to_csv(archivo_salida, index=False, encoding='utf-8')
    print(f"✅ Archivo limpiado guardado en: {archivo_salida}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Limpiador de direcciones CSV')
    parser.add_argument('entrada', help='Archivo CSV de entrada')
    parser.add_argument('salida', help='Archivo CSV de salida')
    
    args = parser.parse_args()
    
    limpiar_direcciones_csv(args.entrada, args.salida)