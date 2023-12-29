import requests
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from pipeline.core import CoinMarketCapComs
import pandas as pd 
from alftools.util import find_continuous_ranges


HEADER = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
}

ID_MAP = {
    'SOL': "So11111111111111111111111111111111111111112",
    'PYTH': 'HZ1JovNiVvGrGNiiYvEozEVgZ58xaU3RKwX8eACQBCt3',
    'USDC': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
}

INTERVAL = '5T'
START_DATE = pd.Timestamp(datetime.now(timezone.utc) - timedelta(days=30)).round(INTERVAL)
END_DATE = pd.Timestamp.now(timezone.utc).round(INTERVAL)
DATA_PATH = Path(f"/Users/lucassoffer/Documents/Develop/alafant/dataset/historical")
coms = CoinMarketCapComs()
coms.register_by_sym_dict(ID_MAP)
params = ",".join([x for x in coms.cmc_to_address.keys()])

# with open(f'/Users/lucassoffer/Documents/Develop/alafant/dataset/test.json') as file:
#     data = json.load(file.buffer)


def process_get_request(data):
    address = coms.cmc_to_address[str(data['data']['id'])]
    for quote in data['data']['quotes']:
        for currency, update in quote['quote'].items():
            save_path = DATA_PATH / f"{quote['timestamp']}/{address}/{currency}/"
            save_path.mkdir(parents=True, exist_ok=True)
            with (save_path / "market_data.json").open('w') as file:
                update["currency"] = currency
                update["token"] = address
                update["name"] = coms.get_token_meta(address)['name']
                json.dump(update, file, ensure_ascii=False, indent=4)

ts = START_DATE
while ts < END_DATE:
    te = min(ts + timedelta(days=10), END_DATE)
    for address in ID_MAP.values():
        requested_ts = pd.date_range(start=ts, end=te, freq=INTERVAL, tz='UTC').to_series()
        timestamps = []
        for dir_ts in DATA_PATH.iterdir():
            if address not in [x.name for x in dir_ts.iterdir()]:
                continue
            timestamps.append(pd.Timestamp.fromisoformat(dir_ts.name).tz_localize(timezone.utc))
        if len(timestamps) == len(requested_ts):
            continue
        timestamps = pd.Series(timestamps).sort_values()
        for start_idx, end_idx in find_continuous_ranges(requested_ts, where=lambda x: x.loc[x.isin(timestamps) == False]):
            time_start, time_end = requested_ts.iloc[start_idx], requested_ts.iloc[end_idx]
            cmc_id = coms.address_to_cmc[address] 
            if time_start == time_end:
                time_start -= timedelta(minutes=5)
                time_end += timedelta(minutes=5)
            time_start, time_end = time_start.isoformat().replace('+00:00', 'Z'), time_end.isoformat().replace('+00:00', 'Z')
                # new_data = requests.get(f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical?time_start={time_start}&id={cmc_id}", headers=HEADER)
            new_data = requests.get(f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical?time_start={time_start}&time_end={time_end}&id={cmc_id}", headers=HEADER)
            new_data = json.loads(new_data.text)
            process_get_request(new_data)
    ts = te
