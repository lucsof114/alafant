import requests
import json
# from pipeline.core import ALFQuote
HEADER = {
  'Accepts': 'application/json',
  'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
}

class ALFQuote:

    def __init__(self,
                timestamp,
                price,
                volume_24h,
                percent_change_7d,
                market_cap,
                currency):
        self.timestamp = timestamp
        self.price = price
        self.volume_24h = volume_24h
        self.percent_change_7d = percent_change_7d
        self.market_cap = market_cap
        self.currency = currency
    
    @staticmethod
    def init_from_cmc_update(quote_usd, currency):
        return ALFQuote(
            timestamp=quote_usd.get('last_updated', quote_usd['timestamp']),
            price=quote_usd['price'],
            volume_24h=quote_usd['volume_24h'],
            percent_change_7d=quote_usd['percent_change_7d'],
            market_cap=quote_usd['market_cap'],
            currency=currency
        )

    def to_dict(self):
        return {
            "timestamp" :self.timestamp,
            "price" :self.price,
            "volume_24h" :self.volume_24h,
            "percent_change_7d" :self.percent_change_7d,
            "market_cap" :self.market_cap,
            "currency" :self.currency,
        }



class CoinMarketCapComs:

    @staticmethod
    def find_chain_address(x, name):
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
            for token_meta in token_data['data'].values():
                address = CoinMarketCapComs.find_chain_address(token_meta, 'Solana')
                cmc_id =  str(token_meta['id'])
                new_add_to_cmc_map[address] = cmc_id
                new_cmc_to_add_map[cmc_id] = address
                
            self.cmc_to_address = self.cmc_to_address | new_cmc_to_add_map
            self.address_to_cmc = self.address_to_cmc | new_add_to_cmc_map
        
    def register_by_sym_address_pairs(self, token_pairs):
        syms = ','.join([x[0] for x in token_pairs])
        response = requests.get(f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/map?symbol={syms}",headers=HEADER)
        data = json.loads(response.text)['data']
        data_address_to_cmc = {CoinMarketCapComs.find_chain_address(x, 'Solana'): x['id'] for x in data}
        cmc_ids = [data_address_to_cmc[x[1]] for x in token_pairs]
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
        if market_update['status']['error_code'] != 0: 
            return None 
        return self.convert_to_market_frame(market_update['data'])
    
    def convert_to_market_frame(self, market_update):
        out = {}
        for cmc_id, quote in market_update.items():
            quote_usd = quote['quote']['USD']
            out[self.cmc_to_address[cmc_id]] = ALFQuote.init_from_cmc_update(quote_usd, 'USD')
        return out
    
# coms = CMCCommunicator()
# coms.register_by_market_cap(10)
# frame = coms.get_market_frame()
# print("wait")



class ALFToken:
    
    def __init__(self, meta): 
        self.meta = meta
        self.unix_ts = None
        self.quote = None

    @property
    def price(self):
        return self.quote.price if self.quote is not None else None

    @property
    def volume_24h(self):
        return self.quote.volume_24h if self.quote is not None else None
   
    @property
    def volume_change_24h(self):
        return self.quote.volume_change_24h if self.quote is not None else None

    @property
    def market_cap(self):
        return self.quote.market_cap if self.quote is not None else None

    @property
    def market_cap_dominance(self):
        return self.quote.market_cap_dominance if self.quote is not None else None

    @property

    @property
    def timestamp(self):
        return self.quote.last_updated if self.quote is not None else None

    @property
    def address(self):
        return self.meta["address"]
    
    @property
    def name(self):
        return self.meta["name"]
    
    @property
    def symbol(self):
        return self.meta["symbol"]

    @property
    def decimals(self):
        return self.meta["decimals"]
    

# class MarketFrame:

#     def __init__(self, quote, orders)

# SOL_ID = 'So11111111111111111111111111111111111111112'

# response = requests.get(f'https://token.jup.ag/strict')
# market = ExchangeMarket(json.loads(response.text))
# # order = BotOrder.sell(0.1, SOL_ID) 
# order = BotOrder.buy(8, SOL_ID) 
# market.place_orders([order])

# out = requests.get(f"http://localhost:3000/order_status")
# print(out.text)

# tokens = [
#     SOL_ID,
#     CONFIG['BASE_CURRENCY']
# ]
# headers = {
#   'Accepts': 'application/json',
#   'X-CMC_PRO_API_KEY': "d7c58506-119d-4c23-a43c-bcfbb9a864da",
# }

# def get_tokens(): 
#     response = requests.get("https://token.jup.ag/strict")
#     tradeable_assets = json.loads(response.text)

#     response = requests.get("https://pro-api.coinmarketcap.com/v1/cryptocurrency/map",headers=headers)
#     cmc_assets = json.loads(response.text)

#     cmc_assets = {x['platform']['token_address']: str(x['id']) for x in cmc_assets['data'] if x['platform'] is not None}
#     out = []
#     for asset in tradeable_assets:
#         if asset['address'] not in cmc_assets:
#             continue
#         out.append(Token(data=asset, cmc_id=cmc_assets[asset['address']]))
#     return out

# tokens = get_tokens()
# params = "id=" + ",".join([x.cmc_id for x in tokens])

# ids = []
# response = requests.get(f'https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest?{params}', headers=headers) 

# print("Wait")
# headers = {
#     'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
# }


# data = requests.get("https://api.solscan.io/v2/account/token/txs?address=VoFqNa6XLMZxLemnGgGvKVo4tUivr6zowHfDtjQvsUL", headers=headers)
# data = json.loads(data.text)

# print("wait")