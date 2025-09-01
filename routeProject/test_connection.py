import requests
import socket

def test_servicio(url, nombre):
    try:
        print(f"🔍 Probando {nombre}...")
        dominio = url.split('//')[1].split('/')[0]
        socket.gethostbyname(dominio)
        print(f"   ✅ DNS resuelto")
        
        response = requests.get(url, timeout=10)
        print(f"   ✅ HTTP Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

# Testear servicios
servicios = {
    "Nominatim": "https://nominatim.openstreetmap.org",
    "OSRM": "http://router.project-osrm.org", 
    "Static Maps": "https://staticmap.openstreetmap.de",
    "Google Maps": "https://maps.googleapis.com"
}

for nombre, url in servicios.items():
    test_servicio(url, nombre)
    print()