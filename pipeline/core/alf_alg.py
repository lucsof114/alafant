
import abc 
import numpy as np
import copy
from pipeline.core.alf_market import ALFOrder


ALG_REGISTRY = {}

class ALFAlgNode(abc.ABC): 
    def __init_subclass__(cls, is_start_node=False) -> None:
        if not is_start_node:
            return
        if cls.__name__ in ALG_REGISTRY: 
            raise ValueError(f"Two algs have the same name {cls.__name__}")
        
        ALG_REGISTRY[cls.__name__] = cls

    def __init__(self, name):
        self.name = name
        self.extractions = {}
        self.alg_nodes = []
        self.new_orders = {}

    def register_alg_node(self, nodes):
        for node in nodes:
            assert isinstance(node, ALFAlgNode), f"{node} is not an ALFAlgNode"
            self.alg_nodes.append(node)

    def set_extraction(self, name, value):
        node_name = f"{self.name}-{name}"
        self.extractions[node_name] = copy.deepcopy(value)
    
    def place_order(self, order):
        assert isinstance(order, ALFOrder), f"{order} is not an ALFOrder"
        assert order.id not in self.new_orders, f"{order} was placed twice in one frame"
        self.new_orders[order.id] = order
        return order.id

    def get_alg_frame(self):
        return self.get_dict_from_children(lambda x: x.extractions)
    def get_dict_from_children(self, property_getter):
        out = property_getter(self)
        for alg in self.alg_nodes:
            new_frame = alg.get_alg_frame()
            overlap = set(new_frame.keys()) & set(out.keys())
            if overlap:
                print("Alg frame has conflicting keys. Cannot create frame")
                return {}
            out = out | new_frame
        return out


    def get_orders(self):
        out = self.get_dict_from_children(lambda x: x.new_orders)
        self.new_orders = {}
        return out
    
    @abc.abstractmethod
    def run(self, **kwargs):
        pass
    

def init_alg_registry():
    from ..models import SmartDCA

