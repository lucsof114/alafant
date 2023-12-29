import pandas as pd
import json
from pathlib import Path
from datetime import datetime

class AlfantDataframeBuilder: 

    def __init__(self):
        self.market_cache = []
        self.order_cache = []
        self.algs_cache = []

    def create_order_df(json_data):
        pass

    
    def update_market_df(self, market_frame, wallet_frame):
        for quote in market_frame:
            quote["wallet_balance"] = wallet_frame[quote['token_id']]
            quote["wallet_balance_usd"] = wallet_frame[quote['token_id']] * quote['price']
            quote['timestamp'] = datetime.fromisoformat(quote['timestamp'])
            self.market_cache.append(quote)

    def update_order_df(self, ts, order_book):
        for order in order_book:
            self.order_cache.append({
                **order,
                "timestamp": datetime.fromisoformat(ts)
            })


    def update_alg_df(self, ts, alg_frame):
        self.algs_cache.append({
            **alg_frame,
            "timestamp": datetime.fromisoformat(ts)
        })



    @staticmethod
    def to_dataframe(path_to_recording):
        
        df_builder = AlfantDataframeBuilder()
        for frame_path in Path(path_to_recording).iterdir():
            with open(frame_path, 'r') as fp:
                frame = json.load(fp)
            alg_frame, order_book, market_frame, wallet_frame = frame["alg_frame"], frame["order_book"], \
                                                                frame['market_frame'], frame['wallet_frame']
            ts = market_frame[0]['timestamp']
            df_builder.update_market_df(market_frame, wallet_frame)
            df_builder.update_order_df(ts, order_book)
            df_builder.update_alg_df(ts, alg_frame)

        return pd.DataFrame(df_builder.order_cache).sort_values(by='timestamp'),\
              pd.DataFrame(df_builder.algs_cache).set_index('timestamp').sort_index(),\
             pd.DataFrame(df_builder.market_cache).sort_values(by='timestamp')


order_df, algs_df, market_df = AlfantDataframeBuilder.to_dataframe('/Users/lucassoffer/Documents/Develop/alafant/dataset/rerun')
print("wait")