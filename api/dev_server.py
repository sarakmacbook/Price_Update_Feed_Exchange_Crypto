"""Run the Vercel function locally — no Vercel CLI required.

    python api/dev_server.py            # http://localhost:8000
    python api/dev_server.py 3000       # custom port

It serves exactly the same handler Vercel serves (``api/index.py``), so you can
open the status page, check ``/api/health`` and poke ``/api/cron`` before
deploying:

    curl "http://localhost:8000/api/health"
    CRON_SECRET=dev curl "http://localhost:8000/api/cron?key=dev"

Environment variables are read the same way as in production (BOT_TOKEN,
ADMIN_IDS, CRON_SECRET, KV_REST_API_URL, …) — see .env.example.
"""

import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# behave like the deployed function: config errors are reported instead of
# exiting the process (set P2P_SERVERLESS=0 to force local/exit behaviour)
os.environ.setdefault("P2P_SERVERLESS", "1")

from api.index import handler  # noqa: E402  (needs the path above)

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), handler)
    print(f"▲ Vercel handler running on http://{host}:{port}")
    print("   /  ·  /api/health  ·  /api/cron?key=$CRON_SECRET  ·  /api/setup?key=$CRON_SECRET")
    print("   Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
