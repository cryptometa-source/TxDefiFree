from abc import abstractmethod
from pubsub import pub
from abc import ABC
import queue
import threading
import concurrent.futures
from typing import TypeVar, Generic
from TxDefi.Abstractions.AbstractTradesManager import AbstractTradesManager
from TxDefi.Abstractions.AbstractSubscriber import AbstractSubscriber
from TxDefi.Data.MarketEnums import *

T = TypeVar("T", bound=object)  # Generic type Key Pair Type
class AbstractTradingStrategy(ABC, threading.Thread, Generic[T], AbstractSubscriber[T]):
    def __init__(self, trades_manager: AbstractTradesManager, subbed_topics: list[str] = [], settings: dict[str, any] = None):
        threading.Thread.__init__(self, daemon=True)
        AbstractSubscriber.__init__(self)
        self.name = AbstractTradingStrategy.__name__
        self.trades_manager = trades_manager        
        self.state = StrategyState.OFF
        self.last_known_state = self.state
        self.unprocessed_event_counter = 0
        self.subbed_topics : list[str] = subbed_topics
        self.updates_lock = threading.Lock()
        self.event_queue = queue.Queue()
        self.event_count = 0        
        self.settings = settings 
        
        if self.settings:
            self.load_from_dict(self.settings)

    def get_settings(self)->dict:
        return self.settings

    def get_state(self)->StrategyState:
        return self.state
    
    def run(self):
        self.resume_or_start_strategy()

    def resume_or_start_strategy(self):
        self.state = StrategyState.RUNNING 

        for subbed_topic in self.subbed_topics:
            pub.subscribe(topicName=subbed_topic, listener=self._handle_update)     

    def stop(self):
        if self.state != StrategyState.COMPLETE:
            self.state = StrategyState.OFF 

        for subbed_topic in self.subbed_topics:
            pub.unsubscribe(topicName=subbed_topic, listener=self._handle_update)

    def _process_event_task(self, event: T):
        with self.updates_lock:
            event_count = self.event_count
            self.event_count += 1
            
        self.process_event(event_count, event)     

    def set_strategy_complete(self):
        self.state = StrategyState.COMPLETE

    def update(self, arg1: T):
        if self.state == StrategyState.COMPLETE:
            self.stop()
        elif self.state != StrategyState.OFF:
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                executor.submit(self._process_event_task, (arg1))           

    def _handle_update(self, arg1: T):
        self.update(arg1)

    @classmethod
    def save_json_template(cls, filepath: str):
        import json
        with open(filepath, 'w') as f:
            json.dump(cls.schema(), f, indent=4)

    @abstractmethod
    def load_from_dict(self, strategy_settings: dict[str, any]): 
        pass

    @abstractmethod
    def load_from_obj(self, obj: object): 
        pass

    @abstractmethod
    def process_event(self, id: int, event: any):
        pass

    @abstractmethod
    def get_status(self)->str:
        pass
       
    @classmethod
    def schema(cls): #Root schema for all strategies
        ret_schema = {
            "comment": "strategy_name must match the actual class name for a loaded py module",
            "strategy_name" :  cls.__name__,
            "strategy_title" : "A Strategy",
        }
        
        custom = cls.custom_schema()

        if custom:
            ret_schema.update(custom)
            
        return ret_schema  

    @classmethod
    @abstractmethod
    def custom_schema(cls)->dict: #Custom schema
        pass
      
    @classmethod
    @abstractmethod
    def create(cls, trades_manager: AbstractTradesManager, settings: dict[str, any])->"AbstractTradingStrategy":
        pass