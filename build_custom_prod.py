import re
import os
import subprocess
from rich.console import Console

# Get PyPI production account token
PYPI_PROD_ACC = os.getenv('PYPI_PROD_ACC')
if not PYPI_PROD_ACC:
    raise EnvironmentError("Please set PYPI_PROD_ACC environment variable with your PyPI token")

console = Console()

def run_command(command):
    console.print(f"[cyan][Running][/cyan] {command}")
    
    env = os.environ.copy()
    if 'twine' in command:
        env.update({
            'TWINE_USERNAME': '__token__',
            'TWINE_PASSWORD': PYPI_PROD_ACC
        })
    
    process = subprocess.Popen(
        command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1,
        env=env
    )
    
    stdout, stderr = process.communicate()
    
    if stdout:
        console.print(stdout.strip())
    if stderr:
        console.print(f"[red]{stderr.strip()}[/red]")
    
    if process.returncode != 0:
        raise Exception(f"Command failed: {command}")

def increment_version(version_file='src/taoreg/version.py'):
    with open(version_file, 'r') as f:
        content = f.read()
    
    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', content)
    if version_match:
        current_version = version_match.group(1)
        major, minor, patch = map(int, current_version.split('.'))
        patch += 1
        new_version = f'{major}.{minor}.{patch}'
        
        new_content = content.replace(current_version, new_version)
        with open(version_file, 'w') as f:
            f.write(new_content)
            
        console.print(f"[green][Version][/green] {current_version} -> {new_version}")
        return new_version
    else:
        raise ValueError("Could not find version string in version.py")

def main():
    bootcli_path = 'src/taoreg/bootcli.py'
    original_content = None
    
    try:
        # Store original content
        with open(bootcli_path, 'r') as f:
            original_content = f.read()
            
        # Clean
        console.print("\n[yellow][Cleaning][/yellow] Removing old builds...")
        run_command("rm -rf build/ dist/ *.egg-info src/*.egg-info src/bittensor_registration.egg-info src/bittensor_registration_cli.egg-info")
        run_command("ls dist/ 2>/dev/null || echo 'dist directory is clean'")

        # Update import for production
        console.print("\n[yellow][Updating][/yellow] bootcli.py import statement...")
        modified_content = original_content.replace('import pcli', 'from . import pcli')
        with open(bootcli_path, 'w') as f:
            f.write(modified_content)

        # Version
        new_version = increment_version()

        # Build
        console.print("\n[yellow][Building][/yellow] Package...")
        run_command("python3 -m build")

        # Upload to Production PyPI
        console.print("\n[yellow][Uploading][/yellow] to Production PyPI...")
        run_command("python3 -m twine upload dist/* --verbose")

        console.print(f"\n[green][Success][/green] Version {new_version} built and uploaded to Production PyPI!")

    except Exception as e:
        console.print(f"\n[red][Error][/red] {str(e)}")
        return 1
    finally:
        # Revert import back to development version
        if original_content:
            console.print("\n[yellow][Reverting][/yellow] bootcli.py import statement...")
            with open(bootcli_path, 'w') as f:
                f.write(original_content)
            console.print("[green]Successfully reverted import statement[/green]")
    
    return 0

if __name__ == "__main__":
    exit(main())