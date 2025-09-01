import sys
import os

def main():
    """Punto de entrada principal - Decide si usar CLI o GUI"""
    if len(sys.argv) > 1:
        # Modo línea de comandos
        from main_cli import main as cli_main
        cli_main()
    else:
        # Modo gráfico
        try:
            from gui import main as gui_main
            gui_main()
        except ImportError as e:
            print(f"Error: {e}")
            print("Ejecuta con argumentos para usar modo línea de comandos")
            print("Ejemplo: python main.py --archivo datos.csv --zona Centro")

if __name__ == "__main__":
    main()