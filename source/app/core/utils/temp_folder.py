import os
from pathlib import Path

class TempFolder():
    temp_folder = "C:\\TempVC"
    folder_created = False
    def __init__(self):
        if Path(self.temp_folder).exists():
            self.folder_created = True
    
    def create_temp_folder(self, input_file_or_folder:str) -> list[bool, str]:
        """This will create a temporary junction folder
        Arg:
            input_file: the complete path or file that needs shortening
                No need for quotes
        return:
            true to be success
        """
        # This only works in Windows system.
        if os.name != "nt":
            return False, None

        file_name = ""
        path = Path(input_file_or_folder)
        if path.is_file():
            file_name = path.name
            path = path.parent
            
        # Remove old junction
        if Path( self.temp_folder ).exists():
            os.remove(self.temp_folder)
            self.folder_created = False
        
        r = os.system(f"mklink /j \"{path.absolute()}\"")
        if r == 0:
            self.folder_created = True
            return True, str(path / file_name)
        else:
            return False, None

    def remove_temp_folder(self):
        if Path(self.temp_folder).exists():
            os.remove(self.temp_folder)
        self.folder_created = False