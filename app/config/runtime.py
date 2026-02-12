import os
from app.core.pipeline_mode import PIPELINE_MODE

# Runtime flags
PROD_STRICT = PIPELINE_MODE == "strict"
BOOTSTRAP = PIPELINE_MODE == "bootstrap"
