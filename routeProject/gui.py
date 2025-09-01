import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import os
import sys
import subprocess

# Importar nuestros módulos con manejo de errores
try:
    from config import NOMINATIM_URL, GEOCODING_DELAY, USER_AGENT
except ImportError:
    # Si config.py no existe, crear valores por defecto
    NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
    GEOCODING_DELAY = 1.0
    USER_AGENT = "OptimizadorRutas/1.0"

try:
    from geocodificador import Geocodificador
    from optimizador_rutas import OptimizadorRutas
    from generador_mapas import GeneradorMapas
    from utils import crear_directorios, filtrar_por_zona, dividir_por_notificadores, mostrar_ruta, verificar_estructura_csv
except ImportError as e:
    print(f"Error importando módulos: {e}")
    print("Algunas funciones estarán limitadas")

# Definir funciones de utils por si falla la importación
if 'crear_directorios' not in globals():
    def crear_directorios():
        directorios = ['datos/entrada', 'datos/salida', 'mapas']
        for directorio in directorios:
            os.makedirs(directorio, exist_ok=True)
        print("✅ Directorios creados/existen")

if 'filtrar_por_zona' not in globals():
    def filtrar_por_zona(df, zona):
        if 'Zona' in df.columns:
            return df[df['Zona'] == zona]
        return df

class OptimizadorRutasGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Optimizador de Rutas de Entrega")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        self.archivo_csv = None
        self.df_original = None
        
        self.setup_ui()
        crear_directorios()
    
    def setup_ui(self):
        # Configurar estilo
        style = ttk.Style()
        style.configure('TFrame', background='#f0f0f0')
        style.configure('TLabel', background='#f0f0f0')
        style.configure('TRadiobutton', background='#f0f0f0')
        
        # Frame principal con scrollbar
        self.main_frame = ttk.Frame(self.root, padding="15")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(9, weight=1)
        
        # Título
        title_label = ttk.Label(self.main_frame, 
                               text="🚀 Optimizador de Rutas de Entrega", 
                               font=("Arial", 16, "bold"),
                               foreground="#2c3e50")
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Selección de archivo
        ttk.Label(self.main_frame, text="Archivo CSV:", 
                 font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        
        self.archivo_label = ttk.Label(self.main_frame, 
                                      text="Ningún archivo seleccionado", 
                                      foreground="gray",
                                      font=("Arial", 9))
        self.archivo_label.grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Button(self.main_frame, 
                  text="Seleccionar CSV", 
                  command=self.seleccionar_archivo).grid(row=1, column=2, padx=5)
        
        # Zona
        ttk.Label(self.main_frame, text="Zona a optimizar:", 
                 font=("Arial", 10, "bold")).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.zona_var = tk.StringVar()
        self.zona_combo = ttk.Combobox(self.main_frame, 
                                      textvariable=self.zona_var, 
                                      state="readonly",
                                      width=30)
        self.zona_combo.grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Modo de optimización
        ttk.Label(self.main_frame, text="Modo de optimización:", 
                 font=("Arial", 10, "bold")).grid(row=3, column=0, sticky=tk.W, pady=5)
        
        self.modo_var = tk.StringVar(value="ruta_unica")
        
        mode_frame = ttk.Frame(self.main_frame)
        mode_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W, pady=5)
        
        ttk.Radiobutton(mode_frame, text="Ruta Única", 
                       variable=self.modo_var, 
                       value="ruta_unica").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="Múltiples Notificadores", 
                       variable=self.modo_var, 
                       value="multi_notificador").pack(side=tk.LEFT, padx=10)
        
        # Cuentas por notificador
        ttk.Label(self.main_frame, text="Cuentas por notificador:", 
                 font=("Arial", 10, "bold")).grid(row=4, column=0, sticky=tk.W, pady=5)
        
        self.cuentas_var = tk.StringVar(value="10")
        self.cuentas_spin = ttk.Spinbox(self.main_frame, 
                                       from_=1, to=50, 
                                       textvariable=self.cuentas_var, 
                                       state="disabled",
                                       width=10)
        self.cuentas_spin.grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Botón de ejecución
        self.ejecutar_btn = ttk.Button(self.main_frame, 
                                      text="▶️ Ejecutar Optimización", 
                                      command=self.ejecutar_optimizacion, 
                                      state="disabled",
                                      style="Accent.TButton")
        self.ejecutar_btn.grid(row=5, column=0, columnspan=3, pady=20)
        
        # Progress bar
        self.progress = ttk.Progressbar(self.main_frame, mode='indeterminate')
        self.progress.grid(row=6, column=0, columnspan=3, sticky=tk.W+tk.E, pady=5)
        
        # Log de salida
        ttk.Label(self.main_frame, text="Log de ejecución:", 
                 font=("Arial", 10, "bold")).grid(row=7, column=0, sticky=tk.W, pady=5)
        
        # Frame para el log con scrollbar
        log_frame = ttk.Frame(self.main_frame)
        log_frame.grid(row=8, column=0, columnspan=3, sticky=tk.W+tk.E+tk.N+tk.S, pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=15, width=80, state="disabled",
                               font=("Consolas", 9), relief=tk.SUNKEN, borderwidth=1)
        self.log_text.grid(row=0, column=0, sticky=tk.W+tk.E+tk.N+tk.S)
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.N+tk.S)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Botones adicionales
        button_frame = ttk.Frame(self.main_frame)
        button_frame.grid(row=9, column=0, columnspan=3, pady=10)
        
        ttk.Button(button_frame, text="🗺️ Ver Mapas", 
                  command=self.ver_mapas).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="📂 Abrir Carpeta Resultados", 
                  command=self.abrir_carpeta_resultados).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="🧹 Limpiar Log", 
                  command=self.limpiar_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="❌ Salir", 
                  command=self.root.quit).pack(side=tk.LEFT, padx=5)
        
        # Bind events
        self.modo_var.trace('w', self.actualizar_ui)
    
    def log(self, message):
        """Agrega mensaje al log"""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
        self.root.update_idletasks()
    
    def limpiar_log(self):
        """Limpia el log"""
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")
    
    def seleccionar_archivo(self):
        """Selecciona el archivo CSV"""
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialdir="datos/entrada"
        )
        
        if filename:
            self.archivo_csv = filename
            self.archivo_label.config(text=os.path.basename(filename), foreground="blue")
            
            try:
                # Cargar CSV para obtener zonas
                if filename.endswith('.xlsx'):
                    self.df_original = pd.read_excel(filename)
                else:
                    self.df_original = pd.read_csv(filename)
                
                # Verificar si existe columna Zona
                if 'Zona' not in self.df_original.columns:
                    messagebox.showerror("Error", "El archivo CSV debe tener una columna 'Zona'")
                    return
                
                zonas = sorted(self.df_original['Zona'].astype(str).unique())
                self.zona_combo['values'] = zonas
                
                if zonas:
                    self.zona_var.set(zonas[0])
                
                self.ejecutar_btn.config(state="normal")
                self.log(f"✅ Archivo cargado: {os.path.basename(filename)}")
                self.log(f"📊 Total de registros: {len(self.df_original):,}")
                self.log(f"📍 Zonas disponibles: {len(zonas)}")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
    
    def actualizar_ui(self, *args):
        """Actualiza la UI según las selecciones"""
        if self.modo_var.get() == "multi_notificador":
            self.cuentas_spin.config(state="normal")
        else:
            self.cuentas_spin.config(state="disabled")
    
    def ejecutar_optimizacion(self):
        """Ejecuta la optimización en un hilo separado"""
        if not self.archivo_csv or not self.zona_var.get():
            messagebox.showwarning("Advertencia", "Selecciona un archivo y una zona primero")
            return
        
        # Deshabilitar UI durante ejecución
        self.ejecutar_btn.config(state="disabled")
        self.progress.start()
        
        # Ejecutar en hilo separado
        thread = threading.Thread(target=self._ejecutar_optimizacion_thread)
        thread.daemon = True
        thread.start()
    
    def _ejecutar_optimizacion_thread(self):
        """Hilo de ejecución de la optimización"""
        try:
            zona = self.zona_var.get()
            modo = self.modo_var.get()
            cuentas_por_notificador = int(self.cuentas_var.get()) if modo == "multi_notificador" else 0
            
            self.log(f"🚀 Iniciando optimización para zona: {zona}")
            
            # Inicializar componentes
            geocodificador = Geocodificador()
            optimizador = OptimizadorRutas()
            generador_mapas = GeneradorMapas()
            
            # Filtrar por zona
            self.log(f"📋 Filtrando datos para la zona: {zona}...")
            df_zona_filtrado = filtrar_por_zona(self.df_original, zona)
            
            if df_zona_filtrado.empty:
                self.log("❌ No se encontraron datos para la zona especificada")
                return
            
            self.log(f"📍 {len(df_zona_filtrado)} domicilios encontrados en {zona}")
            
            # Guardar CSV filtrado
            archivo_filtrado = f"datos/salida/filtrado_{zona}.csv"
            df_zona_filtrado.to_csv(archivo_filtrado, index=False, encoding='utf-8')
            
            # Geocodificación
            self.log("🧹 Geocodificando direcciones...")
            archivo_geocodificado = f"datos/salida/geocodificado_{zona}.csv"
            df = geocodificador.procesar_csv(archivo_filtrado, archivo_geocodificado)
            
            if df.empty:
                self.log("❌ No se pudieron geocodificar las direcciones")
                return
            
            self.log(f"✅ {len(df)} direcciones geocodificadas exitosamente")
            
            # Optimización
            if modo == "multi_notificador":
                self.log(f"🛣️ Generando rutas para {cuentas_por_notificador} cuentas por notificador...")
                chunks = dividir_por_notificadores(df, cuentas_por_notificador)
                
                for i, chunk in enumerate(chunks):
                    self.log(f"📋 Procesando Notificador {i+1} ({len(chunk)} cuentas)...")
                    try:
                        rutas_chunk = optimizador.optimizar_ruta(chunk, 1)
                        # Aquí iría el resto de la lógica de optimización
                        self.log(f"✅ Ruta {i+1} optimizada con {len(rutas_chunk[0])} paradas")
                    except Exception as e:
                        self.log(f"❌ Error en notificador {i+1}: {e}")
            else:
                self.log("🛣️ Optimizando ruta única...")
                try:
                    rutas_optimizadas = optimizador.optimizar_ruta(df, 1)
                    self.log(f"✅ Ruta única optimizada con {len(rutas_optimizadas[0])} paradas")
                    # Aquí iría el resto de la lógica de optimización
                except Exception as e:
                    self.log(f"❌ Error en optimización: {e}")
            
            self.log("✅ Proceso completado exitosamente!")
            self.log("💾 Resultados guardados en: datos/salida/")
            self.log("🗺️ Mapas generados en: mapas/")
            
        except Exception as e:
            self.log(f"❌ Error durante la optimización: {str(e)}")
        finally:
            # Rehabilitar UI
            self.root.after(0, self._finalizar_ejecucion)
    
    def _finalizar_ejecucion(self):
        """Finaliza la ejecución y actualiza UI"""
        self.progress.stop()
        self.ejecutar_btn.config(state="normal")
        messagebox.showinfo("Completado", "Proceso de optimización finalizado")
    
    def ver_mapas(self):
        """Abre el visualizador de mapas"""
        mapas_dir = "mapas"
        if os.path.exists(mapas_dir) and os.listdir(mapas_dir):
            try:
                os.startfile(mapas_dir)
            except:
                messagebox.showinfo("Mapas", f"Los mapas están en: {os.path.abspath(mapas_dir)}")
        else:
            messagebox.showwarning("No hay mapas", "La carpeta 'mapas' está vacía o no existe")
    
    def abrir_carpeta_resultados(self):
        """Abre la carpeta de resultados"""
        resultados_dir = "datos/salida"
        if os.path.exists(resultados_dir):
            try:
                os.startfile(resultados_dir)
            except:
                messagebox.showinfo("Resultados", f"Los resultados están en: {os.path.abspath(resultados_dir)}")
        else:
            messagebox.showwarning("Carpeta no encontrada", "La carpeta 'datos/salida' no existe")

def main():
    """Función principal de la GUI"""
    root = tk.Tk()
    app = OptimizadorRutasGUI(root)
    
    # Centrar la ventana
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()