import asyncio
import bittensor as bt
from substrateinterface import Keypair
import json
import base64
from typing import Dict
import requests
import socketio
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.status import Status
from rich.table import Table

# Constants
SERVER_URL = "http://64.247.206.58:16505"  
SOCKET_URL = SERVER_URL
DEFAULT_VALUES = {
    'netuid':  "",
    'max_fee': "",
    'coldkey_mnemonic': "",
    'hotkey_mnemonic':  "",
}
class SocketManager:
    def __init__(self, console):
        self.console = console
        self.sio = socketio.Client()
        self.connected = False
        self.process_name = None
        self.setup_handlers()
        
    def setup_handlers(self):
        @self.sio.on('connect')
        def on_connect():
            self.connected = True
            self.console.print("[green]Connected to service[/green]")
            
        @self.sio.on('log')
        def on_log(data):
            if data.get('process') == self.process_name:
                self.console.print(f"[bold cyan]{data['message']}[/bold cyan]")
            
    def connect(self, netuid=None, hotkey=None):
        try:
            if netuid and hotkey:
                self.process_name = f"reg_{netuid}_{hotkey}"
            if not self.connected:
                self.sio.connect(SOCKET_URL)
        except Exception:
            self.console.print("[red]Connection error. Please try again later.[/red]")
            
    def disconnect(self):
        if self.connected:
            self.sio.disconnect()

class EnhancedRegistrationCLI:
    def __init__(self):
        self.console = Console()
        self.socket_manager = SocketManager(self.console)
        self.POLL_INTERVAL = 5
        
    def show_welcome(self):
        self.console.print(Panel("Bittensor Registration Terminal", style="green"))
        self.console.print("\nThe most advanced registration system for Bittensor network\n")

    def show_menu(self) -> int:
        self.console.print("\n[bold cyan]Available Options:[/bold cyan]")
        options = {
            "1": "New Registration",
            "2": "Registration Status",
            "3": "Delete Registration Request",
            "4": "Exit"
        }
        for num, option in options.items():
            self.console.print(f"[white]{num}.[/white] {option}")
            
        choice = Prompt.ask("\nEnter your choice", choices=["1", "2", "3", "4"], default="1")
        return int(choice)

    # async def get_registration_details(self, for_status=False) -> Dict:
    #     """Get and validate registration details"""
    #     self.console.print("\n[bold cyan]Enter Registration Details[/bold cyan]")
        
    #     while True:  # Keep asking until valid inputs are provided
    #         try:
    #             inputs = {
    #                 'netuid': int(Prompt.ask("Enter netuid", default="36")),
    #                 'coldkey_mnemonic': Prompt.ask("Enter coldkey mnemonic", 
    #                     default=DEFAULT_VALUES['coldkey_mnemonic']) if not for_status else None,
    #                 'hotkey_mnemonic': Prompt.ask("Enter hotkey mnemonic", 
    #                     default=DEFAULT_VALUES['hotkey_mnemonic']),
    #                 'max_fee': float(Prompt.ask("Enter max fee (τ)", default="0.1")) if not for_status else None
    #             }
                
    #             # Validate hotkey mnemonic
    #             if not self.validate_mnemonic(inputs['hotkey_mnemonic'], "hotkey"):
    #                 self.console.print("[yellow]Invalid hotkey mnemonic. Please try again.[/yellow]")
    #                 continue
                
    #             return inputs
                
    #         except ValueError as e:
    #             self.console.print(f"[red]Invalid input: {str(e)}. Please try again.[/red]")
    #         except Exception as e:
    #             self.console.print(f"[red]Error: {str(e)}. Please try again.[/red]")
    
    async def get_registration_details(self, for_status=False) -> Dict:
        """Get registration details using wallet"""
        self.console.print("\n[bold cyan]Enter Registration Details[/bold cyan]")
        
        try:
            inputs = {
                'netuid': int(Prompt.ask("Enter netuid")),
                'max_fee': float(Prompt.ask("Enter max fee (τ)")) if not for_status else None
            }
            
            wallet_name = Prompt.ask("Enter wallet name", default="default")
            hotkey_name = Prompt.ask("Enter hotkey name", default="default")
            
            wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
            return {
                **inputs,
                'wallet': wallet,
                'coldkey_ss58': wallet.coldkey.ss58_address,
                'hotkey_ss58': wallet.hotkey.ss58_address
            }
                
        except Exception as e:
            self.console.print(f"[red]Error: {str(e)}[/red]")
            raise
                

    def validate_mnemonic(self, mnemonic: str, key_type: str = "key") -> bool:
        """Validate if a mnemonic phrase is valid"""
        try:
            Keypair.create_from_mnemonic(mnemonic)
            return True
        except Exception:
            return False
        
    async def check_registration_status(self, netuid: int, hotkey_ss58: str):
        with Status("[bold green]Checking status...", spinner="dots") as status:
            response = requests.post(f"{SERVER_URL}/checkStatus", json={
                'netuid': netuid,
                'hotkey': hotkey_ss58
            })
            
            if response.status_code == 200:
                data = response.json()
                if data.get('error_code') == 1:
                    self.console.print("[yellow]No active request found[/yellow]")
                else:
                    self.console.print(f"[cyan]Status: {data.get('message')}[/cyan]")
                    self.socket_manager.connect(netuid, hotkey_ss58)
                    try:
                        while True:
                            await asyncio.sleep(1)
                    except KeyboardInterrupt:
                        self.console.print("\n[yellow]Monitoring stopped[/yellow]")
                    finally:
                        self.socket_manager.disconnect()

    async def delete_registration(self, netuid: int, hotkey_ss58: str):
        with Status("[bold yellow]Deleting registration request...", spinner="dots"):
            response = requests.post(f"{SERVER_URL}/deleteReg", json={
                'netuid': netuid,
                'hotkey': hotkey_ss58
            })
            
            if response.status_code == 200:
                data = response.json()
                self.console.print(f"[cyan]{data.get('message')}[/cyan]")
            else:
                self.console.print("[red]Failed to delete registration[/red]")

    async def main(self):
        self.console.clear()
        self.show_welcome()
        
        while True:
            try:
                choice = self.show_menu()

                if choice == 4:
                    break
                elif choice == 1:
                    import pcli
                    reg_cli = pcli.RegistrationCLI()
                    await reg_cli.main()
                elif choice == 2:
                    inputs = await self.get_registration_details(for_status=True)
                    await self.check_registration_status(
                        inputs['netuid'],
                        inputs['hotkey_ss58']
                    )
                else:
                    inputs = await self.get_registration_details(for_status=True)
                    if Confirm.ask("\nDelete this registration request?"):
                        await self.delete_registration(
                            inputs['netuid'],
                            inputs['hotkey_ss58']
                        )

                if not Confirm.ask("\nPerform another operation?"):
                    break

            except KeyboardInterrupt:
                if not Confirm.ask("\nContinue with another operation?"):
                    break
            except ValueError:
                self.console.print("[red]Enter a valid option (1-4)[/red]")
            except Exception as e:
                self.console.print(f"[red]Error: {str(e)}[/red]")
                if not Confirm.ask("\nTry again?"):
                    break

def main():
    try:
        cli = EnhancedRegistrationCLI()
        asyncio.run(cli.main())
    except KeyboardInterrupt:
        print("\nEnd.")
    except Exception:
        print("\Errored")

if __name__ == "__main__":
    main()