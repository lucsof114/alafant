# import asyncio
# import websockets
# import json 
# import sys 
# sys.path.append("/Users/lucassoffer/Documents/Develop/alafant/models")
import requests
import time
from multiprocessing import Process, Queue
import threading
import yaml
import json
from pipeline.util.asset_token import ExchangeMarket, Token
from models.template import ALG_REGISTRY, init_alg_registry

with open('config.json', 'r') as file:
    CONFIG = yaml.safe_load(file)

HEADER = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
}

def fetch_market_data(market_queue, tokens):
    params = "id=" + ",".join([x.cmc_id for x in tokens.values()])
    id_map = {x.cmc_id: x.address for x in tokens.values()}
    while True:
        try:
            start_ts = time.time()
            response = requests.get(f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?{params}', headers=HEADER) 
            response = json.loads(response.text)
            if response['status']['error_code'] != 0: 
                continue
            market_update = {id_map[k]: v['quote']['USD'] for k, v in response['data'].items()}
            market_queue.put(market_update)
            # TODO: make this account for get time
            remaining_time = CONFIG["MARKET_UPDATE_RATE"] - (time.time() - start_ts)
            if remaining_time > 0:
                time.sleep(remaining_time)

        except requests.RequestException as e:
            print(f"Request error: {e}")
            # break


def main_loop(alg, market, data_queue):
    while True:
        if not market.is_live():
            time.sleep(1)
            continue
        while not data_queue.empty():
            market.update_pending_orders()        
            print("RUNNING ALGS")
            market_data = data_queue.get() 
            market.update_quotes(market_data)
            alg.run(market)
        market.place_orders()


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

    available_tokens = get_tokens()
    market = ExchangeMarket(available_tokens)

    # Create the processes
    alg_loop = Process(target=main_loop, args=(alg, market, market_queue))
    alg_loop.start()

    # Start I/O-bound tasks in threads
    market_fetcher = threading.Thread(target=fetch_market_data, args=(market_queue, available_tokens))
    market_fetcher.start()
    
    # Wait for the processes to finish (in this case, they won't)
    market_fetcher.join()


