from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from pipeline.main import run_one_frame
from pipeline.core import CoinMarketCapComs, ALFOrder, ALFQuote, ALG_REGISTRY, init_alg_registry
from pipeline.models import SmartDCA
import numpy as np
import uuid

START_DATE = datetime.now(timezone.utc) - timedelta(days=10)
END_DATE = datetime.now(timezone.utc) - timedelta(days=2)

DATASET_PATH = "/Users/lucassoffer/Documents/Develop/alafant/dataset/historical"

def aggregate_data(start_date, end_date):
    out = []
    base_path = Path(DATASET_PATH)
    for date_dir in base_path.iterdir():
        dir_date = datetime.fromisoformat(date_dir.name)
        if start_date <= dir_date <= end_date:
            market_frame = {"timestamp": date_dir.name}
            for id_dir in date_dir.iterdir():
                json_path = id_dir / 'USD' / 'market_data.json'
                with open(json_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    market_frame[id_dir.name] = ALFQuote.init_from_cmc_update(id_dir.name, data, 'USD')
            out.append((date_dir.name, market_frame))
    sorted_frames = sorted(out, key=lambda x: datetime.fromisoformat(x[0]))
    return [x[1] for x in sorted_frames]

class RerunDEX:

    def __init__(self, wallet, latency=0):
        self.latency = latency
        self.order_id_to_tx_id = {}

    def execute_orders(self, orders):
        for order in orders.values():
            order.status = ALFOrder.PENDING
            self.order_id_to_tx_id[order.id] = str(uuid.uuid4())

    def update_orders(self, order_book):
        pass

class RerunWallet:
    def __init__(self, wallet_state):
        self.balance = wallet_state
        self.pending_orders = []

    def update_wallet(self):
        pass

    def execute_orders(self, order_book):        
        for order in order_book.values():
            if order.status != ALFOrder.PENDING:
                continue
            token_id = order.token_id
            if token_id not in self.balance:
                self.balance[token_id] = 0
            currency_id = ID_MAP['USDC'] if order.is_buy else token_id
            amount_in_wallet = self.balance[currency_id] 
            amount_in_order = order.amount_out if order.is_buy else order.amount_out / order.quote_price
            order.tx_fee = 0.0000001
            seconds_delay = max(0, np.random.normal(100, 5))
            order.exec_timestamp = (datetime.fromisoformat(order.market_timestamp) + timedelta(seconds=seconds_delay)).isoformat()
            if amount_in_wallet < amount_in_order:
                order.status = ALFOrder.FAILED
                continue
            elif order.is_buy:
                self.balance[ID_MAP['USDC']] -= order.amount_out
                self.balance[token_id] += order.amount_out / order.quote_price
                order.amount_in = self.balance[token_id]
                order.status = ALFOrder.COMPLETED
            else:
                self.balance[ID_MAP['USDC']] += order.amount_out
                self.balance[token_id] -= order.amount_out / order.quote_price
                order.amount_in = order.amount_out
                order.status = ALFOrder.COMPLETED
            
    def to_dict(self):
        import copy
        return copy.deepcopy(self.balance)


ID_MAP = {
    'SOL': "So11111111111111111111111111111111111111112",
    'PYTH': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
}

INIT_WALLET_STATE = {
    ID_MAP['USDC'] : 1000,
    ID_MAP['SOL'] : 10,
    ID_MAP['PYTH'] : 0,
}

def save_recording(path, out_frames):
    import shutil
    save_dir = Path(path)
    if save_dir.is_dir():
        shutil.rmtree(path)
    save_dir.mkdir() 
    for frame in out_frames:
        ts = frame['timestamp']
        with open(save_dir / f'{ts}.json', 'w') as fp:
            json.dump(frame, fp, indent=4)


def main():
    init_alg_registry()
    market_updates = aggregate_data(START_DATE, END_DATE)
    data_coms = CoinMarketCapComs()
    wallet_coms = RerunWallet(wallet_state=INIT_WALLET_STATE)
    dex_coms = RerunDEX(wallet=wallet_coms)
    data_coms.register_by_sym_dict(ID_MAP)
    order_book = {}
    algs = ALG_REGISTRY['TestAlg']()
    out_frames = []
    for market_frame in market_updates:
        wallet_coms.execute_orders(order_book)
        for quote in market_frame.values():
            if not isinstance(quote, ALFQuote):
                continue
            seconds_delay = max(0, np.random.normal(150, 30))
            quote.quote_timestamp = (datetime.fromisoformat(quote.quote_timestamp) - timedelta(seconds=seconds_delay)).isoformat()
        out_frame, order_book = run_one_frame(dex_coms, wallet_coms, market_frame, order_book, algs)
        for order in out_frame['order_book']:
            if order['status'] == ALFOrder.PENDING:
                order['status'] = ALFOrder.FAILED
        out_frames.append(out_frame)
                
    save_recording('/Users/lucassoffer/Documents/Develop/alafant/dataset/rerun', out_frames)

if __name__ == "__main__":
    main()
