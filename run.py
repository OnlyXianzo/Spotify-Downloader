import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure dependencies are installed or check environment
    # ...

    # Run the web app
    # Use reload=True for dev, but this is the runner script.
    print("Starting SpotDL Pro Web Interface...")
    print("Open http://localhost:8000 in your browser.")

    # Check if we need to install ffmpeg?
    # SpotDL wrapper usually handles checking, but good to be explicit or leave it to user/spotdl

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=False)
