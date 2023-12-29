import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QDockWidget, QSlider)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import pyqtgraph as pg
from alftools import AlfantDataframeBuilder
from alftools.util import find_continuous_ranges
from pipeline.core import ALFOrder
from PyQt5.QtGui import QColor

class TimelineEmitter(QObject):
    signal = pyqtSignal(int)


class ALFGraphDock(QWidget):
    def __init__(self, has_combo=False):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.has_combo = has_combo

        self.timeline_item = pg.InfiniteLine(angle=90, pen=pg.mkPen(color='gold', style=Qt.DashLine))
        self.timeaxis = None

        # Combo Box
        if has_combo:
            self.comboBox = QComboBox()
            self.comboBox.currentIndexChanged.connect(self.update_plot)
            self.layout.addWidget(self.comboBox)


        # Matplotlib Plot
        self.graphWidget = pg.PlotWidget()
        self.plot_item = self.graphWidget.plot()
        self.layout.addWidget(self.graphWidget)
        self.timeline_item = pg.InfiniteLine(angle=90, pen=pg.mkPen(color='gold', style=Qt.DashLine))
        self.graphWidget.addItem(self.timeline_item)

    def on_timeline_changed(self, value):
        self.timeline_item.setPos(value)

    def add_timestamps(self, x):
        self.init_time = min(x)
        self.timeaxis = (x - self.init_time).total_seconds() / 3600
    
    def convert_to_timeline(self, x):
        return (x - self.init_time).total_seconds() / 3600

    def update_plot(self):
        pass

class MarketDock(ALFGraphDock):
    def __init__(self):
        super().__init__(has_combo=True)
        self.timestamps = []
        self.order_df = None
        self.market_df = None
        self.plotted_orders = []
        # Add scatter plot
        # Create a ScatterPlotItem for scatter plot
        self.scatter_plot = pg.ScatterPlotItem()
        self.graphWidget.addItem(self.scatter_plot)

    def on_timeline_changed(self, value):
        self.timeline_item.setPos(value)

    def set_recording(self, order_df, market_df):
        self.order_df = order_df
        self.market_df = market_df
        token_ids = market_df['token_id'].unique()
        delta_time = self.market_df['timestamp'].unique() 
        self.add_timestamps(delta_time)
        self.comboBox.addItems(token_ids)
        self.update_plot()
    
    def update_plot(self):
        if self.market_df is None:
            return
        self.scatter_plot.clear()
        token_id = self.comboBox.currentText()
        stock_value = self.market_df.loc[self.market_df['token_id'] == token_id, 'price']
        self.plot_item.setData(self.timeaxis, stock_value.values)
        token_df = self.order_df.loc[(self.order_df['token_id'] == token_id)].reset_index()
        
        orders_gp = token_df[(token_df['status'].shift(1) == ALFOrder.PENDING) & (token_df['status'] == ALFOrder.COMPLETED)].groupby('type')
        for order_type in ["buy", "sell"]:
            if order_type not in orders_gp.groups.keys():
                continue
            orders = orders_gp.get_group(order_type)
            symbol = 't1' if order_type == "buy" else 't'
            brush = pg.mkBrush(color='g') if order_type == "buy" else pg.mkBrush(color='r')
            orders['timeaxis'] = orders['timestamp'].apply(lambda x: self.convert_to_timeline(x))
            self.scatter_plot.addPoints(orders['timeaxis'], orders['price'], symbol=symbol, brush=brush)

        for start_idx, end_idx in find_continuous_ranges(token_df['status'], where= lambda x: x.loc[x == ALFOrder.PENDING]):
            start_ts = self.convert_to_timeline(token_df.iloc[start_idx]['timestamp'])
            end_idx = min(end_idx + 1, token_df.shape[0])
            end_ts = self.convert_to_timeline(token_df.iloc[end_idx]['timestamp'])
            
            color = QColor(255, 0 , 0) if token_df.iloc[start_idx]['type'] == "sell" else QColor(0, 255, 0)
            color.setAlphaF(0.3)
            brush = pg.mkBrush(color)

            highlight_item = pg.LinearRegionItem(values=[start_ts, end_ts], brush=brush, movable=False)
            self.graphWidget.addItem(highlight_item)


