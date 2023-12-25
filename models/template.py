
import abc 

ALG_REGISTRY = {}

class AlafantAlg(abc.ABC):

    def __init_subclass__(cls) -> None:
       if cls.__name__ in ALG_REGISTRY: 
           raise ValueError(f"Two algs have the same name {cls.__name__}")
       ALG_REGISTRY[cls.__name__] = cls

    @abc.abstractmethod
    def run(self, market):
        pass

def init_alg_registry():
    from .smart_dca.smart_dca import SmartDCA


