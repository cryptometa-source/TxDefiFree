from typing import TypeVar, Type
from typing import cast
import os
import sys

# insert root directory into python module search path
sys.path.insert(1, os.getcwd())
from TxDefi.Data.MarketEnums import *
from TxDefi.Data.MarketDTOs import ProfitLoss
from TxDefi.Utilities.Encryption import SupportEncryption
from TxDefi.Abstractions.AbstractKeyPair import AbstractKeyPair
from TxDefi.Data.Factories import KeyPairFactory
from TxDefi.Data.Globals import Command
from TxDefi.Data.Amount import Amount

T_KeyPair = TypeVar("T_KeyPair", bound=AbstractKeyPair)  # Generic type Key Pair Type

class TriggerPrice:
    def __init__(self, in_sell_amount: Amount, target_price: Amount):
        self.in_sell_amount = in_sell_amount
        self.target_price = target_price
        
class PnlOption:
    def __init__(self, trigger_at_percent: Amount, allocation_percent: Amount):
        self.trigger_at_percent = trigger_at_percent
        self.allocation_percent = allocation_percent
    
    def serialize(self)->dict:
        return {"trigger_at_percent" : self.trigger_at_percent.to_ui(), "allocation_percent" : self.allocation_percent.to_ui()}
    
    @staticmethod
    def from_dict(values: dict[str, any]):
        return PnlOption(Amount.percent_ui(values.get("trigger_at_percent", 0)),
                        Amount.percent_ui(values.get("allocation_percent", 100)))   


class SocialEvent:
    def __init__(self, user: str, message: str):
        self.user = user
        self.message = message

class CallEvent(SocialEvent):
    def __init__(self, user: str, message: str, contract_addresses: list[str]):
        SocialEvent.__init__(self, user, message)

        self.contract_addresses = contract_addresses

class TradeModeSettings:
    def __init__(self, trade_mode: TradeMode, default_amount: Amount):
        self.trade_mode = trade_mode
        self.default_amount = default_amount

class SignerWalletSettings:
    def __init__(self, default_signer: AbstractKeyPair = None):    
        self.signer_wallets : list[AbstractKeyPair] = []
        self.has_custom_amt = False
        self.default_signer_wallet = default_signer

        if default_signer:
            self.add_wallet(default_signer)

    def add_wallet(self, signer_wallet: AbstractKeyPair):
        if signer_wallet not in self.signer_wallets:
            self.signer_wallets.append(signer_wallet)

    def has_custom_amount(self):
        return self.has_custom_amount
    
    def is_single_signer(self)->bool:
        return len(self.signer_wallets) == 1
    
    def set_default_signer(self, signer_wallet: AbstractKeyPair):
        if signer_wallet not in self.signer_wallets:
            self.add_wallet(signer_wallet)
        
        self.default_signer_wallet = signer_wallet

    def get_default_signer(self)->AbstractKeyPair:
        if not self.default_signer_wallet and len(self.signer_wallets) > 0:
            self.default_signer_wallet = self.signer_wallets[0]

        return self.default_signer_wallet

    def serialize(self)->dict:
        pubkey_infos : list[dict] = []
        encryption = None    
        ret_dict = {"pubkeys" : pubkey_infos, "key_encryption" : None,  "blockchain": "SOL" } 

        for wallet in self.signer_wallets:
            if not encryption:
                encryption = wallet.encryption.name
            
            if wallet.encryption == SupportEncryption.NONE:
                encrypted_key = wallet.decrypted_key
            else:
                encrypted_key = wallet.encrypted_key

            wallet_info = {"pubkey" : encrypted_key}

            if wallet.amount_in and wallet.amount_in.value > 0:
                wallet_info["amount_in"] = wallet.amount_in.to_ui()

            pubkey_infos.append(wallet_info)
        
        ret_dict["key_encryption"] = encryption

        return ret_dict
    
    @staticmethod
    def from_dict(order_settings: dict[str, any])->"SignerWalletSettings":
        signer_key_encryption = order_settings.get("key_encryption", "NONE")
        
        blockchain_str = order_settings.get("blockchain", "SOL")
        encryption = SupportEncryption.to_enum(signer_key_encryption)
        blockchain = Blockchain.to_enum(blockchain_str)
        
        signer_keys : list[dict] = order_settings.get("pubkeys")
        ret_signer_settings: SignerWalletSettings = None
        
        if signer_keys and len(signer_keys) > 0:                
            ret_signer_settings = SignerWalletSettings()
            for entry in signer_keys:
                pubkey = entry.get("pubkey")
                custom_amount_in = entry.get("amount_in") #Assumes SOL only for config files

                if custom_amount_in:
                    custom_amount_in = Amount.sol_ui(custom_amount_in)
                    ret_signer_settings.has_custom_amt = True
                    
                ret_signer_settings.add_wallet(KeyPairFactory.create(pubkey, blockchain, encryption, True, custom_amount_in))           

        return ret_signer_settings         

    @classmethod
    def schema(cls): 
        return {
        "pubkeys" : [{"pubkey": "1st key", 
                        "amount_in": 0.0},
                     {"pubkey": "2nd key and so forth", 
                        "amount_in": 0.0}           
            ],      
        "key_encryption": "None" 
    }
    
