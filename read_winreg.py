import winreg
import sys


WORKLIST_FILEPATH = 'C:\\Users\\Tecan\\Documents\\gilson_app_files\\WORKLIST_FILEPATH.txt'
reg_path = r"Volatile Environment"
reg_key_val = r"WORKLIST_FILEPATH"

def query_registry(reg_path, reg_key_val):
    access_registry = winreg.ConnectRegistry(None,winreg.HKEY_CURRENT_USER) # If None, the local computer is used
    access_key = winreg.OpenKey(access_registry,reg_path)

    # Read the value.                      
    result = winreg.QueryValueEx(access_key, reg_key_val)

    # Close the handle object.
    winreg.CloseKey(access_key)

    # Return only the value from the resulting tuple (value, type_as_int).
    return result[0]

def check_reg_path_exists(reg_path):
    access_registry = winreg.ConnectRegistry(None,winreg.HKEY_CURRENT_USER) # If None, the local computer is used
    try:
        access_key = winreg.OpenKey(access_registry, reg_path)
        winreg.CloseKey(access_key)
        return True
    except EnvironmentError:
        return False


if __name__ == "__main__":
    if check_reg_path_exists(reg_path):
        filepath = query_registry(reg_path, reg_key_val)
        with open(WORKLIST_FILEPATH, 'w', encoding='utf-8') as f:
            f.write(filepath)
        print('new file path updated!')
