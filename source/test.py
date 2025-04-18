from PyQt5.QtCore import *
url = QUrl(r"\\temp\text.txt")
url.setScheme('smb')
print (url)
