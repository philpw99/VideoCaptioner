text = "abcdefg"
if all(x in text for x in ["b","c","h"]):
    print ("good")
else:
    print("not")
