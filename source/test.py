import unicodedata as ud

text1 = u"обращаюсь"
text2 = u"中文试验"
text3 = "Straße"
text4 = "try the words"
text5 = u'سماوي يدور'
text6 = u"det forårsaker første"
text7 = u"кириллический"

for char in text7:
    print( ud.east_asian_width(char) )

