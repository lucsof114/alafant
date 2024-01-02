import requests
import time
from multiprocessing import Process, Queue
import threading
import yaml
import json
from pipeline.core import CoinMarketCapComs, JupiterDEX, ALFWallet, ALFQuote, ALG_REGISTRY, init_alg_registry, ALFOrder
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(format='[%(levelname)s]:(alafant:%(filename)s:linenum:%(lineno)d) %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

with open('config.json', 'r') as file:
    CONFIG = yaml.safe_load(file)

    # response = requests.get("https://token.jup.ag/strict")

def fetch_market_data(market_queue, data_coms):
    while True:
        try:
            start_ts = time.time()
            market_frame = data_coms.get_market_frame()
            market_queue.put(market_frame)

            remaining_time = CONFIG["MARKET_UPDATE_RATE"] - (time.time() - start_ts)
            if remaining_time > 0:
                time.sleep(remaining_time)

        except requests.RequestException as e:
            print(f"Request error: {e}")

def run_one_frame(dex, wallet, market_frame, order_book, algs):
    update_wallet = dex.update_orders(order_book)
    if update_wallet:
        wallet.update_wallet()
    algs.run(market_frame, order_book)
    new_orders = algs.get_orders()
    for order in new_orders.values():
        order.market_timestamp = market_frame['timestamp']
    dex.execute_orders(new_orders)
    order_book = order_book | new_orders
    output_frame = {
            "alg_frame": algs.get_alg_frame(),
            "order_book": [v.to_dict() for v in order_book.values()],
            "market_frame": [v.to_dict() for v in market_frame.values() if isinstance(v, ALFQuote)],
            "wallet_frame": wallet.to_dict(),
            "timestamp": market_frame['timestamp']
        }
    logger.info(f"Timestamp: {market_frame['timestamp']}")
    for order in new_orders.values(): 
        order_type = "BUY" if order.is_buy else "SELL"
        if order.is_buy:
            logger.info(f"[NEW ORDER] -- BUY {order.token_id} : {order.amount_out} USDC @ {order.quote_price} USD per token")
        else:
            logger.info(f"[NEW ORDER] -- SELL {order.amount_out} USDC of {order.token_id} @ {order.quote_price} USD per token")

    return output_frame, order_book

def main_loop(dex, wallet, algs, data_queue, logging_queue):
    order_book = {}
    while True:
        market_frame = data_queue.get() 
        if not dex.is_live():
            print("Skipping market frame, bot is not alive.")
            continue
        output_frame, order_book = run_one_frame(dex, wallet, market_frame, order_book, algs)
        logging_queue.put(output_frame)

def frame_logger(logging_queue):
    session_id = datetime.now().isoformat()
    save_dir = Path(f"/Users/lucassoffer/Documents/Develop/alafant/dataset/live/{session_id}")
    save_dir.mkdir(parents=True, exist_ok=True)
    while True:
        output_frame = logging_queue.get()
        ts = output_frame['timestamp']
        with open(save_dir / f'{ts}.json', 'w') as fp:
            json.dump(output_frame, fp, indent=4)

def main():
    init_alg_registry()
    
    algs = None
    for name, cls_alg in ALG_REGISTRY.items():
        if name == CONFIG["ALG"]:
            algs = cls_alg()
    if algs is None:
        print("No algs")
        return 
    
    data_coms = CoinMarketCapComs()

    ID_MAP = {
        'SOL': "So11111111111111111111111111111111111111112",
        'PYTH': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
        'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
    }

    data_coms.register_by_sym_dict(ID_MAP)
    
    jup_dex = JupiterDEX()
    wallet = ALFWallet(data_coms.token_ids)

    data_queue = Queue()
    logging_queue = Queue()

    alg_loop = Process(target=main_loop, args=(jup_dex, wallet, algs, data_queue, logging_queue))
    alg_loop.start()

    data_fetcher = threading.Thread(target=fetch_market_data, args=(data_queue, data_coms))
    data_fetcher.start()

    logging_thread = threading.Thread(target=frame_logger, args=(logging_queue,))
    logging_thread.start()
    
    data_fetcher.join()


if __name__ == '__main__':
    main()

