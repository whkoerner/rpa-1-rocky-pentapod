# Rocky Brain browser console

This dependency-free webpage connects to the Uno over USB, displays the exact Chordic tokens, and speaks the matching English phrase when translation mode is enabled.

## Run it

1. Upload the Uno firmware first.
2. Close Arduino Serial Monitor.
3. Open `index.html` in desktop Chrome or Edge.
4. If the **Connect** button reports that Web Serial is unavailable, serve this folder locally:
   - Windows: `py -m http.server 8000`
   - macOS/Linux: `python3 -m http.server 8000`
5. Open `http://localhost:8000` in desktop Chrome or Edge.
6. Select the Uno serial port when prompted.

No internet connection or cloud AI is used. The English voice comes from the browser/operating system.
