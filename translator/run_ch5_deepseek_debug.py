import traceback
from pathlib import Path

LOG = Path(__file__).with_name("sidecar_debug.log")

try:
    LOG.write_text("Starting sidecar...\n", encoding="utf-8")
    import ch5_translator_sidecar_deepseek as sidecar

    app = sidecar.SidecarApp()
    app.root.geometry("1240x720+60+60")
    app.root.deiconify()
    app.root.lift()
    app.root.focus_force()
    LOG.write_text("Window created. Entering mainloop.\n", encoding="utf-8")
    app.run()
    LOG.write_text("Mainloop exited normally.\n", encoding="utf-8")
except Exception:
    LOG.write_text(traceback.format_exc(), encoding="utf-8")
    raise
