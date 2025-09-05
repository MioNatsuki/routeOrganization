import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import os
import sys
import math

# Importar nuestros módulos
try:
    from geocodificador import Geocodificador
    from optimizador_rutas import OptimizadorRutas
    from generador_mapas import GeneradorMapas
    from utils import crear_directorios, filtrar_por_zona, dividir_por_notificadores
except ImportError as e:
    print(f"Error importando módulos: {e}")

class ModernOptimizadorRutasGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Optimizador de Rutas Inteligente")
        self.root.geometry("1000x920")
        self.root.configure(bg='white')
        self.root.minsize(900, 650)

        self.ejecucion_activa = False
        self.hilo_ejecucion = None
        self.archivo_csv = None
        self.df_original = None
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.colors = {
            'background': '#ffffff',
            'primary': '#6c5ce7',      # Morado pastel
            'secondary': '#00cec9',    # Verde azulado pastel
            'accent': '#fd79a8',       # Rosa pastel
            'text': '#2d3436',         # Texto oscuro
            'light_text': '#636e72',   # Texto claro
            'card_bg': '#f8f9fa',      # Fondo de tarjetas
            'success': '#00b894',      # Verde éxito
            'warning': '#fdcb6e',      # Amarillo advertencia
            'error': '#e17055',        # Naranja error
            'border': '#dfe6e9'        # Borde claro
        }
        
        self.setup_styles()
        self.setup_ui()
        crear_directorios()
    
    def setup_styles(self):
        # Configurar el estilo general
        self.style.configure('.', background=self.colors['background'], 
                            foreground=self.colors['text'], font=('Segoe UI', 10))
        
        # Configurar frames
        self.style.configure('TFrame', background=self.colors['background'])
        self.style.configure('Card.TFrame', background=self.colors['card_bg'], 
                            relief='raised', borderwidth=1)
        
        # Configurar labels
        self.style.configure('TLabel', background=self.colors['background'], 
                           foreground=self.colors['text'], font=('Segoe UI', 10))
        self.style.configure('Title.TLabel', font=('Segoe UI', 16, 'bold'), 
                           foreground=self.colors['primary'])
        self.style.configure('Subtitle.TLabel', font=('Segoe UI', 12), 
                           foreground=self.colors['light_text'])
        self.style.configure('CardTitle.TLabel', font=('Segoe UI', 12, 'bold'), 
                           foreground=self.colors['primary'], background=self.colors['card_bg'])
        
        # Configurar botones
        self.style.configure('TButton', font=('Segoe UI', 10), padding=8, 
                           relief='flat', borderwidth=0)
        self.style.configure('Primary.TButton', background=self.colors['primary'], 
                           foreground='white', font=('Segoe UI', 11, 'bold'))
        self.style.map('Primary.TButton', 
                      background=[('active', '#5d49d6'), ('pressed', '#4c3cb8')])
        
        self.style.configure('Secondary.TButton', background=self.colors['secondary'], 
                           foreground='white')
        self.style.map('Secondary.TButton', 
                      background=[('active', '#00b7b4'), ('pressed', '#00a19e')])
        
        self.style.configure('Accent.TButton', background=self.colors['accent'], 
                           foreground='white')
        self.style.map('Accent.TButton', 
                      background=[('active', '#fc68a1'), ('pressed', '#fb5799')])
        
        # Configurar combobox
        self.style.configure('TCombobox', fieldbackground='white', 
                           selectbackground=self.colors['primary'])
        self.style.map('TCombobox', 
                      fieldbackground=[('readonly', 'white')],
                      selectbackground=[('readonly', self.colors['primary'])])
        
        # Configurar radiobuttons
        self.style.configure('TRadiobutton', background=self.colors['background'])
        
        # Configurar progressbar
        self.style.configure('TProgressbar', thickness=20, background=self.colors['primary'])
        
        # Configurar notebook (tabs)
        self.style.configure('TNotebook', background=self.colors['background'], 
                           borderwidth=0)
        self.style.configure('TNotebook.Tab', background=self.colors['card_bg'], 
                           padding=[15, 5], font=('Segoe UI', 10))
        self.style.map('TNotebook.Tab', 
                      background=[('selected', self.colors['primary'])],
                      foreground=[('selected', 'white')])
    
    def setup_ui(self):
        # Frame principal con padding
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Header con icono
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, pady=(0, 20), sticky=(tk.W, tk.E))
        header_frame.columnconfigure(0, weight=1)
        
        ttk.Label(header_frame, text="OPTIMIZADOR DE RUTAS INTELIGENTE", 
                 style='Title.TLabel').grid(row=0, column=0, pady=(0, 5))
        ttk.Label(header_frame, text="Sistema de optimización de rutas de entrega", 
                 style='Subtitle.TLabel').grid(row=1, column=0)
        
        # Card de selección de archivo
        file_card = ttk.Frame(main_frame, style='Card.TFrame', padding="15")
        file_card.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=10)
        file_card.columnconfigure(1, weight=1)
        
        ttk.Label(file_card, text="📁 DATOS DE ENTRADA", style='CardTitle.TLabel').grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        ttk.Label(file_card, text="Archivo CSV:", font=('Segoe UI', 10, 'bold')).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.archivo_label = ttk.Label(file_card, text="Ningún archivo seleccionado", 
                                     foreground=self.colors['light_text'], font=('Segoe UI', 9))
        self.archivo_label.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        ttk.Button(file_card, text="Seleccionar CSV", command=self.seleccionar_archivo, 
                  style='Primary.TButton').grid(row=1, column=2, padx=(10, 0))
        
        ttk.Label(file_card, text="Zona a optimizar:", font=('Segoe UI', 10, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=10)
        self.zona_var = tk.StringVar()
        self.zona_combo = ttk.Combobox(file_card, textvariable=self.zona_var, 
                                      state="readonly", width=30, font=('Segoe UI', 10))
        self.zona_combo.grid(row=2, column=1, sticky=tk.W, pady=10, padx=(10, 0))
        
        # Card de configuración
        config_card = ttk.Frame(main_frame, style='Card.TFrame', padding="15")
        config_card.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=10)
        config_card.columnconfigure(1, weight=1)
        
        ttk.Label(config_card, text="⚙️ CONFIGURACIÓN", style='CardTitle.TLabel').grid(
            row=0, column=0, columnspan=3, sticky=tk.W, pady=(0, 10))
        
        ttk.Label(config_card, text="Modo de optimización:", font=('Segoe UI', 10, 'bold')).grid(
            row=1, column=0, sticky=tk.W, pady=5)
        self.modo_var = tk.StringVar(value="ruta_unica")
        
        mode_frame = ttk.Frame(config_card)
        mode_frame.grid(row=1, column=1, columnspan=2, sticky=tk.W, pady=5)
        ttk.Radiobutton(mode_frame, text="📦 Ruta Única", variable=self.modo_var, 
                       value="ruta_unica").pack(side=tk.LEFT, padx=10)
        ttk.Radiobutton(mode_frame, text="👥 Múltiples Notificadores", variable=self.modo_var, 
                       value="multi_notificador").pack(side=tk.LEFT, padx=10)
        
        ttk.Label(config_card, text="Cuentas por notificador:", font=('Segoe UI', 10, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=10)
        self.cuentas_var = tk.StringVar(value="10")
        self.cuentas_spin = ttk.Spinbox(config_card, from_=1, to=50, textvariable=self.cuentas_var, 
                                       state="disabled", width=10, font=('Segoe UI', 10))
        self.cuentas_spin.grid(row=2, column=1, sticky=tk.W, pady=10, padx=(10, 0))
        
        # Botón de ejecución
        self.ejecutar_btn = ttk.Button(main_frame, text="▶️ EJECUTAR OPTIMIZACIÓN", 
                                      command=self.ejecutar_optimizacion, 
                                      state="disabled",
                                      style='Primary.TButton')
        self.ejecutar_btn.grid(row=3, column=0, pady=20)
        
        # Progress bar moderna
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate', style='TProgressbar')
        self.progress.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=10)
        
        # Card de log de ejecución
        log_card = ttk.Frame(main_frame, style='Card.TFrame', padding="15")
        log_card.grid(row=5, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(0, weight=1)
        
        ttk.Label(log_card, text="📊 LOG DE EJECUCIÓN", style='CardTitle.TLabel').grid(
            row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Text area con scrollbar
        log_frame = ttk.Frame(log_card)
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = tk.Text(log_frame, height=12, width=80, state="disabled",
                               font=('Segoe UI', 9), relief=tk.FLAT, borderwidth=1,
                               bg=self.colors['card_bg'], fg=self.colors['text'], 
                               padx=10, pady=10, selectbackground=self.colors['primary'])
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Botones de acción
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, pady=15)
        
        actions = [
            ("🗺️ Ver Mapas", self.ver_mapas, 'Secondary.TButton'),
            ("📂 Abrir Resultados", self.abrir_carpeta_resultados, 'Secondary.TButton'),
            ("🧹 Limpiar Log", self.limpiar_log, 'Accent.TButton'),
            ("❌ Salir", self.root.quit, 'Accent.TButton')
        ]
        
        for text, command, style in actions:
            btn = ttk.Button(button_frame, text=text, command=command, 
                            style=style, width=18)
            btn.pack(side=tk.LEFT, padx=5)
        
        # Bind events
        self.modo_var.trace('w', self.actualizar_ui)
        
        # Estado inicial
        self.actualizar_ui()
    
    def seleccionar_archivo(self):
        filename = filedialog.askopenfilename(
            title="Seleccionar archivo CSV",
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialdir="datos/entrada"
        )
        
        if filename:
            self.archivo_csv = filename
            self.archivo_label.config(text=os.path.basename(filename), 
                                    foreground=self.colors['success'])
            
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
                self.log(f"Archivo cargado: {os.path.basename(filename)}", "success")
                self.log(f"Total de registros: {len(self.df_original):,}", "info")
                self.log(f"Zonas disponibles: {len(zonas)}", "info")
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo leer el archivo:\n{e}")
                self.log(f"Error leyendo archivo: {e}", "error")
    
    def ejecutar_como_cli(self, archivo: str, zona: str, cuentas_por_notificador: int = 0):
        self.archivo_csv = archivo
        self.zona_var.set(zona)
        
        if cuentas_por_notificador > 0:
            self.modo_var.set("multi_notificador")
            self.cuentas_var.set(str(cuentas_por_notificador))
        else:
            self.modo_var.set("ruta_unica")
        
        # Cargar el archivo automáticamente
        try:
            if archivo.endswith('.xlsx'):
                self.df_original = pd.read_excel(archivo)
            else:
                self.df_original = pd.read_csv(archivo)
            
            self.archivo_label.config(text=os.path.basename(archivo), 
                                    foreground=self.colors['success'])
            
            # Configurar zonas disponibles
            if 'Zona' in self.df_original.columns:
                zonas = sorted(self.df_original['Zona'].astype(str).unique())
                self.zona_combo['values'] = zonas
                if zona in zonas:
                    self.zona_var.set(zona)
            
            self.ejecutar_btn.config(state="normal")
            self.log(f"Archivo cargado: {os.path.basename(archivo)}", "success")
            
            # Ejecutar automáticamente
            self.ejecutar_optimizacion()
            
        except Exception as e:
            self.log(f"Error cargando archivo: {e}", "error")
            messagebox.showerror("Error", f"No se pudo cargar el archivo:\n{e}")

    def actualizar_ui(self, *args):
        if self.modo_var.get() == "multi_notificador":
            self.cuentas_spin.config(state="normal")
        else:
            self.cuentas_spin.config(state="disabled")
    
    def log(self, message, tipo="info"):
        colors = {
            "info": self.colors['text'],
            "success": self.colors['success'], 
            "warning": self.colors['warning'],
            "error": self.colors['error']
        }
        
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, message + "\n", tipo)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")
        
        # Aplicar color
        self.log_text.tag_config(tipo, foreground=colors.get(tipo, self.colors['text']))
        self.root.update_idletasks()
    
    def limpiar_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.configure(state="disabled")
    
    def ejecutar_optimizacion(self):
        if self.ejecucion_activa:
            messagebox.showwarning("Advertencia", "Ya hay una ejecución en curso")
            return
            
        if not hasattr(self, 'archivo_csv') or not self.zona_var.get():
            messagebox.showwarning("Advertencia", "Selecciona un archivo y una zona primero")
            return
        
        # Deshabilitar UI durante ejecución
        self.ejecucion_activa = True
        self.ejecutar_btn.config(state="disabled")
        self.progress.start()
        self.log("Iniciando proceso de optimización...", "success")
        
        # Ejecutar en hilo separado
        self.hilo_ejecucion = threading.Thread(target=self._ejecutar_optimizacion_thread)
        self.hilo_ejecucion.daemon = True
        self.hilo_ejecucion.start()
        
        # Verificar periodicamente si el hilo terminó
        self._verificar_estado_hilo()
    
    def _verificar_estado_hilo(self):
        if self.hilo_ejecucion and self.hilo_ejecucion.is_alive():
            # El hilo sigue activo, verificar de nuevo en 100ms
            self.root.after(100, self._verificar_estado_hilo)
        else:
            # El hilo terminó, finalizar ejecución
            self.root.after(0, self._finalizar_ejecucion)

    def _ejecutar_optimizacion_thread(self):
        try:
            zona = self.zona_var.get()
            modo = self.modo_var.get()
            cuentas_por_notificador = int(self.cuentas_var.get()) if modo == "multi_notificador" else 0
            
            self.log(f"Procesando zona: {zona}", "info")
            
            # Inicializar componentes
            geocodificador = Geocodificador()
            optimizador = OptimizadorRutas()
            generador_mapas = GeneradorMapas()
            
            # Filtrar por zona
            self.log(f"Filtrando datos para la zona: {zona}...", "info")
            df_zona_filtrado = filtrar_por_zona(self.df_original, zona)
            
            if df_zona_filtrado.empty:
                self.log("No se encontraron datos para la zona especificada", "error")
                return
            
            self.log(f"{len(df_zona_filtrado)} domicilios encontrados en {zona}", "success")
            
            # Guardar CSV filtrado
            archivo_filtrado = f"datos/salida/filtrado_{zona}.csv"
            df_zona_filtrado.to_csv(archivo_filtrado, index=False, encoding='utf-8')
            
            # Geocodificación
            self.log("Geocodificando direcciones...", "info")
            archivo_geocodificado = f"datos/salida/geocodificado_{zona}.csv"
            df = geocodificador.procesar_csv(archivo_filtrado, archivo_geocodificado)
            
            if df.empty:
                self.log("No se pudieron geocodificar las direcciones", "error")
                return
            
            self.log(f"{len(df)} direcciones geocodificadas exitosamente", "success")
            
            # Verificar que hay datos para optimizar
            if len(df) == 0:
                self.log("No hay direcciones válidas para optimizar", "warning")
                return
            
            # Optimización
            if modo == "multi_notificador":
                self.log(f"Generando rutas para {cuentas_por_notificador} cuentas por notificador...", "info")
                chunks = dividir_por_notificadores(df, cuentas_por_notificador)
                
                for i, chunk in enumerate(chunks):
                    self.log(f"Procesando Notificador {i+1} ({len(chunk)} cuentas)...", "info")
                    try:
                        # Verificar que el chunk no esté vacío
                        if len(chunk) == 0:
                            self.log(f"Notificador {i+1} sin direcciones válidas", "warning")
                            continue
                            
                        rutas_chunk = optimizador.optimizar_ruta(chunk, 1)
                        if not rutas_chunk or len(rutas_chunk) == 0:
                            self.log(f"No se pudo optimizar ruta para Notificador {i+1}", "warning")
                            continue
                            
                        ruta_optimizada = rutas_chunk[0]
                        
                        self.log(f"Ruta {i+1} optimizada con {len(ruta_optimizada)} paradas", "success")
                        
                        # Guardar CSV
                        datos_rutas = []
                        for orden, idx in enumerate(ruta_optimizada):
                            fila = chunk.iloc[idx].to_dict()
                            datos_rutas.append({
                                'notificador_id': i + 1,
                                'orden_parada': orden + 1,
                                'ID': fila.get('ID', ''),
                                'Cuenta': fila.get('Cuenta', ''),
                                'Domicilio_Original': fila.get('Domicilio', ''),
                                'Domicilio_Limpio': fila.get('domicilio_limpio', ''),
                                'Zona': fila.get('Zona', ''),
                                'lat': fila.get('lat', ''),
                                'lon': fila.get('lon', '')
                            })
                        
                        df_ruta = pd.DataFrame(datos_rutas)
                        archivo_ruta = f"datos/salida/ruta_{zona}_notificador_{i+1}.csv"
                        df_ruta.to_csv(archivo_ruta, index=False, encoding='utf-8')
                        self.log(f"CSV guardado: {archivo_ruta}", "success")
                        
                        # Generar mapa
                        coordenadas_chunk = list(zip(chunk['lat'], chunk['lon']))
                        archivo_mapa = f"mapas/ruta_{zona}_notificador_{i+1}.png"
                        if generador_mapas.generar_mapa_estatico(coordenadas_chunk, ruta_optimizada, archivo_mapa):
                            self.log(f"Mapa generado: {archivo_mapa}", "success")
                        else:
                            self.log(f"No se pudo generar mapa para Notificador {i+1}", "warning")
                        
                        # Generar enlaces
                        enlace_google = generador_mapas.generar_enlace_google_maps(coordenadas_chunk, ruta_optimizada)
                        self.log(f"Enlace Google Maps Notificador {i+1}: {enlace_google}", "info")
                        
                    except Exception as e:
                        self.log(f"Error en notificador {i+1}: {str(e)}", "error")
                        continue
            else:
                self.log("Optimizando ruta única...", "info")
                try:
                    rutas_optimizadas = optimizador.optimizar_ruta(df, 1)
                    if not rutas_optimizadas or len(rutas_optimizadas) == 0:
                        self.log("No se pudo optimizar la ruta única", "error")
                        return
                        
                    ruta_optimizada = rutas_optimizadas[0]
                    
                    self.log(f"Ruta única optimizada con {len(ruta_optimizada)} paradas", "success")
                    
                    # Guardar CSV
                    datos_ruta = []
                    for orden, idx in enumerate(ruta_optimizada):
                        fila = df.iloc[idx].to_dict()
                        datos_ruta.append({
                            'orden_parada': orden + 1,
                            'ID': fila.get('ID', ''),
                            'Cuenta': fila.get('Cuenta', ''),
                            'Domicilio_Original': fila.get('Domicilio', ''),
                            'Domicilio_Limpio': fila.get('domicilio_limpio', ''),
                            'Zona': fila.get('Zona', ''),
                            'lat': fila.get('lat', ''),
                            'lon': fila.get('lon', '')
                        })
                    
                    df_ruta = pd.DataFrame(datos_ruta)
                    archivo_rutas = f"datos/salida/ruta_unica_{zona}.csv"
                    df_ruta.to_csv(archivo_rutas, index=False, encoding='utf-8')
                    self.log(f"CSV de ruta guardado: {archivo_rutas}", "success")
                    
                    # Generar mapa
                    coordenadas = list(zip(df['lat'], df['lon']))
                    archivo_mapa = f"mapas/ruta_unica_{zona}.png"
                    if generador_mapas.generar_mapa_estatico(coordenadas, ruta_optimizada, archivo_mapa):
                        self.log(f"Mapa generado: {archivo_mapa}", "success")
                    else:
                        self.log("No se pudo generar el mapa de la ruta única", "warning")
                    
                    # Generar enlaces
                    enlace_google = generador_mapas.generar_enlace_google_maps(coordenadas, ruta_optimizada)
                    enlace_osm = generador_mapas.generar_enlace_osm(coordenadas, ruta_optimizada)
                    self.log(f"📱 Enlace Google Maps: {enlace_google}", "info")
                    self.log(f"🗺️ Enlace OSM: {enlace_osm}", "info")
                    
                except Exception as e:
                    self.log(f"Error en optimización: {str(e)}", "error")
                    raise
            
            # Limpiar archivo temporal
            try:
                if os.path.exists(archivo_filtrado):
                    os.remove(archivo_filtrado)
                    self.log(f"Archivo temporal eliminado: {archivo_filtrado}", "info")
            except:
                pass
            
            self.log("Proceso completado exitosamente!", "success")
            self.log("Resultados guardados en: datos/salida/", "info")
            self.log("Mapas generados en: mapas/", "info")
            
        except Exception as e:
            self.log(f"Error durante la optimización: {str(e)}", "error")
        finally:
            # Marcar ejecución como terminada
            self.ejecucion_activa = False
    
    def _finalizar_ejecucion(self):
        self.progress.stop()
        self.ejecutar_btn.config(state="normal")
        self.ejecucion_activa = False
        messagebox.showinfo("Completado", "Proceso de optimización finalizado")
    
    def ver_mapas(self):
        mapas_dir = "mapas"
        if os.path.exists(mapas_dir) and os.listdir(mapas_dir):
            try:
                os.startfile(mapas_dir)
            except:
                messagebox.showinfo("Mapas", f"Los mapas están en: {os.path.abspath(mapas_dir)}")
        else:
            messagebox.showwarning("No hay mapas", "La carpeta 'mapas' está vacía o no existe")
    
    def abrir_carpeta_resultados(self):
        resultados_dir = "datos/salida"
        if os.path.exists(resultados_dir):
            try:
                os.startfile(resultados_dir)
            except:
                messagebox.showinfo("Resultados", f"Los resultados están en: {os.path.abspath(resultados_dir)}")
        else:
            messagebox.showwarning("Carpeta no encontrada", "La carpeta 'datos/salida' no existe")

def main():
    root = tk.Tk()
    app = ModernOptimizadorRutasGUI(root)
    
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