class ExecutableOrder:
    def __init__(self, order_type: TradeEventType, wallet_settings: SignerWalletSettings = None):
        self.order_type = order_type
        self.wallet_settings = wallet_settings

    def get_wallet_settings(self):
        return self.wallet_settings   

    def set_wallet_settings(self, wallet_settings: SignerWalletSettings):
        self.wallet_settings = wallet_settings
        
    def serialize(self)->dict:
        ret_dict = {"order_type" : self.order_type.name}

        if self.wallet_settings:
            ret_dict.update(self.wallet_settings.serialize())

        return ret_dict
    
    @staticmethod
    def from_dict(order_settings: dict[str, any])->"ExecutableOrder":
        order_type_name = order_settings.get("order_type")
        wallet_settings = SignerWalletSettings.from_dict(order_settings)

        if order_type_name:
            order_type = TradeEventType.to_enum(order_type_name)
            
            return ExecutableOrder(order_type, wallet_settings)

class SwapOrderSettings:
    def __init__(self, in_amount: Amount, slippage: Amount, priority_fee: Amount, confirm_transaction = True, jito_tip: Amount = None):
        self.amount = in_amount
        self.slippage = slippage
        self.priority_fee = priority_fee
        self.jito_tip = jito_tip
        self.confirm_transaction = confirm_transaction

    def clone(self)->"SwapOrderSettings":
        jito_tip = self.jito_tip.clone() if self.jito_tip else None
        return SwapOrderSettings(self.amount.clone(), self.slippage.clone(), self.priority_fee.clone(), self.confirm_transaction, jito_tip)

    def serialize(self)->dict:
        ret_dict = {"in_amount" : self.amount.to_ui(), "slippage" : self.slippage.to_ui(), 
                    "priority_fee": self.priority_fee.to_ui(), "confirm_transaction": self.confirm_transaction}
        ret_dict["jito_tip"] = self.jito_tip.to_ui() if self.jito_tip else 0.0

        return ret_dict
       
    @staticmethod
    def load_from_dict(order_settings: dict[str, any])->"SwapOrderSettings":
        in_amount = Amount.sol_ui(float(order_settings.get("amount_in", .0001)))  
        slippage = Amount.percent_ui(float(order_settings.get("slippage", 1)))
        priority_fee = Amount.sol_ui(float(order_settings.get("priority_fee", 1)))        
        jito_tip = Amount.sol_ui(float(order_settings.get('jito_tip', 0)))
        temp_str = order_settings.get("confirm_transaction", "True")        
        confirm_transaction = True if temp_str == "True" else False
    
        return SwapOrderSettings(in_amount, slippage, priority_fee, confirm_transaction, jito_tip)

    @classmethod
    def schema(cls): 
        return {
        "amount_in": 0.0,
        "slippage": 0,
        "priority_fee": 0.0,
        "jito_tip": 0.0,
        "confirm_transaction": True,
    }     

