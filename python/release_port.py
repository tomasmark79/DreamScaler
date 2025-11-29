#!/usr/bin/env python3
"""
Utility pro uvolnění zablokovaného sériového portu
"""

import sys
import serial
import time

def release_port(port_name):
    """Pokusí se násilně otevřít a zavřít port"""
    print(f"Pokouším se uvolnit port {port_name}...")
    
    try:
        # Zkusit otevřít s různými nastaveními
        attempts = [
            {'baudrate': 115200, 'timeout': 0.1},
            {'baudrate': 9600, 'timeout': 0.1},
            {'exclusive': True, 'baudrate': 115200, 'timeout': 0.1},
        ]
        
        for i, params in enumerate(attempts, 1):
            try:
                print(f"\nPokus {i}/{len(attempts)}: {params}")
                ser = serial.Serial(port_name, **params)
                print(f"  ✓ Port otevřen")
                
                # Resetovat buffery
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                print(f"  ✓ Buffery vymazány")
                
                # Zavřít
                ser.close()
                print(f"  ✓ Port uzavřen")
                
                # Počkat chvíli
                time.sleep(0.5)
                
                # Ověřit že je zavřený
                if not ser.is_open:
                    print(f"\n✓ Port {port_name} byl úspěšně uvolněn!")
                    return True
                    
            except serial.SerialException as e:
                print(f"  ✗ Chyba: {e}")
            except Exception as e:
                print(f"  ✗ Neočekávaná chyba: {e}")
        
        print(f"\n✗ Nepodařilo se uvolnit port {port_name}")
        return False
        
    except Exception as e:
        print(f"✗ Kritická chyba: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Použití: python release_port.py <port>")
        print("Příklad: python release_port.py COM3")
        sys.exit(1)
    
    port = sys.argv[1]
    
    print("="*60)
    print("Utility pro uvolnění sériového portu")
    print("="*60)
    
    success = release_port(port)
    
    if success:
        print("\n" + "="*60)
        print("ÚSPĚCH - Port by měl být nyní k dispozici")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("SELHÁNÍ - Zkuste:")
        print("1. Odpojit a znovu připojit USB kabel")
        print("2. Restartovat PowerShell/CMD")
        print("3. Restartovat počítač")
        print("="*60)
        sys.exit(1)


if __name__ == '__main__':
    main()
