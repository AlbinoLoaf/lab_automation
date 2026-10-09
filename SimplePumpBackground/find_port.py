import serial.tools.list_ports
import platform

def find_port(device_id=None):
    """
    Scans available serial ports and returns (found, port_name).
    If device_id is provided, matches by serial number or description.
    """
    #if platform.system() == "Windows":
        # Hardcode the COM port for Windows
    #    return True, "COM14"
    ports = list(serial.tools.list_ports.comports())

    # Match by device_id if provided
    if device_id:
        for p in ports:
            if device_id in (p.serial_number or '') or device_id in (p.description or ''):
                return True, p.device

    # Prefer typical USB serial ports; avoid debug consoles
    for p in ports:
        name = (p.device or '').lower()
        desc = (p.description or '').lower()
        if ('usb' in name or 'usb' in desc) and 'debug' not in name and 'debug' not in desc:
            return True, p.device

    # Fallback: first available
    if ports:
        return True, ports[0].device
    return False, None