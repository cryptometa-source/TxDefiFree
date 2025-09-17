from abc import abstractmethod
from TxDefi.Abstractions.AbstractTradesManager import AbstractTradesManager
from TxDefi.Abstractions.OrderExecutor import OrderExecutor
from TxDefi.Data.Amount import Amount
from TxDefi.Data.MarketDTOs import *
from TxDefi.Data.TradingDTOs import *
from TxDefi.Engines.TradesExecutors import McapExecutor, PnlExecutor
from TxDefi.Strategies.StrategyRunner import StrategyRunner

class AbstractOrderFacet:
    def __init__(self, trades_manager: AbstractTradesManager):
        self.strategy_runner = StrategyRunner()

        pnl_executor = PnlExecutor(trades_manager, self.strategy_runner)
        mcap_executor = McapExecutor(trades_manager, self.strategy_runner)
        
        #Create a map of order executors to handle the various types of orders
        self.order_exec_map: dict[type[ExecutableOrder], OrderExecutor] = {OrderWithLimitsStops: pnl_executor, McapOrder: mcap_executor}

    def add_executor(self, order_type: type[ExecutableOrder], executor: OrderExecutor):
        self.order_exec_map[order_type] = executor
        
    def get_strategy_runner(self)->StrategyRunner:
        return self.strategy_runner

    def stop(self):
        for executor in self.order_exec_map.values():
            executor.stop()

    @abstractmethod
    def get_token_account_balance(self, token_address: str, owner_address: str)->Amount:
        pass

    @abstractmethod
    def get_sol_balance(self, account_address: str)->Amount:
        pass
                  
    @abstractmethod
    def get_swap_info(self, tx_signature: str, target_pubkey: str, maxtries = 30)->list[SwapTransactionInfo]:
        pass

    def get_order_executor(self, order: ExecutableOrder):
        return self.order_exec_map.get(type(order))
