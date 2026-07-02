import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# EPIC 18 (US 18.1) — bloque le lancement si des SVG de pièces sont manquants
# (astuce PO : éviter de découvrir des 404 sur l'échiquier après coup).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
from validate_assets import main as _validate_assets
if _validate_assets() != 0:
    sys.exit(1)

port = int(os.environ.get("PORT", 8080))
import http.server
httpd = http.server.HTTPServer(("", port), http.server.SimpleHTTPRequestHandler)
print(f"Serving on port {port}", flush=True)
httpd.serve_forever()
