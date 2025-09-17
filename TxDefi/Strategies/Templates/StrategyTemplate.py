from TxDefi.Data.MarketDTOs import *
from TxDefi.Data.TradingDTOs import *
from TxDefi.Abstractions.AbstractTradingStrategy import AbstractTradingStrategy
from TxDefi.Abstractions.AbstractTradesManager import AbstractTradesManager
import TxDefi.Data.Globals as globals

class StrategyTemplate(AbstractTradingStrategy):
    def __init__(self, trades_manager: AbstractTradesManager, settings: dict[str, any]):
        AbstractTradingStrategy.__init__(self, trades_manager, [globals.topic_ui_command], settings)

    def process_event(self, id: int, event: any):
        pass

    def load_from_dict(self, strategy_settings: dict[str, any]):
        pass

    def load_from_obj(self, obj: object): 
        pass

    def get_status(self)->str:
        return "Status details" #TODO
     
    @classmethod
    def create(cls, trades_manager: AbstractTradesManager, settings: dict[str, any])->"StrategyTemplate":
        return StrategyTemplate(trades_manager, settings)

    @classmethod
    def custom_schema(cls): #Example Only
        ret_schema ={
            "custom_field" : "Build your own - define fields that you need. Just load and use them in your <Strategy>.py ",
        }

        ret_schema.update(SwapOrderSettings.schema()) #Optional
        ret_schema.update(SignerWalletSettings.schema()) #Optional
        
        return ret_schema
