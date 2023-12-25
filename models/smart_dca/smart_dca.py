from models.template import AlafantAlg
from pipeline.util.asset_token import BotOrder
PYTH_ID = 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3'

class SmartDCA(AlafantAlg):

    def __init__(self):
        super().__init__()
        self.order = None
        self.prev_ts = None
        pass

    
    def run(self, market):
    
        if self.order is not None:
            self.order = market.get_order(self.order.id)
            if self.order.status == BotOrder.COMPLETED:
                return
            elif self.order.status == BotOrder.FAILED:
                self.order == None
        
        if self.order is not None:
            return
        
        pyth_token = market.get_token(PYTH_ID)
        if self.prev_ts != pyth_token.timestamp:
            print("PRICE: ")
            print(pyth_token.price)
        self.prev_ts = pyth_token.timestamp

        if pyth_token is None:
            return 
        
        if pyth_token.price > 0.355: #cents USD
            self.order = BotOrder.buy(100, PYTH_ID)
            market.execute_order(self.order)