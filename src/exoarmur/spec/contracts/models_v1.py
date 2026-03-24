import sys
from spec.contracts import models_v1 as _real_models_v1

sys.modules[__name__] = _real_models_v1
