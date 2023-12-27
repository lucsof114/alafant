from pipeline.core import ALFAlgNode, ALFOrder


PYTH_ID = 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3'

class SmartDCA(ALFAlgNode):

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
        

        pyth_quote = market_frame[PYTH_ID]
        if self.prev_ts != pyth_quote.timestamp:
            print("PRICE: ")
            print(pyth_quote.price)
        self.prev_ts = pyth_quote.timestamp

        if pyth_quote.price > 10.355: #cents USD
            order = ALFOrder.buy(100, PYTH_ID)
            self.order_id = self.place_order(order)
