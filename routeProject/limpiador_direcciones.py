# routeProject/limpiador_direcciones.py
import pandas as pd
import re
import unicodedata
import argparse
import os

def normalizar_caracteres_especiales(texto):
    if pd.isna(texto):
        return texto
    
    texto = str(texto)
    
    # Corregir caracteres mal codificados comunes (cuando UTF-8 se interpreta como Latin-1)
    correcciones_mala_codificacion = {
        'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú', 
        'Ã±': 'ñ', 'Ã': 'Á', 'Ã': 'É', 'Ã': 'Í', 'Ã': 'Ó', 
        'Ã': 'Ú', 'Ã': 'Ñ', 'Ã¼': 'ü', 'Ã': 'Ü',
        'Â°': '°', 'Âª': 'ª', 'Âº': 'º', 'Â¿': '¿', 'Â¡': '¡',
        'Ã': 'í',  # Caso especial para algunos caracteres
    }
    
    for mal_codificado, correcto in correcciones_mala_codificacion.items():
        texto = texto.replace(mal_codificado, correcto)
    
    # Normalizar caracteres Unicode (descomponer y luego recomponer)
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    texto = unicodedata.normalize('NFC', texto)
    
    return texto

def limpiar_campo(texto):
    """Limpia un campo de texto"""
    if pd.isna(texto):
        return texto
    
    texto = str(texto).strip()
    
    # Normalizar caracteres especiales primero
    texto = normalizar_caracteres_especiales(texto)
    
    # Convertir a título pero preservar acrónimos y abreviaturas
    palabras = texto.split()
    palabras_corregidas = []
    
    for palabra in palabras:
        # Si es una abreviatura conocida, mantener en mayúsculas
        abreviaturas = ['Av', 'Cll', 'Cra', 'No', 'Num', 'Núm', 'Col', 'Cp', 'De', 'Del', 'La', 'Los', 'Las']
        if palabra.replace('.', '') in abreviaturas:
            palabras_corregidas.append(palabra.upper())
        else:
            palabras_corregidas.append(palabra.title())
    
    texto = ' '.join(palabras_corregidas)
    
    # Remover múltiples espacios
    texto = re.sub(r'\s+', ' ', texto)
    
    # Correcciones comunes de formato
    correcciones = {
        r'\bAv\b\.?': 'Av.',
        r'\bCalle\b': 'Cll.',
        r'\bCll\b\.?': 'Cll.',
        r'\bCarrera\b': 'Cra.',
        r'\bCra\b\.?': 'Cra.',
        r'\bNumero\b': 'No.',
        r'\bNúmero\b': 'No.',
        r'\bNum\b\.?': 'No.',
        r'\bNúm\b\.?': 'No.',
        r'\bNo\b\.?': 'No.',
        r'\bColonia\b': 'Col.',
        r'\bCol\b\.?': 'Col.',
        r'#\s*': 'No. ',
        r'\bY\b': 'y',  # 'y' en minúscula para conjunciones
        r'\bE\b': 'e',  # 'e' en minúscula para conjunciones
    }
    
    for patron, reemplazo in correcciones.items():
        texto = re.sub(patron, reemplazo, texto, flags=re.IGNORECASE)
    
    # Asegurar que después de punto haya espacio si no lo hay
    texto = re.sub(r'\.([a-zA-Z])', r'. \1', texto)
    
    return texto

def validar_cp(cp):
    """Valida y formatea el código postal"""
    if pd.isna(cp):
        return cp
    
    cp = str(cp).strip()
    
    # Remover caracteres no numéricos
    cp = re.sub(r'[^\d]', '', cp)
    
    # Asegurar que CP tenga 5 dígitos
    if cp.isdigit():
        if len(cp) > 5:
            cp = cp[:5]  # Tomar solo los primeros 5 dígitos
        elif len(cp) < 5:
            cp = cp.zfill(5)  # Rellenar con ceros a la izquierda
    else:
        # Si no es numérico, devolver vacío
        cp = ''
    
    return cp

def limpiar_direcciones_csv(archivo_entrada: str, archivo_salida: str):
    """Limpia y estandariza las direcciones antes de la geocodificación"""
    try:
        # Detectar automáticamente la codificación del archivo
        try:
            df = pd.read_csv(archivo_entrada, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                df = pd.read_csv(archivo_entrada, encoding='latin-1')
            except UnicodeDecodeError:
                df = pd.read_csv(archivo_entrada, encoding='iso-8859-1')
        
        print(f"Archivo leído con éxito: {archivo_entrada}")
        print(f"Número de registros: {len(df)}")
        
        # Estandarizar nombres de columnas (case insensitive)
        df.columns = df.columns.str.strip().str.title()
        print(f"Columnas detectadas: {list(df.columns)}")
        
        # Limpiar cada campo
        if 'Domicilio' in df.columns:
            print("Limpiando campo 'Domicilio'...")
            df['Domicilio'] = df['Domicilio'].apply(limpiar_campo)
        
        if 'Colonia' in df.columns:
            print("Limpiando campo 'Colonia'...")
            df['Colonia'] = df['Colonia'].apply(limpiar_campo)
        
        if 'Cp' in df.columns:
            print("Limpiando campo 'Cp'...")
            df['Cp'] = df['Cp'].apply(validar_cp)
        
        # Mostrar algunas muestras de los datos limpios
        print("\nMuestra de datos limpios:")
        if 'Domicilio' in df.columns:
            muestras = df['Domicilio'].head(3).tolist()
            for i, muestra in enumerate(muestras, 1):
                print(f"  {i}. {muestra}")
        
        # Guardar archivo limpio
        df.to_csv(archivo_salida, index=False, encoding='utf-8')
        print(f"\nArchivo limpiado guardado en: {archivo_salida}")
        print(f"Tamaño del archivo: {os.path.getsize(archivo_salida)} bytes")
        
        return True
        
    except Exception as e:
        print(f"Error procesando el archivo: {e}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Limpiador de direcciones CSV - Normaliza y limpia direcciones para geocodificación',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python limpiador_direcciones.py --entrada datos_sucios.csv --salida datos_limpios.csv
  python limpiador_direcciones.py -e entrada.csv -s salida.csv
        """
    )
    
    parser.add_argument('-e', '--entrada', 
                       required=True, 
                       help='Archivo CSV de entrada con direcciones a limpiar')
    parser.add_argument('-s', '--salida', 
                       required=True, 
                       help='Archivo CSV de salida con direcciones limpias')
    
    args = parser.parse_args()
    
    # Verificar que el archivo de entrada existe
    if not os.path.exists(args.entrada):
        print(f"Error: El archivo '{args.entrada}' no existe")
        exit(1)
    
    # Verificar que el directorio de salida existe, si no crearlo
    directorio_salida = os.path.dirname(args.salida)
    if directorio_salida and not os.path.exists(directorio_salida):
        os.makedirs(directorio_salida)
    
    # Ejecutar la limpieza
    exito = limpiar_direcciones_csv(args.entrada, args.salida)
    
    if not exito:
        exit(1)
    
# python limpiador_direcciones.py -e "datos/entrada/entrada.csv" -s "datos/entrada/direcciones_limpias.csv" 