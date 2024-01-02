# NODE_REGISTRY = set()

# class ALFNode:
#     def __init__(self, name):
#         self.name = name
#         if name in NODE_REGISTRY: 
#             raise ValueError(f"{name} already exists! use another name")
#         NODE_REGISTRY.add(name)


# class ALFDataNode(ALFNode, abc.ABC):

#     def __init__(self, name):
#         super().__init__(name)
#         self._value = np.nan

    
# class ALFWorkNode(ALFNode, abc.ABC):

#     def __init__(self, name):
#         super().__init__(name)
#         self.registered_inputs = {}
#         self.registered_outputs = {}

#     @abc.abstractmethod
#     def run(market, **kwargs):
#         pass

#     # registered nodes get viewed for extraction
#     def register_inputs(self, data_nodes):
#         for node in data_nodes:
#             assert isinstance(node, ALFDataNode), "must be a list of data nodes"
#             self.registered_inputs[node.name] = copy.deepcopy(node.value)
        
#     def register_outputs(self, data_nodes):
#         for node in data_nodes:
#             assert isinstance(node, ALFDataNode), "must be a list of data nodes"
#             self.registered_outputs[node.name] = copy.deepcopy(node.value)



# class ALFAlgStep(ALFWorkNode, abc.ABC):

#     def __init__(self, name):
#         super().__init__(name)
#         self.new_orders = []

#     def send_order(self, order):
#         assert isinstance(order, ALFOrder), "Not a valid order"
#         self.new_orders.append(order)

#     @abc.abstractmethod
#     def run(self):
#         pass



# class ALFAlgTask(ALFWorkNode, abc.ABC):

#     def __init__(self, name):
#         super().__init__(name)
#         self.work_nodes = []


#     def __init_subclass__(cls, is_parent_node=False) -> None:
#         if not is_parent_node:
#             return
        
#         if cls.__name__ in ALG_REGISTRY: 
#             raise ValueError(f"Two algs have the same name {cls.__name__}")
        
#         ALG_REGISTRY[cls.__name__] = cls
#         cls.is_parent_node = is_parent_node

#     def register_work_nodes(self, work_nodes):
#         for node in work_nodes:
#             assert issubclass(node.__class__, ALFAlgStep) or issubclass(node.__class__, ALFAlgTask), f"{node} not a ALFWorkNode"
#         self.work_nodes = work_nodes

#     def run(self):
#         for step in self.work_nodes:
#             step.run()


# class NodeCounterStep(ALFAlgStep):
#     def __init__(self, name, node_counter, two_counter):
#         super().__init__(name)
#         self.register_outputs([node_counter])
#         self.node_counter = node_counter
#         self.two_counter = two_counter

#     def run(self):
#         self.node_counter.value += 1
#         self.two_counter += 2
#         print(f"{self.name} has two counter: {self.node_counter.value}")

# class ChildTask(ALFAlgTask):

#     def __init__(self, name, node_counter, two_counter):
#         super().__init__(name)
#         self.register_inputs([
#             node_counter
#         ])

#         self.register_work_nodes([
#             NodeCounterStep("NodeCounterStep2", node_counter, two_counter),
#             NodeCounterStep("NodeCounterStep3", node_counter, two_counter),
#             NodeCounterStep("NodeCounterStep4", node_counter, two_counter),
#         ])


# class DemoAlg(ALFAlgTask, is_parent_node=True):

#     def __init__(self, name, offset=0):
#         super().__init__(name)
#         self.node_counter = ALFDataNode("kNodeCounterNode")
#         self.node_counter.value = offset
#         self.two_counter =  0
#         self.register_inputs([
#             self.node_counter
#         ])

#         self.register_work_nodes([
#             NodeCounterStep("NodeCounterStep1", self.node_counter, self.two_counter),
#             ChildTask("ALFNodeTask1", self.node_counter, self.two_counter)
#         ])



# class AdderNode(ALFAlgNode):

#     def __init__(self, name, node_number):
#         super().__init__(name)
#         self.node_number = node_number

#     def run(self, x):
#         x += 1
#         self.set_extraction("node-value", x)
#         return x

# class DemoAlg2(ALFAlgNode, is_start_node=True):

#     def __init__(self, name):
#         super().__init__(name)
#         self.node_counter = 0
#         self.adder_node0 = AdderNode("ADDER1", 0)
#         self.adder_node1 = AdderNode("ADDER2", 1)
#         self.adder_node2 = AdderNode("ADDER3", 2)

#         self.register_alg_node([
#             self.adder_node0,
#             self.adder_node1,
#             self.adder_node2,
#         ])


    
#     def run(self, offset):
#         self.node_counter += offset
#         self.set_extraction("init_value", self.node_counter)
#         self.node_counter = self.adder_node0.run(self.node_counter)
#         self.node_counter = self.adder_node1.run(self.node_counter)
#         self.node_counter = self.adder_node2.run(self.node_counter)
#         self.set_extraction("final_value", self.node_counter)


# alg = DemoAlg2("DEMO")
# alg.run(3)
# print(alg.get_alg_frame())
# alg.run(0)
# print(alg.get_alg_frame())
# alg.run(1)
# print(alg.get_alg_frame())

# import requests
# import json
# HEADER = {
#   'Accepts': 'application/json',
#   'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
# }
# num_tokens = 24
# response = requests.get("https://token.jup.ag/strict")
# response = json.loads(response.text)

# response = requests.get("https://pro-api.coinmarketcap.com/v2/cryptocurrency/info?id=16116",headers=HEADER)
# tradeable_assets = json.loads(response.text)
# print("wait")
# import requests
# ID_MAP = {
#     'SOL': "So11111111111111111111111111111111111111112",
#     'PYTH': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
#     'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
# }
# tx_id = "3H5AcD7Wr6PvDCj4NJMdh5JjikMGx1sAFUk4SLKmWurCggZx9JXLpujPcD22P3wtjhkEtGCbnW2gxFJ8yer58At2"
# # out = requests.get(f"http://localhost:3000/transaction_meta?txid={tx_id}")
# ids = ','.join([v for v in ID_MAP.values()])
# out = requests.get(f"http://localhost:3000/get_balance?ids={ids}")
# # tx_data = json.loads(out.text)
# print(out.text)

class ALFWallet:

    def __init__(self):
        self.balances = {2: 'a', 4 : 'c'}

    def to_dict(self):
        return self.balances

x = ALFWallet()
y = x.to_dict()
y[2] = 'r'

print(x.to_dict())
