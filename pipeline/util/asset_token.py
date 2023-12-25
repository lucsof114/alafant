import requests
import json
import uuid


with open('config.json', 'r') as file:
    CONFIG = json.load(file)

class BotOrder:
    PENDING = 0
    SENT = 1
    COMPLETED = 2
    FAILED = 3

    def __init__(self, is_buy, amount, token_id, slippageBPS=CONFIG["DEFAULT_SLIPPAGE"]):
        self.is_buy = is_buy
        self.amount = amount
        self.status = BotOrder.PENDING
        self.token_id = token_id
        self.slippage = slippageBPS
        self.id = str(uuid.uuid4())

    @staticmethod
    def buy(amount, token_id):
        return BotOrder(True, amount, token_id)
    
    @staticmethod
    def sell(amount, token_id):
        return BotOrder(False, amount, token_id)
    
    def to_dict(self):
        return {
            "inputTokenAddress": CONFIG['BASE_CURRENCY'] if self.is_buy else self.token_id,
            "outputTokenAddress":  self.token_id if self.is_buy else CONFIG['BASE_CURRENCY'],
            "swapAmount": self.amount,
            "slippageBps": self.slippage,
            "orderID": str(self.id)
        }


class Token:
    
    def __init__(self, data, cmc_id): 
        self.data = data
        self.unix_ts = None
        self.cmc_id = cmc_id
        self.quote = None

    @property
    def price(self):
        return self.quote['price'] if self.quote is not None else None

    @property
    def volume_24h(self):
        return self.quote['volume_24h'] if self.quote is not None else None
   
    @property
    def volume_change_24h(self):
        return self.quote['volume_change_24h'] if self.quote is not None else None

    @property
    def percent_change_1h(self):
        return self.quote['percent_change_1h'] if self.quote is not None else None

    @property
    def percent_change_24h(self):
        return self.quote['percent_change_24h'] if self.quote is not None else None

    @property
    def percent_change_7d(self):
        return self.quote['percent_change_7d'] if self.quote is not None else None

    @property
    def percent_change_30d(self):
        return self.quote['percent_change_30d'] if self.quote is not None else None

    @property
    def percent_change_60d(self):
        return self.quote['percent_change_60d'] if self.quote is not None else None

    @property
    def percent_change_90d(self):
        return self.quote['percent_change_90d'] if self.quote is not None else None

    @property
    def market_cap(self):
        return self.quote['market_cap'] if self.quote is not None else None

    @property
    def market_cap_dominance(self):
        return self.quote['market_cap_dominance'] if self.quote is not None else None

    @property
    def fully_diluted_market_cap(self):
        return self.quote['fully_diluted_market_cap'] if self.quote is not None else None

    @property
    def timestamp(self):
        return self.quote['last_updated'] if self.quote is not None else None

    @property
    def stake(self):
        pass

    @property
    def address(self):
        return self.data["address"]
    
    @property
    def name(self):
        return self.data["name"]
    
    @property
    def symbol(self):
        return self.data["symbol"]

    @property
    def decimals(self):
        return self.data["decimals"]
    
    def price_update(self, data, address):
        assert self.addresss == address, "wrong address"
    
    def order_update(self, data, address):
        assert self.addresss == address, "wrong address"
    

class ExchangeMarket:

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
                current_order.status = BotOrder.FAILED
            elif value == "PENDING":
                current_order.status = BotOrder.PENDING
                continue
            elif value != None:
                current_order.status = BotOrder.COMPLETED
            self.finished_orders[id] = current_order
            del self.pending_orders[id]

    def update_quotes(self, data):
        for address, quote in data.items():
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

# SOL_ID = 'So11111111111111111111111111111111111111112'

# response = requests.get(f'https://token.jup.ag/strict')
# market = ExchangeMarket(json.loads(response.text))
# # order = BotOrder.sell(0.1, SOL_ID) 
# order = BotOrder.buy(8, SOL_ID) 
# market.place_orders([order])

# out = requests.get(f"http://localhost:3000/order_status")
# print(out.text)

# tokens = [
#     SOL_ID,
#     CONFIG['BASE_CURRENCY']
# ]
# headers = {
#   'Accepts': 'application/json',
#   'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
# }

# def get_tokens(): 
#     response = requests.get("https://token.jup.ag/strict")
#     tradeable_assets = json.loads(response.text)

#     response = requests.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/map",headers=headers)
#     cmc_assets = json.loads(response.text)

#     cmc_assets = {x['platform']['token_address']: str(x['id']) for x in cmc_assets['data'] if x['platform'] is not None}
#     out = []
#     for asset in tradeable_assets:
#         if asset['address'] not in cmc_assets:
#             continue
#         out.append(Token(data=asset, cmc_id=cmc_assets[asset['address']]))
#     return out

# tokens = get_tokens()
# params = "id=" + ",".join([x.cmc_id for x in tokens])

# ids = []
# response = requests.get(f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?{params}', headers=headers) 

# print("Wait")
