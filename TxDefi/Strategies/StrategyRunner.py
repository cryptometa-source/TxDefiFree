from email import message
from TxDefi.Abstractions.AbstractTradingStrategy import AbstractTradingStrategy
from TxDefi.Data.TradingDTOs import *
import TxDefi.Utilities.LoggerUtil as logger_util

#TODO Remove inactive strategies
class StrategyRunner:
    def __init__(self):
        self.active_strategies : dict[int, AbstractTradingStrategy] = {}

    def execute(self, strategy: AbstractTradingStrategy)->list[str]:       
        strategy.start()

        self.active_strategies[strategy.get_id()] = strategy

        message = f"Strategy with id {strategy.get_id()} started successfully! Use the strategies configurator tool to monitor and manage it."
        print(message)
        logger_util.logger.info(message)
        return [strategy.get_id()]
    
    def delete_strategy(self, strategy_id: str):
        strategy = self.active_strategies.get(strategy_id)

        if strategy:
            strategy.stop()
            self.active_strategies.pop(strategy_id)
    
    def get_strategy(self, strategy_id: str)->AbstractTradingStrategy:
        return self.active_strategies.get(strategy_id)
