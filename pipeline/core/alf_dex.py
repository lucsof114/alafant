import uuid
import requests
import json 

with open('config.json', 'r') as file:
    CONFIG = json.load(file)

class ALFOrder:
    SENT = 0
    PENDING = 1
    COMPLETED = 2
    FAILED = 3

    def __init__(self, is_buy, amount, quote, slippageBPS=CONFIG["DEFAULT_SLIPPAGE"]):
        self.is_buy = is_buy
        self.amount = amount
        self.status = ALFOrder.PENDING
        self.token_id = quote.token_id
        self.slippage = slippageBPS
        self.price = quote.price
        self.id = str(uuid.uuid4())
        self.tx_id = None

    @staticmethod
    def buy(amount, token_id):
        return ALFOrder(True, amount, token_id)
    
    @staticmethod
    def sell(amount, token_id):
        return ALFOrder(False, amount, token_id)
    
    def to_dict(self):
        return {
                "type": "buy" if self.is_buy else "sell",
                "amount": self.amount,
                "status": self.status,
                "token_id": self.token_id,
                "slippage": self.slippage,
                "price": self.price,
                "id": self.id,
                "tx_id": self.tx_id,
        }
    # def to_dict(self):
    #     return {
    #         "inputTokenAddress": CONFIG['BASE_CURRENCY'] if self.is_buy else self.token_id,
    #         "outputTokenAddress":  self.token_id if self.is_buy else CONFIG['BASE_CURRENCY'],
    #         "swapAmount": self.amount,
    #         "slippageBps": self.slippage,
    #         "orderID": str(self.id)
    #     }

class ALFMarket:

    def __init__(self, tokens):
        self.tokens = tokens
        self.finished_orders = {}
        self.pending_orders = {}
        self.orders_to_send = []

    def update_pending_orders(self):
        order_ids = [x.id for x in self.pending_orders.values()]
        out = requests.get(f"http://localhost:3000/order_status?ids={','.join(order_ids)}")
        data = json.loads(out.text)
        print("ORDER STATUS: ")
        print(data)
        for id, value in data.items():
            current_order = self.pending_orders[id]
            if value == "FAILED":
                current_order.status = ALFOrder.FAILED
            elif value == "PENDING":
                current_order.status = ALFOrder.PENDING
                continue
            elif value != None:
                current_order.status = ALFOrder.COMPLETED
            self.finished_orders[id] = current_order
            del self.pending_orders[id]

    def update_quotes(self, market_frame):
        for address, quote in market_frame:
            if self.tokens[address].timestamp != quote['last_updated']:
                self.tokens[address].quote = quote
            
    def get_order(self, id):
        if id in self.pending_orders:
            return self.pending_orders[id]
        elif id in self.finished_orders:
            return self.finished_orders[id]
        return None

    def execute_order(self, order):
        if all(order.id != x.id for x in self.orders_to_send):
            self.orders_to_send.append(order) 

    def get_token(self, id):
        if id in self.tokens:
            return self.tokens[id]
        return None
    
    def is_live(self):
        try:
            out = requests.get(f"http://localhost:3000/is_alive")
            return out.text == "TRUE"
        except:
            pass
        return False
    
    def place_orders(self):
        meta = []
        for order in self.orders_to_send:
            meta.append(order.to_dict())
            self.pending_orders[order.id] = order
        if len(self.orders_to_send) != 0:
            out = requests.post(f"http://localhost:3000/execute-swaps", json=meta)
            print(out.text)
        self.orders_to_send = []


