import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QDockWidget, QSlider)
from PyQt5.QtCore import Qt, pyqtSignal, QObject
import pyqtgraph as pg
from alftools import AlfantDataframeBuilder
from alftools.util import find_continuous_ranges
from pipeline.core import ALFOrder
from PyQt5.QtGui import QColor
import pandas as pd

class TimelineEmitter(QObject):
    signal = pyqtSignal(int)


class ALFGraphDock(QWidget):
    def __init__(self, has_combo=False):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.has_combo = has_combo
        self.clear_cache = []

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
    
    def add_item(self, x):
        self.graphWidget.addItem(x)
        self.clear_cache.append(x)
            
    def clear(self):
        self.plot_item.clear()
        for x in self.clear_cache:
            self.graphWidget.removeItem(x)
        self.clear_cache = []

    def on_timeline_changed(self, value):
        self.timeline_item.setPos(value)

    def add_timestamps(self, x):
        self.init_time = min(x)
        self.timeaxis = x.apply(self.convert_to_timeline)
    
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

    def clear(self):
        super().clear()
        self.scatter_plot.clear()

    def on_timeline_changed(self, value):
        self.timeline_item.setPos(value)

    def set_recording(self, order_df, market_df):
        self.order_df = order_df
        self.market_df = market_df
        token_ids = market_df['token_id'].unique()
        self.comboBox.addItems(token_ids)
        self.update_plot()
    
    def update_plot(self):
        if self.market_df is None:
            return
        self.clear()
        token_id = self.comboBox.currentText()
        stock_df = self.market_df.loc[self.market_df['token_id'] == token_id]
        self.add_timestamps(stock_df['quote_timestamp'])
        self.plot_item.setData(self.timeaxis.values, stock_df['price'].values)

        if self.order_df.empty:
            return

        token_df = self.order_df.loc[(self.order_df['token_id'] == token_id)]
        if token_df.empty:
            return
        order_gp = self.order_df.groupby('order_id')
        for order_id in order_gp.groups.keys():
            order_df = order_gp.get_group(order_id)
            complete_order = order_df.loc[order_df['status'] == ALFOrder.COMPLETED]
            buy_order = order_df.iloc[0]['type'] == 'buy'
            if complete_order.empty:
                incomplete_order = order_df.loc[order_df['status'].isin([ALFOrder.PENDING, ALFOrder.FAILED])]
                if incomplete_order.empty:
                    print("probably not good")
                incomplete_order = incomplete_order.iloc[0]
                ts = self.convert_to_timeline(incomplete_order['market_timestamp'])
                scatter_item = pg.ScatterPlotItem([ts], [incomplete_order['quote_price']], symbol='x', brush=pg.mkBrush('r'), size=15)
                self.add_item(scatter_item)
            else:
                complete_order = complete_order.iloc[0]
                ts = self.convert_to_timeline(complete_order['market_timestamp'])
                tf = self.convert_to_timeline(complete_order['exec_timestamp'])
                tq = self.convert_to_timeline(complete_order['quote_timestamp'])
                
                scatter_brush = pg.mkBrush(color='g') if buy_order else pg.mkBrush(color='r')
                scatter_symbol = 't1' if buy_order else 't'
                scatter_item = pg.ScatterPlotItem([tf], [complete_order['quote_price']], symbol=scatter_symbol, brush=scatter_brush, size=15)
                self.add_item(scatter_item)

                order_line = pg.PlotDataItem([tq, tf], [complete_order['quote_price'], complete_order['quote_price']], pen=pg.mkPen(color='b', width=5, style=Qt.DashLine))
                self.add_item(order_line)
                self.scatter_plot.addPoints([tq], [complete_order['quote_price']], symbol='s', size=10, symbolBrush=pg.mkBrush(color='b'))

                color = QColor(0, 255 , 0) if buy_order else QColor(255, 255, 0)
                color.setAlphaF(0.2)
                brush = pg.mkBrush(color)
                highlight_item = pg.LinearRegionItem(values=[ts, tf], brush=brush, movable=False)
                self.add_item(highlight_item)

                
            


class AlgDock(ALFGraphDock):

    def __init__(self):
        super().__init__(has_combo=True)
        self.alg_df = None

    def set_recording(self, alg_df):
        self.alg_df = alg_df
        self.timestamps = self.add_timestamps(self.alg_df.index.to_series())
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
        total_balance = self.market_df.groupby("market_timestamp")['wallet_balance_usd'].agg('sum').sort_index()
        self.add_timestamps(pd.Series(self.market_df['market_timestamp'].unique()).sort_values())
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
    # path = '/Users/lucassoffer/Documents/Develop/alafant/dataset/rerun'
    path = '/Users/lucassoffer/Documents/Develop/alafant/dataset/live/2023-12-31T17:46:45.425358'
    mainWindow.set_recording(path)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
 