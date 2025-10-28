import json
import os
from functools import lru_cache

from google.cloud import storage
from google.oauth2 import service_account


@lru_cache(maxsize=1)
def get_gcs_client():
    """Get cached GCS client from GOOGLE_CLOUD_CREDENTIALS_JSON env var."""
    creds_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS_JSON")
    if not creds_json:
        raise ValueError(
            "GOOGLE_CLOUD_CREDENTIALS_JSON environment variable not set. "
            "Set it to your service account JSON credentials."
        )

    info = json.loads(creds_json)
    credentials = service_account.Credentials.from_service_account_info(info)
    return storage.Client(credentials=credentials)
