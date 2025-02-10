import os
from pathlib import Path
TEMP_SHORT_FOLDER = "C:\\TempVC"

def create_temp_folder(input_folder:str) -> bool:
    """This will create a temporary junction folder
    Arg:
        input_folder: the complete path for the folder that needs shorten
            No need for quotes
    return:
        true to be success
    """
    
    # This only works in Windows system.
    if os.name != "nt":
        return False

    # Remove old junction
    if Path(TEMP_SHORT_FOLDER).exists():
        os.remove(TEMP_SHORT_FOLDER)
    
    r = os.system(f"mklink /j {TEMP_SHORT_FOLDER} \"{input_folder}\"")
    if r == 0:
        return True
    else:
        return False

def remove_temp_folder():
    os.remove(TEMP_SHORT_FOLDER)

remove_temp_folder()