class SwapOrder(ExecutableOrder):
    def __init__(self, order_type: TradeEventType, token_address: str, swap_settings: SwapOrderSettings, wallet_settings: SignerWalletSettings = None):
        ExecutableOrder.__init__(self, order_type, wallet_settings)
        self.use_signer_amount = False
        self.token_address = token_address
        self.swap_settings = swap_settings
    
    def set_use_signer_amount(self, use_signer_amount: bool):
        self.use_signer_amount = use_signer_amount

    def get_signer_amount(self, signer: T_KeyPair)->Amount:
        #Use custom signer amount if available
        if signer.amount_in:
            amount_in = signer.amount_in
        else:
            amount_in = self.swap_settings.amount

        return amount_in

    def serialize(self)->dict:
        ret_dict = {"token_address" : self.token_address}
        ret_dict.update(super().serialize())
        ret_dict.update(self.swap_settings.serialize())

        return ret_dict
    
    @staticmethod
    def from_dict(order_settings: dict[str, any])->"SwapOrder":
        token_address = order_settings.get("token_address")
        order_type_str = order_settings.get("order_type")

        if order_type_str:
            order_type = TradeEventType.to_enum(order_type_str)
        else:    
            order_type = TradeEventType.EXCHANGE

        if token_address:
            swap_order_settings = SwapOrderSettings.load_from_dict(order_settings)
            wallet_settings = SignerWalletSettings.from_dict[T_KeyPair](order_settings)
        
            return SwapOrder(order_type, token_address, swap_order_settings, wallet_settings)

    @classmethod
    def schema(cls):
        ret_schema = {
            "order_type" : "BUY | SELL",
            "token_address" : "contract address",
            "use_signer_amount" : False
        }
        
        ret_schema.update(SwapOrderSettings.schema())
        ret_schema.update(SignerWalletSettings.schema())
        return ret_schema
    
class BundledSwapOrder(SwapOrder):
    bundle_limit = 5
    def __init__(self, order_type: TradeEventType, token_address: str, swap_settings: SwapOrderSettings, wallet_settings: SignerWalletSettings):
        SwapOrder.__init__(self, order_type, token_address, swap_settings, wallet_settings)
        self.use_signer_amount = True #Will use whatever is set in the wallets
        self.bundled_swap_orders : list[SwapOrder] = []

    def add_swap_order(self, order: SwapOrder):
        if len(self.bundled_swap_orders) == self.bundle_limit:
            raise Exception("Bundle order exceeded the limit!")

        self.bundled_swap_orders.append(order)

