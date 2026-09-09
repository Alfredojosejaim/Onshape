"""Smoke test: ventana nativa carga dist/ e invoca api real. Uso: python smoke_prod.py"""
import json
import threading
import webview
from api import Api

OUT = {}


def run():
    w = webview.create_window("smoke", "html/dist/index.html", js_api=Api(),
                              width=1200, height=800)

    def probe():
        try:
            OUT["title"] = w.evaluate_js("document.title")
            OUT["has_api"] = w.evaluate_js("typeof window.pywebview !== 'undefined'")
            OUT["api_methods"] = w.evaluate_js("Object.keys(window.pywebview.api)")
            OUT["react_root"] = w.evaluate_js(
                "document.getElementById('root') ? document.getElementById('root').childElementCount : -1")
        except Exception as e:  # noqa: BLE001
            OUT["error"] = str(e)
        finally:
            w.destroy()

    def loaded():
        # espera al ready del bridge y sondea
        import time
        for _ in range(100):
            try:
                if w.evaluate_js("document.readyState") == "complete":
                    break
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.3)
        time.sleep(2.0)
        probe()

    threading.Thread(target=loaded, daemon=True).start()
    webview.start()
    print(json.dumps(OUT, default=str)[:3000])


if __name__ == "__main__":
    run()
