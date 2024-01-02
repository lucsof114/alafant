import uuid
import requests
import json 
from datetime import datetime
import copy 
import logging

logging.basicConfig(format='%(levelname)s: [%(filename)s:linenum:%(lineno)d] %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

with open('config.json', 'r') as file:
    CONFIG = json.load(file)

class ALFOrder:
    SENT = 0
    PENDING = 1
    COMPLETED = 2
    FAILED = 3

    def __init__(self, is_buy, amount, quote, slippageBPS=CONFIG["DEFAULT_SLIPPAGE"]):
        self.is_buy = is_buy
        self.amount_out = amount
        self.status = ALFOrder.PENDING
        self.token_id = quote.token_id
        self.slippage = slippageBPS
        self.quote_price = quote.price
        self.quote_timestamp = quote.quote_timestamp
        self.id = str(uuid.uuid4())
        self.amount_in = None
        self.exec_timestamp = None
        self.market_timestamp = None
        self.tx_id = None
        self.tx_fee = None

    @staticmethod
    def buy(amount, quote):
        return ALFOrder(True, amount, quote)
    
    @staticmethod
    def sell(amount, quote):
        return ALFOrder(False, amount, quote)
    
    def to_dict(self):
        return {
                "type": "buy" if self.is_buy else "sell",
                "amount_out": self.amount_out,
                "amount_in": self.amount_in,
                "status": self.status,
                "token_id": self.token_id,
                "slippage": self.slippage,
                "quote_price": self.quote_price,
                "order_id": self.id,
                "exec_timestamp": self.exec_timestamp,
                "market_timestamp": self.market_timestamp,
                "quote_timestamp": self.quote_timestamp,
                "id": self.id,
                "tx_id": self.tx_id,
                "tx_fee": self.tx_fee,
        }

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
        self.orders_to_send = []


class JupiterDEX:

    def is_live(self):
        try:
            out = requests.get(f"http://localhost:3000/is_alive")
            return out.text == "TRUE"
        except:
            pass
        return False

    def execute_orders(self, orders):
        meta = []
        for order in orders.values():
            order.status = ALFOrder.PENDING
            meta.append({
                "inputTokenAddress": CONFIG['BASE_CURRENCY'] if order.is_buy else order.token_id,
                "outputTokenAddress":  order.token_id if order.is_buy else CONFIG['BASE_CURRENCY'],
                "swapAmount": order.amount_out if order.is_buy else order.amount_out / order.quote_price,
                "slippageBps": order.slippage,
                "orderID": str(order.id)
            })

        if len(meta) != 0:
            out = requests.post(f"http://localhost:3000/execute-swaps", json=meta)

    def update_orders(self, order_book):
        order_ids = [o.id for o in order_book.values() if o.status == ALFOrder.PENDING]
        out = requests.get(f"http://localhost:3000/order_status?ids={','.join(order_ids)}")
        data = json.loads(out.text)
        should_update_wallet = False
        for id, value in data.items():
            order = order_book[id]
            status = value['status']
            if value == "FAILED":
                logger.info(f"Order ID: {id} STATUS: FAILED")
                order.status = ALFOrder.FAILED
            elif value == "PENDING":
                continue
            elif status == 'COMPLETE':
                order.tx_id = value['tx_id']
                order.status = ALFOrder.COMPLETED
                out = requests.get(f"http://localhost:3000/transaction_meta?txid={order.tx_id}")
                tx_data = json.loads(out.text)
                order.exec_timestamp = datetime.utcfromtimestamp(tx_data['blockTime']).isoformat()
                order.tx_fee = tx_data['meta']['fee'] / tx_data['LAMPORTS_PER_SOL']
                relevant_id = order.token_id if order.is_buy else CONFIG['BASE_CURRENCY']
                pre_balance = value['pre_trade_balance']
                post_balance =  value['post_trade_balance']
                order.amount_in = post_balance[relevant_id] - pre_balance[relevant_id]
                should_update_wallet = True
                delta_balance = {tid: post_balance[tid] - pre_balance[tid] for tid in [CONFIG['BASE_CURRENCY'], order.token_id] }
                logger.info(f"Order ID: {id} STATUS: COMPLETE, TX_ID: {order.tx_id}")
                logger.info(f"Trade Value: {delta_balance}")
        return should_update_wallet

class ALFWallet:

    def __init__(self, token_ids):
        self.balances = {token_id: 0 for token_id in token_ids}
        requests.post(f"http://localhost:3000/set_tokens", json={'token_ids': token_ids})
        self.update_wallet()
    
    def update_wallet(self):
        out = requests.get(f"http://localhost:3000/get_balance")
        self.balances = json.loads(out.text)
    
    def to_dict(self):
        return copy.deepcopy(self.balances)