class OrderWithLimitsStops(SwapOrder):
    def __init__(self, token_address: str, base_token_price: Amount, order_type: TradeEventType, swap_settings: SwapOrderSettings, is_trailing = False, wallet_settings: SignerWalletSettings = None):
        if order_type == TradeEventType.SELL:
            order_type = TradeEventType.LO_PENDING_SELL #Must be a limit order pending sell
        SwapOrder.__init__(self, order_type, token_address, swap_settings, wallet_settings)

        self.limits: list[PnlOption] = []
        self.stop_losses: list[PnlOption] = []
        self.base_token_price = base_token_price
        self.is_trailing = is_trailing

    def get_swap_order(self)->SwapOrder:
        return SwapOrder(self.order_type, self.token_address, self.swap_settings, self.wallet_settings)
    
    def add_pnl_option(self, pnl_option: PnlOption):
        if pnl_option.trigger_at_percent.to_ui() > 0:
            self.limits.append(pnl_option)
        elif pnl_option.trigger_at_percent.to_ui() < 0:
            self.stop_losses.append(pnl_option)

    def serialize(self)->dict:
        ret_dict = {"base_token_price" : self.base_token_price.to_ui(), "self.is_trailing" : self.is_trailing, "limit_orders": [], "stop_loss_orders" : []}

        for limit in self.limits:           
            ret_dict["limit_orders"].append(limit.serialize())

        for stop in self.stop_losses:
            ret_dict["stop_loss_orders"].append(stop.serialize())

        ret_dict.update(super().serialize())

        return ret_dict
    
    @staticmethod
    def from_dict(order_settings: dict[str, any])->"OrderWithLimitsStops":
        swap_settings = SwapOrderSettings.load_from_dict(order_settings)
        token_address = order_settings.get("token_address")
        is_trailing = order_settings.get("token_address", False)
        limits_dict = order_settings.get("limit_orders", [])
        stops_dict = order_settings.get("stop_loss_orders", [])
        base_token_price = Amount.sol_ui(order_settings.get("base_token_price"))

        limits: list[PnlOption] = []
        stops: list[PnlOption] = []

        for limit_info in limits_dict:
            limits.append(PnlOption.from_dict(limit_info))
      
        for stop_info in stops_dict:
            stops.append(PnlOption.from_dict(stop_info))

        wallet_settings = SignerWalletSettings.from_dict(order_settings)

        return OrderWithLimitsStops(token_address, base_token_price, TradeEventType.LO_PENDING_SELL, swap_settings, is_trailing, wallet_settings)

    @classmethod
    def schema(cls):
        ret_schema = {
        "token_address" : "contract address",
        "base_token_price" : 0.0,   
        "is_trailing" : False,     
        "limit_orders" : [{"trigger_at_percent": 50, "allocation_percent": 100}],
        "stop_loss_orders" : [{"trigger_at_percent": -99, "allocation_percent": 100}]
        }

        ret_schema.update(SwapOrderSettings.schema())
        return ret_schema

class McapOrder(SwapOrder):
    def __init__(self, order_type: TradeEventType, token_address: str, swap_settings: SwapOrderSettings, target_mcap: Amount, wallet_settings: SignerWalletSettings = None, limit_orders: OrderWithLimitsStops = None):
        SwapOrder.__init__(self, order_type, token_address, swap_settings, wallet_settings)
        self.limit_orders = limit_orders
        self.target_mcap = target_mcap

    def serialize(self)->dict:
        ret_dict = {"target_mcap" : self.target_mcap.to_ui()}
        ret_dict.update(super().serialize())

        if self.limit_orders:
            ret_dict.update(self.limit_orders.serialize())

        return ret_dict
    
    @staticmethod
    def from_dict(order_settings: dict[str, any])->"McapOrder":
        token_address = order_settings.get("token_address")
        target_mcap = order_settings.get("target_mcap")
        order_type_str = order_settings.get("order_type", "BUY")                
        order_type = TradeEventType.to_enum(order_type_str)

        swap_settings = SwapOrderSettings.load_from_dict(order_settings)
        wallet_settings = SignerWalletSettings.from_dict(order_settings)
        limit_orders = OrderWithLimitsStops.from_dict(order_settings)

        return McapOrder(order_type, token_address, swap_settings, target_mcap, wallet_settings, limit_orders)
    
    @classmethod
    def schema(cls):
        ret_schema = {
            "target_mcap" : 0.0,        
        }

        ret_schema.update(SwapOrder.schema())
        ret_schema.update(OrderWithLimitsStops.schema())

        return ret_schema
    
#0 uses default trade amount set in config; if isForced is set, trade manager disregards any risk protection
class TradeCommand(Command):
  def __init__(self, command: UI_Command, mint_address: str, amount_in: Amount, prompt_user: bool, is_forced = False):
      Command.__init__(self, command)
      self.mint_address = mint_address
      self.promptUser = prompt_user
      self.is_forced = is_forced
      self.amount_in = amount_in

class DeleteCommand(Command):
    def __init__(self, command: UI_Command, mint_address: str, supported_pg: SupportedPrograms):
        Command.__init__(self, command)
        self.mint_address = mint_address
        self.supported_pg = supported_pg

class LoadSideWidgetCommand(Command):
    def __init__(self, mint_address: str):
        Command.__init__(self, UI_Command.FORCE_ADD_TOKEN)
        self.mint_address = mint_address

