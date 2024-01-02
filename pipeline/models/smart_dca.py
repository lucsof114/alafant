from pipeline.core import ALFAlgNode, ALFOrder


PYTH_ID = 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3'
SOL_ID = 'So11111111111111111111111111111111111111112'

class SmartDCA(ALFAlgNode, is_start_node=True):

    def __init__(self):
        super().__init__(type(self).__name__)
        self.order_id = None
        self.prev_ts = None
        pass

    
    def run(self, market_frame, order_book):
        if self.order_id is not None:
            order = order_book[self.order_id]
            if order.status == ALFOrder.COMPLETED:
                return
            elif order.status == ALFOrder.FAILED:
                self.order_id = None
        
        if self.order_id is not None:
            return
        
        self.set_extraction("some_var", 4)
        pyth_quote = market_frame[PYTH_ID]
        self.prev_ts = pyth_quote.timestamp

        if pyth_quote.price > 0.34: #cents USD
            order = ALFOrder.buy(100, pyth_quote)
            self.order_id = self.place_order(order)

class TestAlg(ALFAlgNode, is_start_node=True):

    def __init__(self):
        super().__init__(type(self).__name__)
        self.was_buy = True
        self.frame_counter = 3
    

    def run(self, market_frame, order_book):
        if self.frame_counter > 2:
            if self.was_buy:
                order = ALFOrder.sell(5, market_frame[SOL_ID])
            else: 
                order = ALFOrder.buy(10, market_frame[SOL_ID])
            self.order_id = self.place_order(order)
            self.frame_counter = 0
            self.was_buy = not self.was_buy
        else:
            self.frame_counter += 1
        # print(self.frame_counter)
        self.set_extraction("frame_count", self.frame_counter)