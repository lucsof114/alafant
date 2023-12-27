from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
from pipeline.core import CoinMarketCapComs, ALFOrder, ALFQuote
from pipeline.models import SmartDCA

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
                    market_frame[id_dir.name] = ALFQuote.init_from_cmc_update(data, 'USD')
            out.append(market_frame)
    return out

ID_MAP = {
    'SOL': "So11111111111111111111111111111111111111112",
    'PYTH': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3'
}

def main():
    market_updates = aggregate_data(START_DATE, END_DATE)
    data_coms = CoinMarketCapComs()
    # dex_coms = DEXJupiterComs()
    # wallet_coms = WalletComs()
    sym_address_pairs = [(x, ID_MAP[x]) for x in ['SOL', 'PYTH']]
    data_coms.register_by_sym_address_pairs(sym_address_pairs)
    order_book = {}
    algs = SmartDCA()
    for market_frame in market_updates:
        # tx_ids = dex_coms.get(tx_ids, [o for o in order_book if o.status == ALFOrder.PENDING])
        # wallet_coms.update(order_book)
        algs.run(market_frame, order_book)
        new_orders = algs.get_orders()
        if len(new_orders) != 0:
            print(new_orders)
        # dex_coms.execute_orders(new_orders)
        order_book = order_book | new_orders



if __name__ == "__main__":
    main()
