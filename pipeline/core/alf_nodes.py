

# NODE_REGISTRY = {}

# class ALFNode:
#     def __init__(self, name, work_node_name):
#         self.name = name
#         self.work_node = work_node_name

#     def __init_subclass__(cls, name):
#        if name in NODE_REGISTRY: 
#            raise ValueError(f"{name} already exists! use another name")
#        NODE_REGISTRY[name] = cls



class Foo:
    def __init_subclass__(cls) -> None:
        print("1")

class Bar(Foo):
    pass
    # def __init_subclass__(cls) -> None:
    #     Foo.__init_subclass__()
    #     print("2")

class Test(Bar):

    def __init__(cls):
        pass

x = Test()
print(type(x).__name__)