import os
import json
from pathlib import Path

DEFAULT_CONFIG_FILE = "anomaly_config.json"


def load_anomaly_config(path: str | None = None) -> dict:
    """Load anomaly detection configuration from JSON file.

    Parameters
    ----------
    path: str | None
        Path to the configuration file. If not provided, the path is taken
        from the ``ANOMALY_CONFIG`` environment variable or defaults to
        ``anomaly_config.json`` in the working directory.
    Returns
    -------
    dict
        Configuration dictionary. If the file doesn't exist or is invalid,
        an empty dictionary is returned.
    """
    if path is None:
        path = os.getenv("ANOMALY_CONFIG", DEFAULT_CONFIG_FILE)
    try:
        data = json.loads(Path(path).read_text())
        if isinstance(data, dict):
            return data
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return {}
