"""
                Trading algorithm architecture
                ------------------------------

                                      +----------+
                                      |          +<---Network
                                      |Broker API|
                      Live            |          +<--+
                                      +----+-----+   |
                                           |         |
                                    +------+-------+ |
  +----fire-EveryBarData-event------+LiveDataLoader| |
  |                                 +------+-------+ |
  |                                        |         |
  | +------------------+ +---------+ +-----+------+  |
  | |MarketEventManager| |Algorithm| |FactorEngine|  |
  | +---------+--------+ +----+----+ +-----+------+  |
  |           |               |            |         |
  |      +----+-----+   +-----+-----+    +-+-+       |
  +----->+fire_event+-->+_run_engine+--->+run+---+   |
         +----+-----+   +-----+----++    +---+   |   |
              |               |    ^             |   |
              |               |    +--save-data--+   |
              |               |                      |
 time    +----+-----+    +----+----+    --------+    |
trigger->+fire close+--->+rebalance+--->+Blotter+----+
         +----------+    +---------+    +-------+


                                      +-------------+
                      Back-test       |CsvDataLoader|
                                      +-----+-------+
                                            |
 +----------------------+ +---------+ +-----+------+
 |SimulationEventManager| |Algorithm| |FactorEngine|
 +------------+---------+ +----+----+ +-----+------+
              |                |            |
       +------+------+    +----+-----+    +-+-+
       |loop data row+--->+run_engine+--->+run+---+
       +------+---+--+    ++---+----++    +---+   |
              |   ^        |   |    ^             |
              |   +-return-+        +---return----+
              |                |
              |           +----+----+   +-----------------+
              +---------->+rebalance+-->+SimulationBlotter|
                          +---------+   +-----------------+


                Pseudo-code for back-test and live
                ----------------------------------

class MyAlg(trading.CustomAlgorithm):
    def initialize(self):
        engine = self.get_factor_engine()
        factor = ....
        factor_engine.add(factor, 'your_factor')

        # 10000 ns before market close
        self.schedule_rebalance(trading.event.MarketClose(self.rebalance, -10000))

        self.blotter.set_commission()  # only works on back-test
        self.blotter.set_slippage()  # only works on back-test

    def rebalance(self, data, history):
        weight = data.your_factor / data.your_factor.sum()
        self.order_to_percent(data.index, weight)

        record(...)

    def terminate(self):
        plot()

# Back-test
-----------------
loader = spectre.factors.CsvDirLoader(...)
blotter = spectre.trading.SimulationBlotter(loader)
evt_mgr = spectre.trading.SimulationEventManager()
alg = MyAlg(blotter, man=loader)
evt_mgr.subscribe(alg)
evt_mgr.subscribe(blotter)
evt_mgr.run('2018-01-01', '2019-01-01')

## Or the helper function:
spectre.run_backtest(loader, MyAlg, '2018-01-01', '2019-01-01')

# Live
----------------
class YourBrokerAPI:
    class LiveDataLoader(EventReceiver, DataLoader):
        def on_run():
            self.schedule(event.Always(read_data))
        def read_data(self):
            api.asio.read()
            agg_data(_cache)
            _cache.resample(self.rule)
            if new_bar:
                self.fire_event(event.EveryBarData)
        def load(...):
            return self._cache[xx:xx]
    ...

broker_api = YourBrokerAPI()
loader = broker_api.LiveDataLoader(rule='5mins')
blotter = broker_api.LiveBlotter()

evt_mgr = spectre.trading.MarketEventManager(calendar_2020)
evt_mgr.subscribe(loader)

alg = MyAlg(blotter, main=loader)
evt_mgr.subscribe(alg)
evt_mgr.run()

"""
from .event import (
    Event,
    EveryBarData,
    Always,
    MarketOpen,
    MarketClose,
    EventReceiver,
    EventManager,
)
from .algorithm import (
    CustomAlgorithm,
    SimulationEventManager
)
from .blotter import (
    Portfolio,
    BaseBlotter,
    SimulationBlotter
)
from .metric import (
    drawdown,
    sharpe_ratio,
    turnover,
    plot_cumulative_returns
)


def run_backtest(loader: 'DataLoader', alg_type: 'Type[CustomAlgorithm]', start, end):
    # force python to free memory, else will encountering cuda out of memory
    import gc
    gc.collect()

    _blotter = SimulationBlotter(loader)
    evt_mgr = SimulationEventManager()
    alg = alg_type(_blotter, main=loader)
    evt_mgr.subscribe(_blotter)
    evt_mgr.subscribe(alg)
    evt_mgr.run(start, end)

    return alg.results