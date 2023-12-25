import requests
import json
from datetime import datetime, timedelta
from pipeline.util.asset_token import Token
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
# delta_t = timedelta(days=10)
# time_end = datetime.now().isoformat()
# time_start = (datetime.now() - delta_t).isoformat()

# data = requests.get(f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical?time_start={time_start}&time_end={time_end}&id={params}", headers=HEADER)
# data = json.loads(data.text)

out = {t.symbol: [] for t in tokens_for_data}
with open(f'/Users/lucassoffer/Documents/Develop/alafant/alpaca/dataset/d1.json') as file:
    data = json.load(file.buffer)

for i in range(1, 3):
    delta_t = timedelta(days=10)
    time_end = (datetime.now() - timedelta(days=10*i)).isoformat()
    time_start = (datetime.now() - timedelta(days=10* (i + 1))).isoformat()
    new_data = requests.get(f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical?time_start={time_start}&time_end={time_end}&id={params}", headers=HEADER)
    new_data = json.loads(new_data.text)
    for token in tokens_for_data:
        data['data'][token.cmc_id]['quotes'] += new_data['data'][token.cmc_id]['quotes']

for token in tokens_for_data:
    with open(f'/Users/lucassoffer/Documents/Develop/alafant/alpaca/dataset/{token.cmc_id}-{time_start}-{time_end}.json', 'w') as file:
        json.dump(data['data'][token.cmc_id], file, indent=4)



print("wait")