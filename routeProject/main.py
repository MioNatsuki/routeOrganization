import sys
import os
import argparse

def main():
    # Verificar si hay argumentos de línea de comandos
    if len(sys.argv) > 1 and not any(arg in sys.argv for arg in ['--gui', '--help']):
        # Modo línea de comandos con interfaz gráfica opcional
        parser = argparse.ArgumentParser(description='Route Optimizer Pro - AI-Powered Delivery Route Optimization')
        parser.add_argument('--archivo', required=True, help='Input CSV file path')
        parser.add_argument('--zona', required=True, help='Zone to optimize')
        parser.add_argument('--cuentas-por-notificador', type=int, default=0, 
                           help='Number of accounts per notifier (0 for single route)')
        parser.add_argument('--cli-only', action='store_true', 
                           help='Run in CLI-only mode without GUI')
        parser.add_argument('--gui', action='store_true', 
                           help='Force GUI mode with pre-loaded parameters')
        
        try:
            args = parser.parse_args()
            
            # Validar archivo
            if not os.path.exists(args.archivo):
                print(f"Error: File '{args.archivo}' no encontrado")
                return 1
            
            if args.cli_only:
                # Modo CLI puro
                from main_cli import main as cli_main
                # Simular argumentos para main_cli
                sys.argv = [
                    'main_cli.py',
                    '--archivo', args.archivo,
                    '--zona', args.zona,
                    '--cuentas-por-notificador', str(args.cuentas_por_notificador)
                ]
                cli_main()
            else:
                # Modo CLI con GUI
                try:
                    import tkinter as tk
                    from gui import ModernOptimizadorRutasGUI
                    
                    print("Empezando la optimización de rutas")
                    print(f"Archivo: {args.archivo}")
                    print(f"Zona: {args.zona}")
                    print(f"Modo: {'Multi-notifier' if args.cuentas_por_notificador > 0 else 'Single route'}")
                    
                    root = tk.Tk()
                    app = ModernOptimizadorRutasGUI(root)
                    
                    # Pre-cargar parámetros y ejecutar
                    app.ejecutar_como_cli(args.archivo, args.zona, args.cuentas_por_notificador)
                    
                    root.mainloop()
                    return 0
                    
                except ImportError as e:
                    print(f"GUI no está disponible: {e}")
                    from main_cli import main as cli_main
                    sys.argv = [
                        'main_cli.py',
                        '--archivo', args.archivo,
                        '--zona', args.zona,
                        '--cuentas-por-notificador', str(args.cuentas_por_notificador)
                    ]
                    cli_main()
                    
        except SystemExit as e:
            # argparse.ArgumentParser llamó a sys.exit()
            return e.code if hasattr(e, 'code') else 1
        except Exception as e:
            print(f"Error: {e}")
            return 1
            
    else:
        # Modo GUI interactivo
        try:
            import tkinter as tk
            from gui import main as gui_main
            
            print("Iniciando la optimización de rutas...")
            
            # Ejecutar GUI
            gui_main()
            return 0
            
        except ImportError as e:
            print(f"Error loading GUI: {e}")
            print("\nYou can still use CLI mode:")
            return 1
        except Exception as e:
            print(f"Unexpected error: {e}")
            return 1

def check_dependencies():
    """Verifica dependencias críticas"""
    required_modules = [
        'pandas', 'requests', 'matplotlib', 'folium', 
        'geopy', 'numpy', 'ortools'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    
    if missing_modules:
        print("Missing required dependencies:")
        for module in missing_modules:
            print(f"   - {module}")
        print("\nInstall with: pip install " + " ".join(missing_modules))
        return False
    
    return True

if __name__ == "__main__":
    # Verificar dependencias si es necesario
    if '--check-deps' in sys.argv:
        if check_dependencies():
            print("All dependencies are installed")
            sys.exit(0)
        else:
            sys.exit(1)
    
    # Ejecutar aplicación principal
    try:
        exit_code = main()
        sys.exit(exit_code or 0)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)