from TxDefi.Abstractions.AbstractOrderFacet import AbstractOrderFacet
from TxDefi.Data.TransactionInfo import SwapTransactionInfo
from TxDefi.Engines.TradesExecutors import *
from TxDefi.Managers.MarketManager import MarketManager

class SimExecutor(OrderExecutor[SwapOrder]):
    def __init__(self, market_manager: MarketManager, trade_manager: AbstractTradesManager, default_wallet_settings: SignerWalletSettings, default_sol_amount: Amount):
        OrderExecutor.__init__(self)
        #Create a map of order executors to handle the various types of orders
        self.market_manager = market_manager
        self.trade_manager = trade_manager
        self.transaction_id = 0
        self.swap_info_history : dict[int, list[SwapTransactionInfo]] = {}
        self.max_history = 10

        self.sol_balances : dict[str, Amount] = { default_wallet_settings.get_default_signer().get_account_address() : default_sol_amount} #key=owner address
        self.token_balances : dict[str, dict[str, Amount]] = {} #key=owner address

    def get_token_account_balance(self, token_address: str, owner_address: str)->Amount:
        return self.token_balances.get(owner_address, {}).get(token_address)
     
    #TODO handle swap bundles
    def execute_impl(self, order: SwapOrder, max_tries: int)->list[str]: 
        owner_address = order.get_wallet_settings().get_default_signer().get_account_address()
        sol_balance = self.sol_balances.get(owner_address)
        token_balance = self.get_token_account_balance(order.token_address, owner_address)

        if sol_balance:
            tx_signatures : list[str] = []
            swap_info = SwapTransactionInfo(str(self.transaction_id), 0) #TODO Use current slot onchain as a means to simulate trade latency if desired
            swap_info.token_address = order.token_address
            swap_info.fee = order.swap_settings.priority_fee.to_scaled()   
            swap_info.payer_token_account_address = "NA" 
            swap_info.payer_address = order.wallet_settings.get_default_signer().get_account_address()
            
            if not token_balance:
                token_balance = Amount.tokens_ui(0, swap_info.token_decimals)
                token_balances = self.token_balances.get(owner_address)

                if not token_balances:
                    token_balances : dict[str, Amount] = {}
                    self.token_balances[owner_address] = token_balances
                    
                token_balances[order.token_address] = token_balance
                
            if order.order_type == TradeEventType.BUY:
                token_exchange_amount = self.trade_manager.get_exchange(order.token_address, order.swap_settings.amount, True)
            
                #Subtract the amount from our reserves                
                sol_balance.add_amount(-order.swap_settings.amount.to_scaled(), Value_Type.SCALED)
                token_balance.add_amount(token_exchange_amount.to_ui(), Value_Type.UI)

                swap_info.sol_balance_change = -order.swap_settings.amount.to_scaled()
                swap_info.token_balance_change = token_exchange_amount.to_ui() 
                swap_info.token_decimals = token_exchange_amount.decimals
            else:
                sol_exchange_amount = self.trade_manager.get_exchange(order.token_address, order.swap_settings.amount, False)
        
                #Add the amount from our reserves
                sol_balance.add_amount(sol_exchange_amount.to_scaled(), Value_Type.SCALED)
                token_balance.add_amount(-order.swap_settings.amount.to_ui(), Value_Type.UI)
     
                swap_info.sol_balance_change = sol_exchange_amount.to_scaled()
                swap_info.token_balance_change = -order.swap_settings.amount.to_ui() 
                swap_info.token_decimals = order.swap_settings.amount.decimals
            
            if token_balance.to_ui() <= 0: #Remove if token balance is 0
                self.token_balances.get(owner_address).pop(order.token_address)
            
            swap_info.payer_token_ui_balance = token_balance.to_ui()            

            tx_signatures.append(swap_info.tx_signature)

            self.swap_info_history[self.transaction_id] = [swap_info]

            if len(self.swap_info_history) > self.max_history:
                (k := next(iter(self.swap_info_history)), self.swap_info_history.pop(k))

            self.transaction_id += 1

            return tx_signatures
        
class SimOrderFacet(AbstractOrderFacet, ):
    def __init__(self, market_manager: MarketManager, trade_manager: AbstractTradesManager, default_wallet_settings: SignerWalletSettings, default_sol_amount: Amount):
        AbstractOrderFacet.__init__(self, trade_manager)
        self.sim_executor = SimExecutor(market_manager, trade_manager, default_wallet_settings, default_sol_amount)
        self.add_executor(SwapOrder, self.sim_executor)

    def load(): #TODO implement a save and load state mechanism
        pass
    
    def save():
        pass

    def get_sol_balance(self, account_address: str)->Amount:
        return self.sim_executor.sol_balances.get(account_address)

    def get_token_account_balance(self, token_address: str, owner_address: str)->Amount:
        return self.sim_executor.get_token_account_balance(token_address, owner_address)

    def get_swap_info(self, tx_signature: str, target_pubkey: str, maxtries = 30)->list[SwapTransactionInfo]:
        return self.sim_executor.swap_info_history.get(int(tx_signature)) 

