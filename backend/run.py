"""
run.py — Start the ServiceDesk HQ FastAPI server
Usage:
    python run.py
    python run.py --port 8080 --reload
"""
import uvicorn
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host",   default="0.0.0.0")
    parser.add_argument("--port",   default=8000, type=int)
    parser.add_argument("--reload", action="store_true", default=True)
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info"
    )
