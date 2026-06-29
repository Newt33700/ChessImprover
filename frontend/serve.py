import os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
port = int(os.environ.get("PORT", 8080))
import http.server
httpd = http.server.HTTPServer(("", port), http.server.SimpleHTTPRequestHandler)
print(f"Serving on port {port}", flush=True)
httpd.serve_forever()
