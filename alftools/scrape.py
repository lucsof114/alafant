import requests
import pandas as pd
import matplotlib.pyplot as plt
import json

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    # Add other headers as necessary
}
data = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/PYTH-USD?region=US&lang=en-US&includePrePost=false&interval=5m&useYfid=true&range=60d&corsDomain=finance.yahoo.com&.tsrc=finance", headers=headers)

data = json.loads(data.text)
plt.plot(data['chart']['result'][0]['indicators']['quote'][0]['open'])