import argparse
import functools
import mimetypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Start frontend static server with correct JS MIME.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5173, help="Bind port (default: 5173)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    frontend_root = project_root / "frontend"
    if not frontend_root.exists():
        raise SystemExit(f"frontend directory not found: {frontend_root}")

    # Ensure module scripts are served with a JavaScript MIME type.
    mimetypes.add_type("text/javascript", ".js")

    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(frontend_root))
    server = ThreadingHTTPServer((args.host, args.port), handler)

    print(f"[frontend] Serving {frontend_root}")
    print(f"[frontend] URL: http://{args.host}:{args.port}/index.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
