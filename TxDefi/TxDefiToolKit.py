import threading
import os
import json
import base58
from dotenv import load_dotenv
from solders.keypair import Keypair
import TxDefi.Data.Globals as globals
from TxDefi.Data.TradingDTOs import *
from TxDefi.DataAccess.Blockchains.Solana.RiskAssessor import RiskAssessor
from TxDefi.Engines.TokenInfoRetriever import TokenInfoRetriever
from TxDefi.Engines.TokenAccountsMonitor import TokenAccountsMonitor
from TxDefi.Managers.MarketManager import MarketManager
from TxDefi.Managers.TradesManager import TradesManager
from TxDefi.Managers.WalletTracker import WalletTracker
from TxDefi.DataAccess.Blockchains.Solana.SubscribeSocket import SubscribeSocket
from TxDefi.DataAccess.Blockchains.Solana.AccountSubscribeSocket import AccountSubscribeSocket
from TxDefi.DataAccess.Blockchains.Solana.SolanaRpcApi import SolanaRpcApi
from TxDefi.DataAccess.Blockchains.Solana.SolanaTradeExecutor import SolanaTradeExecutor
from TxDefi.DataAccess.Blockchains.Solana.SolPubKey import SolPubKey
from TxDefi.DataAccess.Decoders.TransactionsDecoder import TransactionsDecoder
from TxDefi.DataAccess.Decoders.MessageDecoder import MessageDecoder
from TxDefi.DataAccess.Decoders.SolanaLogsDecoder import SolanaLogsDecoder
from TxDefi.DataAccess.Decoders.PumpDataDecoder import *
from TxDefi.Strategies.StrategyFactory import StrategyFactory
from TxDefi.UI.EnvEditorUI import EnvEditorUI