class AlgDock(ALFGraphDock):

    def __init__(self):
        super().__init__(has_combo=True)
        self.alg_df = None

    def set_recording(self, alg_df):
        self.alg_df = alg_df
        self.timestamps = self.add_timestamps(self.alg_df.index)
        self.comboBox.addItems(list(self.alg_df.columns))
        self.update_plot()
    
    def on_timeline_changed(self, value):
        self.timeline_item.setPos(value)

    def update_plot(self):
        if self.alg_df is None:
            return
        extraction = self.comboBox.currentText()
        self.plot_item.setData(self.timeaxis, self.alg_df[extraction])

class WalletDock(ALFGraphDock):
    def __init__(self):
        super().__init__()
        self.market_df = None
        self.order_df = None
        self.timeline_emitter = TimelineEmitter()

        self.timeline = QSlider(Qt.Horizontal)
        self.layout.addWidget(self.timeline)
        self.timeline.valueChanged.connect(self.on_timeline_changed)

        # Buttons
        self.addMarketDock = QPushButton("Add Market Dock")
        self.addAlgDock = QPushButton("Add Alg Dock")

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.addMarketDock)
        buttonLayout.addWidget(self.addAlgDock)
        self.layout.addLayout(buttonLayout)
    
    def on_timeline_changed(self, value):
        self.timeline_item.setPos(value)
        self.timeline_emitter.signal.emit(value)

    def set_recording(self, order_df, market_df):
        self.market_df = market_df
        self.order_df = order_df
        total_balance = self.market_df.groupby("timestamp")['wallet_balance_usd'].agg('sum')
        self.add_timestamps(self.market_df['timestamp'].unique())
        self.timeline.setMaximum(int(max(self.timeaxis)) + 1)
        self.graphWidget.plot(self.timeaxis, total_balance)

class Alpaca(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Alpaca")

        self.walletDock = QDockWidget("Wallet View", self)
        self.walletDock.setWidget(WalletDock())
        self.addDockWidget(Qt.BottomDockWidgetArea, self.walletDock)

        self.market_docks = []
        self.alg_docks = []
        alg_dock = self.add_alg_dock()
        market_dock = self.add_market_dock()
        self.addDockWidget(Qt.LeftDockWidgetArea, alg_dock)
        self.addDockWidget(Qt.RightDockWidgetArea, market_dock)
        

    def set_recording(self, path_to_recording):
        order_df, algs_df, market_df = AlfantDataframeBuilder.to_dataframe(path_to_recording)
        for dock in self.market_docks:
            dock.widget().set_recording(order_df, market_df)
            
        for dock in self.alg_docks:
            dock.widget().set_recording(algs_df)
        
        self.walletDock.widget().set_recording(order_df, market_df)

    def add_market_dock(self):
        market_dock = QDockWidget("Market View", self)
        market_view = MarketDock()
        self.walletDock.widget().timeline_emitter.signal.connect(market_view.on_timeline_changed)
        market_dock.setWidget(market_view)
        self.market_docks.append(market_dock)
        return market_dock

    def add_alg_dock(self):
        alg_dock = QDockWidget("Algorithm View", self)
        alg_view = AlgDock()
        self.walletDock.widget().timeline_emitter.signal.connect(alg_view.on_timeline_changed)
        alg_dock.setWidget(alg_view)
        self.alg_docks.append(alg_dock)
        return alg_dock

def main():
    app = QApplication(sys.argv)
    mainWindow = Alpaca()
    mainWindow.show()
    path = '/Users/lucassoffer/Documents/Develop/alafant/dataset/rerun'
    mainWindow.set_recording(path)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
 