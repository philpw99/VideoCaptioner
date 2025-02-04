import re
test = "abcd<think>this is the <translate>aw</translate> result</think>ass"

out = re.sub(r"<think>.*?</think>", " ", test)
print (out)

