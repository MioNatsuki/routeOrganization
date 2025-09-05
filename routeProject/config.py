#routeProject/config.py
# Configuración de servicios OSM
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OSRM_URL = "http://router.project-osrm.org/route/v1/driving"
STATIC_MAP_URL = "https://staticmap.openstreetmap.de/staticmap.php"

# Configuración de geocodificación
GEOCODING_BATCH_SIZE = 50
GEOCODING_DELAY = 1.0  # OSM pide 1 segundo entre requests
USER_AGENT = "OptimizadorRutas/1.0 (milagros.115295@gmail.com)"  # Required by Nominatim

# Configuración de optimización
DEPOT_INDEX = 0