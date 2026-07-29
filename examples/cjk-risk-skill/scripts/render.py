import os
import subprocess
import tempfile
from pathlib import Path


env = os.environ.copy()
env["HOME"] = str(Path(tempfile.gettempdir()) / "example-render-home")
subprocess.run(
    ["soffice", "--headless", "--convert-to", "pdf", "input.docx"],
    check=False,
    env=env,
)
