"""Start the food tracker: python run.py  (then open http://localhost:8000)"""
import os

import uvicorn

if __name__ == "__main__":
    uvicorn.run("food_tracker.app:app", host=os.environ.get("HOST", "127.0.0.1"),
                port=int(os.environ.get("PORT", "8000")), reload=bool(os.environ.get("RELOAD")))