class TradeState:
    def __init__(self, token_address: str):
        self.token_address = token_address
        self.active_trades : dict[float, Amount] = {} #key=cost basis price; Stores available token amount for each active trade

    def active_trade_count(self):
        return len(self.active_trades)
    
    def get_total_tokens_held(self)->Amount:
        active_trades_list = list(self.active_trades.values())
        
        if len(active_trades_list) > 0:
            ret_amount = 0
            decimals = active_trades_list[0].decimals

            for amount in active_trades_list:
                ret_amount += amount.to_ui()
            
            return Amount.tokens_ui(ret_amount, decimals)
    
    def add_token_amount(self, current_price: Amount, token_amount: Amount):
        trade = self.active_trades.get(current_price.to_ui())
        
        if trade:
            trade.add_amount(token_amount.to_ui(), Value_Type.UI)
        else:                    
            self.active_trades[current_price.to_ui()] = token_amount
            
        if len(self.active_trades) > 1:
            self.active_trades = dict(sorted(self.active_trades.items(), reverse=True))

    def substract_token_amount(self, token_amount: Amount):
        in_token_amount_ui = token_amount.to_ui()
        active_trades_list = list(self.active_trades.keys())

        for cost_basis_price_ui in active_trades_list:
            active_trade_amount = self.active_trades[cost_basis_price_ui]
            trade_amount_left_ui = active_trade_amount.to_ui()-in_token_amount_ui
            tokens_clipped_ui = min(in_token_amount_ui, active_trade_amount.to_ui())
            in_token_amount_ui -= tokens_clipped_ui

            if trade_amount_left_ui > 0: 
                active_trade_amount.set_amount2(trade_amount_left_ui, Value_Type.UI)
                break
            else: #Done with this trade
                self.active_trades.pop(cost_basis_price_ui)
               
                if in_token_amount_ui == 0:
                    break

    def get_estimated_pnl(self, current_price: Amount, in_token_amount: Amount)->ProfitLoss:
        in_token_amount_ui = in_token_amount.to_ui()
        active_trades_list = list(self.active_trades.keys())
        total_cost_basis_ui = 0
        trade_num = 0

        for cost_basis_price_ui in active_trades_list: 
            active_trade_amount = self.active_trades[cost_basis_price_ui]     
            trade_amount_left_ui = active_trade_amount.to_ui()-in_token_amount_ui

            tokens_clipped_ui = min(in_token_amount_ui, active_trade_amount.to_ui())       
                    
            #Calculate the weighted average
            total_cost_basis_ui += cost_basis_price_ui*tokens_clipped_ui
  
            in_token_amount_ui -= tokens_clipped_ui
            trade_num += 1

            if trade_amount_left_ui >= 0:
                break           
        try:            
            if total_cost_basis_ui == 0: #set pnl to 0% for unrecorded trades as we don't know
                entry_price_avg = current_price.to_ui()
                in_token_amount_ui = 0
            else:
                entry_price_avg = total_cost_basis_ui/in_token_amount.to_ui()

            price_diff = current_price.to_ui()-entry_price_avg
            exit_pnl = Amount.sol_ui(price_diff*in_token_amount.to_ui())

            #if entry_price_avg > 0:
            #    percent_pnl = Amount.percent_ui(price_diff/entry_price_avg*100)
            #else:
            #    percent_pnl = Amount.percent_ui(0)
        
            is_complete = True if in_token_amount_ui == 0 and trade_num == len(self.active_trades) else False
            cost_basis = Amount.tokens_ui(total_cost_basis_ui, current_price.decimals)
            
            if total_cost_basis_ui > 0:
                percent_pnl = Amount.percent_ui(exit_pnl.to_ui()/total_cost_basis_ui*100)
            else:
                percent_pnl = Amount.percent_ui(0)

            return ProfitLoss(self.token_address, exit_pnl, percent_pnl, cost_basis, in_token_amount, is_complete)
        except Exception as e:
            print("TradingDTOs: Error in get_estimated_pnl " + str(e)) 