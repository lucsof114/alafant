import requests
import json
# from pipeline.core import ALFQuote
HEADER = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
}

class ALFQuote:

    def __init__(self,
                token_id,
                timestamp,
                price,
                volume_24h,
                percent_change_7d,
                market_cap,
                currency):
        self.token_id = token_id
        self.quote_timestamp = timestamp
        self.price = price
        self.volume_24h = volume_24h
        self.percent_change_7d = percent_change_7d
        self.market_cap = market_cap
        self.currency = currency
    
    @staticmethod
    def init_from_cmc_update(token_id, quote_usd, currency):
        return ALFQuote(
            token_id=token_id,
            timestamp=quote_usd.get('last_updated') if 'last_updated' in quote_usd else quote_usd['timestamp'],
            price=quote_usd['price'],
            volume_24h=quote_usd['volume_24h'],
            percent_change_7d=quote_usd['percent_change_7d'],
            market_cap=quote_usd['market_cap'],
            currency=currency
        )

    def to_dict(self):
        return {
                "token_id": self.token_id,
                "quote_timestamp": self.quote_timestamp,
                "price": self.price,
                "volume_24h": self.volume_24h,
                "percent_change_7d": self.percent_change_7d,
                "market_cap": self.market_cap,
                "currency": self.currency,
        }



class CoinMarketCapComs:

    @staticmethod
    def find_chain_address(x, name):
        if x['name'] == 'USDC':
            return 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'
        if x.get('platform') and x['platform']['name'] == name:
            return x['platform']['token_address']
        if x.get('contract_address') is None:
            return None
        for address in x['contract_address']:
            if address['platform']['name'] == name:
                return address['contract_address']
        return None

    def __init__(self):
        self.cmc_to_address = {}
        self.address_to_cmc = {}
        self.add_to_description = {}

    @property
    def cmc_ids(self):
        return [x for x in self.cmc_to_address.keys()]

    @property
    def token_ids(self):
        return [x for x in self.cmc_to_address.values()]
    
    def register_by_cmc_id(self, cmc_ids):
        new_cmcs = []
        for cmc_id in cmc_ids:
            if cmc_id not in self.cmc_to_address:
                new_cmcs.append(str(cmc_id))
        if len(new_cmcs) != 0:
            cmc_params = ','.join(new_cmcs)
            response = requests.get(f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/info?id={cmc_params}",headers=HEADER)
            token_data = json.loads(response.text)
            if token_data['status']['error_code'] != 0:
                print("unable to register new_cmcs")
                return
            new_add_to_cmc_map = {}
            new_cmc_to_add_map = {}
            new_add_to_description = {}
            for token_meta in token_data['data'].values():
                address = CoinMarketCapComs.find_chain_address(token_meta, 'Solana')
                cmc_id =  str(token_meta['id'])
                new_add_to_cmc_map[address] = cmc_id
                new_cmc_to_add_map[cmc_id] = address
                new_add_to_description[address] = token_meta
            
            self.add_to_description = self.add_to_description | new_add_to_description
            self.cmc_to_address = self.cmc_to_address | new_cmc_to_add_map
            self.address_to_cmc = self.address_to_cmc | new_add_to_cmc_map
    
    def get_token_meta(self, address):
        return self.add_to_description[address]

    def register_by_sym_dict(self, sym_dict):
        syms = ','.join([x for x in sym_dict.keys()])
        response = requests.get(f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/map?symbol={syms}",headers=HEADER)
        data = json.loads(response.text)['data']
        data_address_to_cmc = {CoinMarketCapComs.find_chain_address(x, 'Solana'): x['id'] for x in data}
        cmc_ids = [data_address_to_cmc[x] for x in sym_dict.values()]
        self.register_by_cmc_id(cmc_ids=cmc_ids)


    def register_by_market_cap(self, num_tokens):
        response = requests.get(f"https://api.coinmarketcap.com/data-api/v3/cryptocurrency/listing?start=1&limit={num_tokens}&sortBy=market_cap&sortType=desc&convert=USD,BTC,ETH&cryptoType=all&tagType=all&audited=false&aux=ath,atl,high24h,low24h,num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,self_reported_circulating_supply,self_reported_market_cap,total_supply,volume_7d,volume_30d&tagSlugs=solana-ecosystem")
        response = json.loads(response.text)['data']['cryptoCurrencyList']
        cmc_ids = [x['id'] for x in response]
        self.register_by_cmc_id(cmc_ids)

    def get_market_frame(self):
        params = "id=" + ",".join([x for x in self.cmc_to_address.keys()])
        response = requests.get(f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?{params}', headers=HEADER) 
        market_update = json.loads(response.text)
        ts = market_update['status']['timestamp']
        if market_update['status']['error_code'] != 0: 
            return None 
        return self.convert_to_market_frame(market_update, ts)
    
    def convert_to_market_frame(self, market_update, ts):
        out = {"timestamp" : ts}
        for cmc_id, quote in market_update['data'].items():
            quote_usd = quote['quote']['USD']
            address = self.cmc_to_address[cmc_id]
            out[self.cmc_to_address[cmc_id]] = ALFQuote.init_from_cmc_update(address, quote_usd, 'USD')
        return out
    