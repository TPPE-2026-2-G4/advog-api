import os
import tempfile

os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/advog_test.sqlite"
)
