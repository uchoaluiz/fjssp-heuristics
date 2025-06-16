from ..instance.instance import Instance
from mip import Model, xsum, minimize, CBC, OptimizationStatus, BINARY, CONTINUOUS


class Model:
    def __init__(self, instance: Instance) -> None:
        self._instance = instance
        self._create_model()

    def _create_model(self) -> None:
        instance = self._instance
