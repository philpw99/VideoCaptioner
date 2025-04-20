import re
lrc_pattern = re.compile(
        r'\[(\d{2}):(\d{2}):(\d{1,2})\](.*)'
)
line = "[00:11:22]lyric line 1"

match = lrc_pattern.match(line)
print ( match.group(1))

