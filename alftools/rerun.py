from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from pipeline.core import CoinMarketCapComs, ALFOrder, ALFQuote
from pipeline.models import SmartDCA
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
            market_frame = {}
            for id_dir in date_dir.iterdir():
                json_path = id_dir / 'USD' / 'market_data.json'
                with open(json_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
                    market_frame[id_dir.name] = ALFQuote.init_from_cmc_update(id_dir.name, data, 'USD')
            out.append((date_dir.name, market_frame))
    sorted_frames = sorted(out, key=lambda x: datetime.fromisoformat(x[0]))
    return [x[1] for x in sorted_frames]

class RerunDEX:

    def __init__(self, latency=0):
        self.latency = latency
        self.order_id_to_tx_id = {}

    def execute_orders(self, orders):
        for order in orders.values():
            order.status = ALFOrder.PENDING
            self.order_id_to_tx_id[order.id] = str(uuid.uuid4())

    def get_tx_ids(self, orders):
        out = []
        for order in orders:
            tx_id = self.order_id_to_tx_id[order.id]
            order.tx_id = tx_id
            out.append(tx_id)
        return out 

class RerunWallet:
    def __init__(self, wallet_state):
        self.wallet = wallet_state

    def update_order_book(self, tx_ids, order_book):
        for order in order_book.values():
            if order.status != ALFOrder.PENDING:
                continue
            token_id = order.token_id
            if token_id not in self.wallet:
                self.wallet[token_id] = 0
            currency_id = ID_MAP['USDC'] if order.is_buy else token_id
            amount_in_wallet = self.wallet[currency_id]
            if amount_in_wallet < order.amount:
                order.status = ALFOrder.FAILED
            elif order.is_buy:
                self.wallet[ID_MAP['USDC']] -= order.amount
                self.wallet[token_id] += order.amount / order.price
                order.status = ALFOrder.COMPLETED
            else:
                self.wallet[ID_MAP['USDC']] += order.amount
                self.wallet[token_id] -= order.amount / order.price
                order.status = ALFOrder.COMPLETED
            
    def to_dict(self):
        import copy
        return copy.deepcopy(self.wallet)


ID_MAP = {
    'SOL': "So11111111111111111111111111111111111111112",
    'PYTH': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
}

INIT_WALLET_STATE = {
    ID_MAP['USDC'] : 1000,
    ID_MAP['SOL'] : 0,
    ID_MAP['PYTH'] : 0,
}

def save_recording(path, out_frames):
    import shutil
    save_dir = Path(path)
    if save_dir.is_dir():
        shutil.rmtree(path)
    save_dir.mkdir() 
    for frame in out_frames:
        ts = frame['market_frame'][0]['timestamp']
        with open(save_dir / f'{ts}.json', 'w') as fp:
            json.dump(frame, fp, indent=4)


def main():
    market_updates = aggregate_data(START_DATE, END_DATE)
    data_coms = CoinMarketCapComs()
    dex_coms = RerunDEX()
    wallet_coms = RerunWallet(wallet_state=INIT_WALLET_STATE)
    data_coms.register_by_sym_dict(ID_MAP)
    order_book = {}
    algs = SmartDCA()
    out_frames = []
    for market_frame in market_updates:
        tx_ids = dex_coms.get_tx_ids([o for o in order_book.values() if o.status == ALFOrder.PENDING])
        wallet_coms.update_order_book(tx_ids, order_book)
        algs.run(market_frame, order_book)
        new_orders = algs.get_orders()
        if len(new_orders) != 0:
            print(new_orders)
        dex_coms.execute_orders(new_orders)
        order_book = order_book | new_orders
        out_frames.append({
            "alg_frame": algs.get_alg_frame(),
            "order_book": [v.to_dict() for v in order_book.values()],
            "market_frame": [v.to_dict() for v in market_frame.values()],
            "wallet_frame": wallet_coms.to_dict(),
        })

    save_recording('/Users/lucassoffer/Documents/Develop/alafant/dataset/rerun', out_frames)

if __name__ == "__main__":
    main()