#Tx Defi Toolkit Free Primary Setup
#Join the Discord for details on obtaining the complete Tx Defi version https://discord.gg/B2qHQj3bVR
class TxDefiToolKit(threading.Thread):
    default_none = "None"
    APP_NAME = "TxDefi Free"
    PROFILE_NAME = "xyz53"

    def __init__(self, disable_social_media = False):
        threading.Thread.__init__(self, daemon=True)
        self.name = TxDefiToolKit.__name__
        self.disable_social_media = disable_social_media

        wdir = os.getcwd()
        
        self.discord_monitor = None
        self.ifttt_webhook_monitor = None

        load_dotenv(wdir + "/.env", override=True)
        #Default Keys      
        default_sol = float(os.getenv('DEFAULT_SIM_SOL', "99.9"))
        trade_mode_settings = TradeModeSettings(TradeMode.SIM, Amount.sol_ui(default_sol))
        default_signer_keypair = Keypair() #Sim signer keypair
        payer_keys_hash = base58.b58encode(bytes(default_signer_keypair)).decode()    

        #RPC Credemtials
        rpc_http_uri = os.getenv('HTTP_RPC_URI')
        use_backup_rpc = False
        rpc_backup_uri = None

        rpc_wss_uri = os.getenv('WSS_RPC_URI')
        rpc_rate_limit = int(os.getenv('RPC_RATE_LIMIT', '10'))
        
        self.solana_rpc_api = SolanaRpcApi(rpc_http_uri, rpc_wss_uri, rpc_rate_limit, rpc_backup_uri)

        #Custom Strategies Path
        custom_strategies_path = os.getenv("CUSTOM_STRATEGIES_PATH") 

        #Init anchor Program so we can take advantage of the decoder  
        pump_client = SolanaTradeExecutor.create_program(globals.idl_path + "/pumpidl.json",
                                                         default_signer_keypair, self.solana_rpc_api.async_client)
        pump_pg_address = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
        pump_decoder = PumpDataDecoder(pump_pg_address, pump_client.coder, MessageDecoder.base58_encoding)
        
        self.sockets : dict[SupportedPrograms, SubscribeSocket] = {}
        self.wallet_transaction_socket = AccountSubscribeSocket(rpc_wss_uri, globals.topic_wallet_update_event, False) #Custom ping doesn't work for accountSubscribe so it's disabled here

        transactions_decoder = TransactionsDecoder()
        transactions_decoder.add_data_decoder(pump_pg_address, pump_decoder)
        pump_logs_decoder = SolanaLogsDecoder(pump_pg_address, self.solana_rpc_api, pump_decoder, transactions_decoder)
        
        #Auto Trade Settings
        auto_buy_in = float(os.getenv("AUTO_BUY_IN_SOL", ".001"))
        default_slippage = float(os.getenv('DEFAULT_SLIPPAGE', "50"))
        default_priority_fee = float(os.getenv('DEFAULT_PRIORITY_FEE', ".001"))    
        auto_trade_settings = SwapOrderSettings(Amount.sol_ui(auto_buy_in), Amount.percent_ui(default_slippage), Amount.sol_ui(default_priority_fee))
             
        #Setup Managers and Monitors
        self.wallet_tracker = WalletTracker(self.wallet_transaction_socket, self.solana_rpc_api)

        if os.path.exists(custom_strategies_path) and os.path.isdir(custom_strategies_path):
            strategy_factory = StrategyFactory(custom_strategies_path)
        else:
            strategy_factory = StrategyFactory(globals.library_root + "/Strategies/Examples")
            print("TxDefiToolKit: No strategies to load from " + custom_strategies_path +  ". Check your configuration.")

        tokens_info_retriever = TokenInfoRetriever(self.solana_rpc_api, pump_decoder, transactions_decoder, use_backup_rpc)        
        
        #Need the events coder for pump logs
        self.risk_assessor = RiskAssessor(self.solana_rpc_api)
        self.token_accounts_monitor = TokenAccountsMonitor(self.solana_rpc_api, tokens_info_retriever, pump_logs_decoder, self.risk_assessor)
        self.market_manager = MarketManager(self.solana_rpc_api, self.token_accounts_monitor, self.risk_assessor)

        default_payer = SolPubKey(payer_keys_hash, SupportEncryption.NONE, False, Amount.sol_ui(auto_buy_in))
        wallet_settings = SignerWalletSettings(default_payer)
        
        self.trades_manager = TradesManager(self.solana_rpc_api, self.market_manager, self.wallet_tracker, strategy_factory, auto_trade_settings, wallet_settings, trade_mode_settings)       

        #Init Logs Subscribe            
        pump_program_sub_request = json.dumps(SolanaRpcApi.get_logs_sub_request([pump_pg_address]))

        #Need 3 sockets to differentiate log messages; wss doesn't accept pings
        pump_logs_socket = SubscribeSocket(rpc_wss_uri, pump_logs_decoder, globals.topic_amm_program_event, [pump_program_sub_request], False)

        self.sockets[SupportedPrograms.PUMPFUN] = pump_logs_socket
              
        self.sockets[SupportedPrograms.GENERAL_WALLET] = self.wallet_transaction_socket
        self.cancel_event = threading.Event() #Create an Event object
        self.start()

    def toggle_socket_listener(self, program: SupportedPrograms):
        socket = self.sockets.get(program)

        if socket:
            socket.toggle()

    @staticmethod
    def show_env_ui():
        import customtkinter as ctk

        root = ctk.CTk()

        #Set Env Editor
        root.geometry("600x800")             
        env_editor_frame = EnvEditorUI(root, TxDefiToolKit.APP_NAME, TxDefiToolKit.PROFILE_NAME)
        env_editor_frame.pack(fill="both", expand=True)
  
        env_editor_frame.load_values() #Loads default .env values

        root.mainloop()

    def run(self):
        for socket in self.sockets.values():
            time.sleep(.5)
            socket.start() 
 
        self.risk_assessor.start()
        self.wallet_tracker.start()
        self.market_manager.start()
        self.trades_manager.start()        
        self.solana_rpc_api.start()   
        self.token_accounts_monitor.start()
        self.cancel_event.wait()

    def shutdown(self):
        for socket in self.sockets.values():
            socket.stop() 
  
        self.wallet_tracker.stop()
        self.market_manager.stop()        
        self.trades_manager.stop()          
        self.solana_rpc_api.stop()   
        self.risk_assessor.stop()
        self.cancel_event.set() 
        
