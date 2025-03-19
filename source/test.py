import re
info = """
Input #0, matroska,webm, from '.\\Sosyal Climbers 2025 1080p (DUAL) WEB-DL HEVC x265 5.1 BONE.mkv':
  Metadata:
    creation_time   : 2025-02-27T15:55:05.000000Z
    ENCODER         : Lavf61.7.100
  Duration: 01:43:34.08, start: -0.021000, bitrate: 2154 kb/s
  Stream #0:0: Video: hevc (Main), yuv420p(tv, bt709), 1920x1080 [SAR 1:1 DAR 16:9], 23.98 fps, 23.98 tbr, 1k tbn (default)
    Metadata:
      DURATION        : 01:43:34.083000000
  Stream #0:1(eng): Audio: aac (LC), 48000 Hz, 5.1, fltp (default)
    Metadata:
      title           : Surround
      DURATION        : 01:43:34.058000000
  Stream #0:2(fil): Audio: aac (LC), 48000 Hz, 5.1, fltp
    Metadata:
      title           : Surround
      DURATION        : 01:43:34.058000000
  Stream #0:3(eng): Subtitle: ass (ssa)
    Metadata:
      DURATION        : 01:41:25.829000000
  Stream #0:4(eng): Subtitle: ass (ssa)
    Metadata:
      title           : Dubtitle
      DURATION        : 01:41:25.621000000
  Stream #0:5(fil): Subtitle: ass (ssa)
    Metadata:
      title           : Forced
      DURATION        : 01:41:10.689000000
  Stream #0:6(fil): Subtitle: ass (ssa)
    Metadata:
      DURATION        : 01:41:25.329000000
  Stream #0:7(fil): Subtitle: ass (ssa)
"""


match = re.findall(r"Stream #\d+:(\d+\(.+?\)): Audio:", info, re.DOTALL)
if match:
    print(len(None))
    print(match)
else:
    print("no match")
