"""selldatatoai: Python client for the Data Asset Score API (https://www.selldatatoai.com/api/)."""
from .client import BATCH_MAX, VERSION, DataAssetScoreClient, SellDataToAIError

__version__ = VERSION
__all__ = ["DataAssetScoreClient", "SellDataToAIError", "BATCH_MAX", "__version__"]
