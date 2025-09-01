import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk
import os

class MapaViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Visualizador de Rutas Optimizadas")
        self.root.geometry("1000x700")
        
        # Frame principal
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)
        
        # Título
        ttk.Label(self.main_frame, text="🗺️ Visualizador de Rutas", 
                 font=("Arial", 16, "bold")).grid(row=0, column=0, pady=10)
        
        # Canvas para el mapa
        self.canvas = tk.Canvas(self.main_frame, bg="white", relief=tk.SUNKEN, borderwidth=2)
        self.canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # Frame de controles
        self.control_frame = ttk.Frame(self.main_frame)
        self.control_frame.grid(row=2, column=0, pady=10)
        
        # Botones
        ttk.Button(self.control_frame, text="Cargar Mapa", 
                  command=self.cargar_mapa).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Abrir Carpeta", 
                  command=self.abrir_carpeta).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.control_frame, text="Salir", 
                  command=root.quit).pack(side=tk.LEFT, padx=5)
        
        self.current_image = None
    
    def cargar_mapa(self, image_path=None):
        """Carga y muestra un mapa en el canvas"""
        if not image_path:
            from tkinter import filedialog
            image_path = filedialog.askopenfilename(
                initialdir="mapas",
                title="Seleccionar mapa",
                filetypes=[("PNG files", "*.png"), ("All files", "*.*")]
            )
        
        if image_path and os.path.exists(image_path):
            try:
                # Cargar imagen con PIL
                image = Image.open(image_path)
                
                # Redimensionar manteniendo aspect ratio
                max_width, max_height = 900, 500
                image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # Convertir para tkinter
                self.current_image = ImageTk.PhotoImage(image)
                
                # Limpiar canvas y mostrar imagen
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image)
                self.canvas.config(width=image.width, height=image.height)
                
                # Actualizar título
                self.root.title(f"Visualizador de Rutas - {os.path.basename(image_path)}")
                
            except Exception as e:
                tk.messagebox.showerror("Error", f"No se pudo cargar la imagen: {e}")
    
    def abrir_carpeta(self):
        """Abre la carpeta de mapas"""
        import subprocess
        import os
        
        mapas_dir = "mapas"
        if os.path.exists(mapas_dir):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(mapas_dir)
                elif os.name == 'posix':  # macOS/Linux
                    subprocess.run(['open', mapas_dir] if os.name == 'posix' 
                                 else ['xdg-open', mapas_dir])
            except:
                tk.messagebox.showinfo("Carpeta", f"Los mapas están en: {os.path.abspath(mapas_dir)}")
        else:
            tk.messagebox.showwarning("Carpeta no encontrada", "La carpeta 'mapas' no existe")

def mostrar_mapa(image_path=None):
    """Función para mostrar un mapa específico"""
    root = tk.Tk()
    app = MapaViewer(root)
    if image_path:
        app.cargar_mapa(image_path)
    root.mainloop()

if __name__ == "__main__":
    mostrar_mapa()