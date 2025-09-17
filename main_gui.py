import asyncio
from TxDefi.TxDefiToolKit import TxDefiToolKit
from TxDefi.Data.TradingDTOs import *
from TxDefi.UI.MainUi import MainUi

async def main():    
    program_executor = TxDefiToolKit(True)
    
    main_gui = MainUi(program_executor, is_muted=True)

    main_gui.show_modal()

asyncio.run(main())