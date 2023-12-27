import requests
import time
from multiprocessing import Process, Queue
import threading
import yaml
import json
from pipeline.core import ALFMarket, MarketFrame
from pipeline.core.alf_alg import ALG_REGISTRY, init_alg_registry
from datetime import datetime
from pathlib import Path

with open('config.json', 'r') as file:
    CONFIG = yaml.safe_load(file)


def fetch_market_data(market_queue, tokens):
    params = "id=" + ",".join([x.cmc_id for x in tokens.values()])
    id_map = {x.cmc_id: x.address for x in tokens.values()}
    while True:
        try:
            start_ts = time.time()
            response = requests.get(f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?{params}', headers=HEADER) 
            market_update = json.loads(response.text)
            # market_update = {id_map[k]: v['quote']['USD'] for k, v in response['data'].items()}
            if market_update['status']['error_code'] != 0: 
                continue
            market_frame = MarketFrame.init_from_cmc(market_update)
            market_queue.put(market_frame)
            # TODO: make this account for get time
            remaining_time = CONFIG["MARKET_UPDATE_RATE"] - (time.time() - start_ts)
            if remaining_time > 0:
                time.sleep(remaining_time)

        except requests.RequestException as e:
            print(f"Request error: {e}")
            # break

def run_one_frame(market, market_frame, alg):
    market.update_order_status()        
    market.update_quotes(market_frame)
    alg_frame = alg.run(market)
    order_frame = market.send_orders()
    return alg_frame, order_frame


def main_loop(alg, market, data_queue, logging_queue):
    while True:
        market_frame = data_queue.get() 
        if not market.is_live():
            print("Skipping market frame, bot is not alive.")
            continue
        alg_frame, order_frame = run_one_frame(market, market_frame, alg)
        logging_queue.put((market_frame, alg_frame, order_frame))

def log_one_frame(save_dir, output_frame):
    market_frame, alg_frame, order_frame = output_frame
    frame_dir = save_dir / market_frame.timestamp 
    frame_dir.mkdir(parents=True)
    frame_path = frame_dir / 'output_frame.json'
    with open(frame_path, 'w') as fp:
        json.dump({
            "market_frame": market_frame.to_dict(),
            "alg_frame": alg_frame.to_dict(),
            "order_frame": order_frame.to_dict(),
        }, fp)


def frame_logger(logging_queue):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = Path(f"/Users/lucassoffer/Documents/Develop/alafant/dataset/live/{timestamp}")
    save_dir.mkdir(parents=True, exist_ok=True)
    while True:
        output_frame = logging_queue.get()





def get_tokens(): 
    response = requests.get("https://token.jup.ag/strict")
    tradeable_assets = json.loads(response.text)

    response = requests.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/map",headers=HEADER)
    cmc_assets = json.loads(response.text)
    cmc_assets = {x['platform']['token_address']: str(x['id']) for x in cmc_assets['data'] if x['platform'] is not None}
    out = {}
    for asset in tradeable_assets:
        if asset['address'] not in cmc_assets:
            continue
        out[asset['address']] = Token(data=asset, cmc_id=cmc_assets[asset['address']])
    return out


if __name__ == '__main__':
    init_alg_registry()
    
    alg = None
    for name, cls_alg in ALG_REGISTRY.items():
        if name == CONFIG["ALG"]:
            alg = cls_alg()
        
    
    market_queue = Queue()
    order_queue = Queue()
    logging_queue = Queue()

    available_tokens = get_tokens()
    market = ALFMarket

    # Create the processes
    alg_loop = Process(target=main_loop, args=(alg, market, market_queue, logging_queue))
    alg_loop.start()

    # Start I/O-bound tasks in threads
    market_fetcher = threading.Thread(target=fetch_market_data, args=(market_queue, available_tokens))
    market_fetcher.start()

    logging_thread = threading.Thread(target=frame_logger, args=(logging_queue))
    logging_thread.start()
    
    # Wait for the processes to finish (in this case, they won't)
    market_fetcher.join()


