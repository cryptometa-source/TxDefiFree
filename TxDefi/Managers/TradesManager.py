import json
import time
import concurrent.futures
import threading

from pubsub import pub
from TxDefi.Managers.Facets.SimOrderFacet import SimOrderFacet
from TxDefi.Strategies.StrategyFactory import StrategyFactory
from TxDefi.Abstractions.AbstractTradingStrategy import AbstractTradingStrategy
from TxDefi.Abstractions.AbstractTradesManager import AbstractTradesManager
from TxDefi.Abstractions.AbstractSubscriber import AbstractSubscriber
from TxDefi.DataAccess.Blockchains.Solana.SolanaRpcApi import *
from TxDefi.DataAccess.Blockchains.Solana.SolPubKey import *
from TxDefi.Managers.MarketManager import MarketManager
from TxDefi.Data.TradingDTOs import *
from TxDefi.Data.MarketDTOs import *
from WalletTracker import WalletTracker
import TxDefi.Utilities.FinanceUtil as finance_util
import TxDefi.Data.Globals as globals

class TradesManager(AbstractTradesManager[ExecutableOrder], AbstractSubscriber[AccountInfo], threading.Thread):
    def __init__(self, solana_rpc_api: SolanaRpcApi, market_manager: MarketManager, wallet_tracker: WalletTracker,
                  strategy_factory: StrategyFactory, default_trade_settings: SwapOrderSettings, default_wallet_settings: SignerWalletSettings, trade_mode_settings: TradeModeSettings):
        AbstractTradesManager.__init__(self, solana_rpc_api, market_manager, wallet_tracker, default_trade_settings, default_wallet_settings)
        AbstractSubscriber.__init__(self)
        threading.Thread.__init__(self)
        self.strategy_factory = strategy_factory
        self.active_trades : dict[str, TradeState] = {} #key=token address; Stores cost basis for each active trade
        self.trade_mode = trade_mode_settings.trade_mode
        self.default_wallet_settings = default_wallet_settings
        self.default_payer = self.default_wallet_settings.get_default_signer()

        if self.trade_mode  == TradeMode.SIM:
            self.order_facet = SimOrderFacet(market_manager, self, default_wallet_settings, trade_mode_settings.default_amount)

        self.default_wallet_account_balance = self.order_facet.get_sol_balance(self.default_payer.get_account_address())
        self.strategy_runner = self.order_facet.get_strategy_runner()

        self.trade_infos : dict[str, TradeInfo] = {} #key=tx_signature
        self.trade_events : dict[str, threading.Event] = {} #key=tx_signature
        
        self.total_realized_profit = Amount.sol_ui(0)
        self.total_realized_loss = Amount.sol_ui(0)
        self.total_unrealized_profit = Amount.sol_ui(0)

        self.cancel_token = threading.Event()
     
    def run(self):
        self._update_stats_task()

    #Executes and initiates retrieving a transaction off of the blockchain
    def execute(self, order: ExecutableOrder, max_tries = 1)->list[str]:
        order_executor = self.order_facet.get_order_executor(order) 

        if order_executor:                
            if order.get_wallet_settings() is None:
                order.set_wallet_settings(self.get_default_wallet_settings())

            signatures = order_executor.execute(order, max_tries)

            if signatures:
                for signature in signatures:
                    with concurrent.futures.ThreadPoolExecutor() as executor: #Set thread limit?
                        executor.submit(self._process_transaction, order, signature)
                
                return signatures

    def run_strategy_from_settings(self, strategy_settings: dict[str, any])->list[str]:
        if self.strategy_factory:
            strategy = self.strategy_factory.create_strategy(self, strategy_settings)

            if strategy:        
                return self.run_strategy(strategy)

    #input is path to the strategies file
    def run_strategies(self, strategies_config_path: str)-> list[int]:
        ret_values = []

        with open(strategies_config_path, 'r') as file:
            strategies = json.load(file)

            if strategies:                
                if isinstance(strategies, list):
                    for strategy_settings in strategies:
                        ret_value = self.run_strategy_from_settings(strategy_settings)
                        ret_values.append(ret_value)
                else:
                     ret_value = self.run_strategy_from_settings(strategies)
                     ret_values.append(ret_value)
                     
            return ret_values
    
    def get_running_strategy(self, strategy_id: str)->AbstractTradingStrategy:
        return self.strategy_runner.get_strategy(strategy_id)

    def get_running_strategies(self)->list[AbstractTradingStrategy]:
        return list(self.strategy_runner.active_strategies.values())
    
    def get_strategy_factory(self)->StrategyFactory:
        return self.strategy_factory
    
    def run_strategy(self, strategy: AbstractTradingStrategy)->list[str]:
        return self.strategy_runner.execute(strategy)

    def _process_transaction(self, order: ExecutableOrder, signature: str):      
        if self.strategy_runner.get_strategy(signature) and isinstance(order, OrderWithLimitsStops):
            token_info = self.market_manager.get_token_info(order.token_address, False)

            trade_info = TradeInfo.create(token_info, order.order_type, signature)
            #Need to generate a trade info so clients can populate their views with the active trade
            self._record_active_trade(trade_info)

            pub.sendMessage(topicName=globals.topic_strategies_event, arg1=trade_info)
        else:
            trade_info = self.get_trade_info(signature)

            if trade_info:
                #Publish the trade info
                pub.sendMessage(topicName=globals.topic_trade_event, arg1=trade_info)

                if trade_info.get_type() == TradeEventType.SELL:
                    if trade_info.token_address in self.active_trades:
                        token_trades = self.active_trades.get(trade_info.token_address)
                        
                        if trade_info.amount_in.to_ui() > 0:
                            #Track Pnl for this trade
                            price = Amount.sol_ui(trade_info.amount_out.to_ui()/trade_info.amount_in.to_ui())
                            profitloss = token_trades.get_estimated_pnl(price, trade_info.amount_in)
                    
                            if profitloss.pnl.to_ui() > 0:
                                self.total_realized_profit.add_amount(profitloss.pnl.to_ui(), Value_Type.UI)
                            else:
                                self.total_realized_loss.add_amount(profitloss.pnl.to_ui(), Value_Type.UI)
                    else:
                        profitloss = ProfitLoss(trade_info.token_address, trade_info.amount_out, Amount.percent_ui(0), trade_info.amount_out, trade_info.amount_in, True)
                
                    profitloss.tx_signature = trade_info.tx_signature

                    #Publish PNL to subscribers
                    pub.sendMessage(topicName=globals.topic_token_alerts, arg1=profitloss)    

                #for trade_info in trade_infos: #FYI ray sometimes splits the trade in two; Ignoring this for now
                self._record_active_trade(trade_info)
            
    def _record_active_trade(self, trade_info: TradeInfo)->TradeState:
        trade_state = self.active_trades.get(trade_info.token_address)

        if not trade_state:
            trade_state = TradeState(trade_info.token_address)
            self.active_trades[trade_info.token_address] = trade_state
        
        if trade_info.get_type() == TradeEventType.BUY:            
            trade_state.add_token_amount(trade_info.get_price(), trade_info.amount_out)
        elif trade_info.get_type() == TradeEventType.SELL:      
            trade_state.substract_token_amount(trade_info.amount_in)

            if trade_state.active_trade_count() == 0:
                self.active_trades.pop(trade_info.token_address)

        return trade_state

    @staticmethod
    def _get_exchange_type(balance_change: float)->TradeEventType:
        if balance_change > 0:
            return TradeEventType.BUY
        else:
            return TradeEventType.SELL
    
    def wait_for_trade_info(self, tx_signature: str, timeout=30)->TradeInfo:
        """Waits for self.trade_infos[tx_signature] to be initialized"""
        if tx_signature not in self.trade_infos:
            print("Waiting for trade " + tx_signature)
            event = self.trade_events.setdefault(tx_signature, threading.Event())
            event.wait(timeout=timeout)

        return self.trade_infos.get(tx_signature) #Return the initialized data
    
    #Assumes this is a simple one-for-one trade; don't use for complex transactions involving multiple tokens
    def get_trade_info(self, tx_signature: str)->TradeInfo:
        if tx_signature in self.trade_infos:
            return self.trade_infos[tx_signature]

        transaction_info_list = self.get_swap_info(tx_signature, self.default_payer.get_account_address(), 30)   
        target_token_info = None
        token_amount = None
        fee = Amount.sol_ui(0)
        sol_amount = Amount.sol_ui(0) #initialize for possible sol wsol payment splits
        
        if transaction_info_list:
            for transaction_info in transaction_info_list:      
                token_info = self.market_manager.get_token_info(transaction_info.token_address)
                
                if token_info:                
                    #base_token_price = Amount.sol_scaled(abs(transaction_info.sol_balance_change/transaction_info.token_balance_change))
                    inner_sol_amount = transaction_info.sol_balance_change
                    inner_token_amount = transaction_info.token_balance_change #Amount.tokens_ui(abs(transaction_info.token_balance_change), token_info.token_vault_amount.decimals)

                    #print(f"Received Transaction {tx_signature} Base Price: {base_token_price.to_ui()} Tokens: {payer_token_amount.to_ui()}") #DELETE

                    #Safe to say that if you earned WSOL, this has to be a sale
                    if token_info.token_address == solana_utilites.WRAPPED_SOL_MINT_ADDRESS:
                        #Inverse the balance change to get the right exchange type
                        trade_type = self._get_exchange_type(-inner_token_amount)

                        sol_amount.add_amount(abs(inner_token_amount), Value_Type.SCALED)
                    else:
                        trade_type = self._get_exchange_type(inner_token_amount) 
                        target_token_info = token_info
                        fee.set_amount2(transaction_info.fee, Value_Type.SCALED)

                        if not (trade_type == TradeEventType.SELL and inner_sol_amount < 0): #Must have been WSOL if negative or 0
                            sol_amount.add_amount(abs(inner_sol_amount), Value_Type.SCALED)
                
                        token_amount = Amount.tokens_ui(abs(inner_token_amount), token_info.token_vault_amount.decimals)

                    #transaction_info.print_swap_info()

            if sol_amount and token_amount:                 
                if trade_type == TradeEventType.BUY:
                    ret_trade_info = TradeInfo(target_token_info, trade_type, sol_amount, token_amount, fee, tx_signature)
                else:             
                    ret_trade_info = TradeInfo(target_token_info, trade_type, token_amount, sol_amount, fee, tx_signature)

                self.trade_infos[tx_signature] = ret_trade_info

                if tx_signature in self.trade_events:
                    self.trade_events[tx_signature].set() #Notify waiting threads

                return ret_trade_info
            
    def delete_strategy(self, strategy_id: str):
        self.strategy_runner.delete_strategy(strategy_id)

    def fast_sell(self, token_address):
        trade = self.active_trades.get(token_address)

        if trade:
            swap_settings = self.default_trade_settings.clone()
            swap_settings.amount = trade.get_total_tokens_held()
            order = SwapOrder(TradeEventType.SELL, trade.token_address, swap_settings)
            self.execute(order, 3)

    def fast_buy(self, token_address):
        swap_settings = self.default_trade_settings.clone()
        order = SwapOrder(TradeEventType.BUY, token_address, swap_settings)
        self.execute(order, 3)

    def sell_all(self):
        for token_address in self.active_trades:
            self.fast_sell(token_address)

    #Sell non-positive PNL Trades
    def sweep(self):
        for token_address in self.active_trades:
            pnl = self.get_pnl(token_address)

            if pnl.pnl_percent <= 0:
                self.fast_sell(token_address)

    def get_market_manager(self):
        return self.market_manager

    def get_token_account_balance(self, token_address: str, owner_address: str):
        return self.order_facet.get_token_account_balance(token_address, owner_address)
           
    def get_default_payer_token_account_balance(self, token_address: str):
        return self.get_token_account_balance(token_address, self.default_payer.get_account_address())
    
    #Pause/Unpause a strategy 
    def toggle_strategy(self, strategy_id: int):
        print("TradesManager: Toggled " + str(strategy_id)) #DELETE
        strategy = self.strategy_runner.get_strategy(strategy_id)

        if strategy:
            if strategy.get_state() == StrategyState.OFF:
                strategy.resume_or_start_strategy()
            else:
                strategy.stop()

    #Pause any strategies associated with this token and pause them
    def hold(self, token_address: str):
        print("Not implemented yet.")
        pass #TODO need to pull strategies associated with this token
    
    def get_status(self, token_address: str)->str:        
        profit_loss = self.get_pnl(token_address)

        if profit_loss:
            status = f"PNL: {round(profit_loss.pnl.to_ui(), 7)}"
        else:
            status = ""

        return status
        
    def update(self, data: AccountInfo):
        if data.account_address == self.default_payer.get_account_address():
            self.default_wallet_account_balance = data.balance

    def get_sol_balance(self)->Amount:
        if self.trade_mode == TradeMode.SIM:
            return self.order_facet.get_sol_balance(self.default_payer.get_account_address())
        else:
            return self.default_wallet_account_balance                       
                  
    def get_pnl(self, token_address: str)->ProfitLoss:
        trade_state = self.active_trades.get(token_address)
        token_price = self.market_manager.get_price(token_address)

        if trade_state and token_price:
            return trade_state.get_estimated_pnl(token_price, trade_state.get_total_tokens_held())

    def get_total_profit(self)->Amount:
        return self.total_realized_profit

    def get_total_loss(self)->Amount:
        return self.total_realized_loss

    def get_unrealized_sol(self)->Amount:        
        return self.total_unrealized_profit 

    def get_swap_info(self, tx_signature: str, target_pubkey: str, maxtries = 30)->list[SwapTransactionInfo]:
        return self.order_facet.get_swap_info(tx_signature, target_pubkey, maxtries)

    def get_swap_info_default_payer(self, tx_signature: str, maxtries: int)->list[SwapTransactionInfo]:
        return self.order_facet.get_swap_info(tx_signature, self.default_payer.get_account_address(), maxtries)

    def get_exchange(self, token_address: str, amount_in: Amount, is_buy: bool)->Amount:
        token_info = self.market_manager.get_token_info(token_address)

        if token_info:
            if is_buy:
                exchange_amt = finance_util.estimate_exchange(token_info.sol_vault_amount.to_ui(), token_info.token_vault_amount.to_ui(), amount_in.to_ui()) 
                out_amount = Amount.tokens_ui(exchange_amt, token_info.token_vault_amount.decimals)
            else:
                exchange_amt = finance_util.estimate_exchange(token_info.token_vault_amount.to_ui(), token_info.sol_vault_amount.to_ui(), amount_in.to_ui())
                out_amount = Amount.sol_ui(exchange_amt)
            
            return out_amount

    def _update_stats_task(self):
        while not self.cancel_token.is_set():
            total_unrealized_pnl = 0
            self.solana_rpc_api.update_latest_block_hash() #Updates recent block hash every ten seconds

            trades = list(self.active_trades.values())

            for trade in trades:                
                current_price = self.market_manager.get_price(trade.token_address)
                tokens_held = trade.get_total_tokens_held()

                if current_price and tokens_held:
                    total_unrealized_pnl += trade.get_estimated_pnl(current_price, trade.get_total_tokens_held()).pnl.to_ui()

            self.total_unrealized_profit.set_amount2(total_unrealized_pnl, Value_Type.UI)
            
            time.sleep(10)
    
    def stop(self):
        self.cancel_token.set()
        self.order_facet.stop()


    