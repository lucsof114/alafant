import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
HEADER = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
}

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

tokens = get_tokens()
sym_to_token = {x.symbol: x for x in tokens.values()}
tokens_for_data= [sym_to_token['SOL'], sym_to_token['PYTH']]
params = ",".join([x.cmc_id for x in tokens_for_data])

# with open(f'/Users/lucassoffer/Documents/Develop/alafant/dataset/test.json') as file:
#     data = json.load(file.buffer)


def process_get_request(data):
    for token in tokens_for_data:
        for quote in data['data'][token.cmc_id]['quotes']:
            for currency, update in quote['quote'].items():
                save_path = Path(f"/Users/lucassoffer/Documents/Develop/alafant/dataset/historical/{quote['timestamp']}/{token.address}/{currency}/")
                save_path.mkdir(parents=True, exist_ok=True)
                with (save_path / "market_data.json").open('w') as file:
                    update["currency"] = currency
                    update["token"] = token.address
                    update["name"] = token.name
                    json.dump(update, file, ensure_ascii=False, indent=4)


for i in range(0, 3):
    delta_t = timedelta(days=10)
    time_end = (datetime.now() - timedelta(days=10*i)).isoformat()
    time_start = (datetime.now() - timedelta(days=10* (i + 1))).isoformat()
    new_data = requests.get(f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical?time_start={time_start}&time_end={time_end}&id={params}", headers=HEADER)
    new_data = json.loads(new_data.text)
    process_get_request(new_data)


# print("wait")