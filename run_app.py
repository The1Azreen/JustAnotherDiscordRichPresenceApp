import subprocess
import sys
import os

REQUIREMENTS = "requirements.txt"


def check_and_install_requirements():
    if not os.path.exists(REQUIREMENTS):
        print(f"{REQUIREMENTS} not found!")
        sys.exit(1)
    try:
        import pkg_resources
        with open(REQUIREMENTS) as f:
            required = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        installed = {pkg.key for pkg in pkg_resources.working_set}
        missing = [pkg for pkg in required if pkg.split('==')[0].lower() not in installed]
        if missing:
            print(f"Installing missing packages: {', '.join(missing)}")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', *missing])
        else:
            print("All required packages are already installed.")
    except ImportError:
        print("pkg_resources not found. Installing all requirements...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS])

def main():
    check_and_install_requirements()
    subprocess.call([sys.executable, 'main.py'])

if __name__ == "__main__":
    main()
