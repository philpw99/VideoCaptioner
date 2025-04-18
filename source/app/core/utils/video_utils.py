import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import requests
from typing import Literal

from ..utils.logger import setup_logger
from PyQt5.QtCore import QObject

logger = setup_logger("video_utils")
qoVideo = QObject()  # for i18n

def video2audio(input_file: str, output_file: str = "", format: str = "copy", allow_running: list = [True], audio_track: int = 0 ) -> bool:
    """使用ffmpeg将视频转换为音频"""    
    if not check_ffmpeg_available():
        logger.error("ffmpeg not available to transcode audio.")
        return False
    # 创建output目录
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    if format == "copy":
        # copy only
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-map', '0:a:'+str(audio_track),    # The chosen audio track
            '-c', 'copy',
            '-y',
            output_file
        ]
    else:
        # encode to whatever format
        cmd = [
            'ffmpeg',
            '-i', input_file,
            '-map', '0:a:'+str(audio_track),
            '-ac', '1',
            '-acodec', format,      # can be aac, mp3 ...etc
            '-ar', '16000',
            '-af', 'aresample=async=1',  # 处理音频同步问题
            '-y',
            output_file
        ]

    logger.info(f"转换为音频执行命令: {' '.join(cmd)}")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout= subprocess.PIPE,
            stderr= subprocess.STDOUT,
            stdin= subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='ignore',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 等待结束或者中途停止
        start_output = False
        while process.poll() is None:
            output = process.stdout.readline()
            if output:
                if output.startswith("Stream mapping:"):
                    start_output = True
                if start_output:
                    logger.info(output.strip())
            if not allow_running[0]:
                # Tell ffmpeg to quit
                process.terminate()
                logger.error("ffmpeg 执行音频转换时中断")
                return

        # 获取所有输出和错误信息
        process.communicate()
                
        if allow_running[0] and process.returncode == 0 and Path(output_file).is_file():
            return True
        else:
            logger.error("音频转换失败")
            return False
    except Exception as e:
        logger.exception(f"音频转换出错: {str(e)}")
        return False


def check_cuda_available() -> bool:
    """检查CUDA是否可用"""
    logger.info("检查CUDA是否可用")
    try:
        # 首先检查ffmpeg是否支持cuda
        result = subprocess.run(
            ['ffmpeg', '-hwaccels'], 
            capture_output=True, 
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,

        )
        if 'cuda' not in result.stdout.lower():
            logger.info("CUDA不在支持的硬件加速器列表中")
            return False
            
        # 进一步检查CUDA设备信息
        result = subprocess.run(
            ['ffmpeg', '-hide_banner', '-init_hw_device', 'cuda'], 
            capture_output=True, 
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # 如果stderr中包含"Cannot load cuda" 或 "Failed to load"等错误信息，说明CUDA不可用
        if any(error in result.stderr.lower() for error in ['cannot load cuda', 'failed to load', 'error']):
            logger.info("CUDA设备初始化失败")
            return False
            
        logger.info("CUDA可用")
        return True
        
    except Exception as e:
        logger.exception(f"检查CUDA出错: {str(e)}")
        return False


def add_subtitles(
        input_file: str,
        subtitle_file: str,
        output: str,
        duration: int,
        input_width: int = None,
        input_height: int = None,
        output_width: int = None,
        output_height: int = None,
        quality: Literal[
            'ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium', 'slow', 'slower', 'veryslow'] = 'medium',
        vcodec: str = 'libx264',
        soft_subtitle: bool = False,
        portrait: bool = False,
        logo: str = None,
        vertical_offset: int = 0,
        crf: int = 23,
        zoom_video: int = 100,
        zoom_subtitle: int = 100,
        blur_background = False,
        progress_callback: callable = None,
        allow_running: list = [True],
) -> None:
    """ Add subtitles to videos by hard coding method.
    """
    
    assert Path(input_file).is_file(), qoVideo.tr("输入文件不存在")
    assert Path(subtitle_file).is_file(), qoVideo.tr("字幕文件不存在")
    
    if not check_ffmpeg_available():
        logger.error("ffmpeg not available.")
        return
    
    # 移动到临时文件  Fix: 路径错误
    temp_dir = Path(tempfile.gettempdir()) / "VideoCaptioner"
    temp_dir.mkdir(exist_ok=True)
    output_file = Path(output)
    
    temp_subtitle = temp_dir / ( "temp_subtitle" + Path(subtitle_file).suffix )   # could be .srt, .ass or .vtt
    shutil.copy2(subtitle_file, temp_subtitle)
    subtitle_file = str(temp_subtitle)

    # 如果是WebM格式，强制使用硬字幕
    if output_file.suffix.lower() == '.webm':
        soft_subtitle = False
        logger.info("WebM格式视频，强制使用硬字幕")

    if soft_subtitle:
        # 添加软字幕
        if output_file.suffix.lower() == '.mp4':
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-i', subtitle_file,
                '-map', '0',    # 复制所有流
                '-c:v', 'copy',
                '-c:a', 'copy',
                '-c:s', 'mov_text',
                output,
                '-y'
            ]
        else:   # 其他格式 most likely .mkv
            cmd = [
                'ffmpeg',
                '-i', input_file,
                '-i', subtitle_file,
                '-sub_charenc', 'UTF-8',
                '-map', '0',    # 复制视频所有流
                '-map', '1',    # 复制字幕文件所有流
                '-c', 'copy',
                output,
                '-y'
            ]
        logger.info(f"添加软字幕执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            check=True, 
            encoding='utf-8', 
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
            )
    else:
        # 添加硬字幕
        logger.info("使用硬字幕")
        subtitle_file = Path(subtitle_file).as_posix().replace(':', r'\:')
        if Path(output).suffix.lower() == '.webm':
            vcodec = 'libvpx-vp9'
            logger.info("WebM格式视频，使用libvpx-vp9编码器")

        # 检查CUDA是否可用
        use_cuda = check_cuda_available()
        cmd = ['ffmpeg']
        if use_cuda:
            logger.info("使用CUDA加速")
            cmd.extend(['-hwaccel', 'cuda'])
            if vcodec == 'libx264':
                vcodec = 'h264_nvenc'
            elif vcodec == 'libx265':
                vcodec = 'hevc_nvenc'
                
        cmd.extend([
            '-i', input_file,
        ])
        
        # print (f"portrait: {portrait}, background{background}\n" \
        #    +f"output_width: {output_width}, output_height: {output_height}, duration{duration}")
        
        
        if portrait and input_width > input_height:
            # Landscape convert to portrait mode.
            # output_height = 1920, output_width = 1080, squeeze_height = 606
            squeeze_height = int( output_width * output_width / output_height /2) * 2   # The original video's height after rotating.
            # Zoom of video and subtitles, all need to be multiple of 2
            output_width_subtitle = int(output_width * zoom_subtitle // 200) * 2
            output_height_subtitle = int(squeeze_height * zoom_subtitle // 200) * 2
            squeeze_height_subtitle = int( squeeze_height * zoom_subtitle // 200 ) * 2
            subtitle_x = (output_width - output_width_subtitle) //2
            subtitle_y = (output_height - squeeze_height_subtitle) // 2
            
            output_width_video = int(output_width * zoom_video // 200) * 2
            output_height_video = int(squeeze_height * zoom_video // 200) * 2
            squeeze_height_video = int(squeeze_height * zoom_video // 200) * 2
            video_x = (output_width - output_width_video) // 2
            video_y = (output_height - output_height_video) // 2
            
            if blur_background:
                # Blur background for videos that changed orientation or zoomed out.
                bg_str = f"[0:v]avgblur=sizeX=40:sizeY=40,scale={output_width}x{output_height}:flags=fast_bilinear[bg];" 
            else:
                # Just black background
                bg_str = f"color=d={duration}:c=black@0:s={output_width}x{output_height}[bg];"
            
            if logo:
                cmd.extend(['-i', logo])

                # With logo
                vf = bg_str + f"[1:v]trim=0:{duration},scale={output_width}:{output_height}[logo];" \
                    + f"color=d={duration}:c=black@0:s={output_width_subtitle}x{squeeze_height_subtitle}," \
                    + f"subtitles='{subtitle_file}':alpha=1[sub];[0:v]scale={output_width_video}:{squeeze_height_video}[fg];" \
                    + f"[bg][fg]overlay={video_x}:{video_y}[out];[out][logo]overlay[outlogo];" \
                    + f"[outlogo][sub]overlay={subtitle_x}:{subtitle_y+vertical_offset},setsar=1"
                
            else:   # Without logo
                vf = bg_str + f"color=d={duration}:c=black@0:s={output_width_subtitle}x{squeeze_height_subtitle}," \
                    + f"subtitles='{subtitle_file}':alpha=1[sub];[0:v]scale={output_width_video}:{squeeze_height_video}[fg];" \
                    + f"[bg][fg]overlay={video_x}:{video_y}[out];[out][sub]overlay={subtitle_x}:{subtitle_y+vertical_offset},setsar=1"
        
        elif not portrait and input_width < input_height:
            # Landscape mode. Convert from portrait video.
            # output_height = 1080, output_width = 1920, squeeze_width = 607
            squeeze_width = int( output_height * output_height / output_width /2) * 2   # The original video's height after rotating.
            # Zoom of video and subtitles, all need to be multiple of 2
            output_width_subtitle = int(squeeze_width * zoom_subtitle // 200) * 2
            output_height_subtitle = int(output_height * zoom_subtitle // 200) * 2
            squeeze_width_subtitle = int( squeeze_width * zoom_subtitle // 200 ) * 2
            subtitle_x = (output_width - squeeze_width_subtitle) //2
            subtitle_y = (output_height - output_height_subtitle) // 2
            
            output_width_video = int(squeeze_width * zoom_video // 200) * 2
            output_height_video = int(output_height * zoom_video // 200) * 2
            squeeze_width_video = int(squeeze_width * zoom_video // 200) * 2
            video_x = (output_width - output_width_video) // 2
            video_y = (output_height - output_height_video) // 2

            if blur_background:
                # Blur background for videos that changed orientation or zoomed out.
                bg_str = f"[0:v]avgblur=sizeX=40:sizeY=40,scale={output_width}x{output_height}:flags=fast_bilinear[bg];" 
            else:
                # Just black background
                bg_str = f"color=d={duration}:c=black@0:s={output_width}x{output_height}[bg];"

            if logo: 
                cmd.extend(['-i', logo])
                # With logo
                vf = bg_str + f"[1:v]trim=0:{duration},scale={output_width}:{output_height}[logo];" \
                    + f"color=d={duration}:c=black@0:s={squeeze_width_subtitle}x{output_height_subtitle}," \
                    + f"subtitles='{subtitle_file}':alpha=1[sub];[0:v]scale={squeeze_width_video}:{output_height_video}[fg];" \
                    + f"[bg][fg]overlay={video_x}:{video_y}[out];[out][logo]overlay[outlogo];" \
                    + f"[outlogo][sub]overlay={subtitle_x}:{subtitle_y+vertical_offset},setsar=1"
                
            else:   # Without logo
                vf = bg_str + f"color=d={duration}:c=black@0:s={squeeze_width_subtitle}x{output_height_subtitle}," \
                    + f"subtitles='{subtitle_file}':alpha=1[sub];[0:v]scale={squeeze_width_video}:{output_height_video}[fg];" \
                    + f"[bg][fg]overlay={video_x}:{video_y}[out];[out][sub]overlay={subtitle_x}:{subtitle_y+vertical_offset},setsar=1"
            
        else:
            # Landscape or Portrait mode. No convert
            # Zoom of video and subtitles, all need to be multiple of 2
            output_width_subtitle = int(output_width * zoom_subtitle // 200) * 2
            output_height_subtitle = int(output_height * zoom_subtitle // 200) * 2
            subtitle_x, subtitle_y = 0, 0

            if logo:
                # With logo
                cmd.extend(['-i', logo])
                
                vf =  f"[1:v]trim=0:{duration},scale={output_width}:{output_height}[logo];" \
                    + f"color=d={duration}:c=black@0:s={output_width_subtitle}x{output_height_subtitle}," \
                    + f"subtitles='{subtitle_file}':alpha=1[sub];" \
                    + f"[0:v][logo]overlay[outlogo];" \
                    + f"[outlogo][sub]overlay={subtitle_x}:{subtitle_y+vertical_offset},setsar=1"
            else:
                # No logo
                f"color=d={duration}:c=black@0:s={output_width_subtitle}x{output_height_subtitle}," \
                + f"subtitles='{subtitle_file}':alpha=1[sub];[0:v][sub]overlay={subtitle_x}:{subtitle_y+vertical_offset},setsar=1"

        cmd.extend([
            '-map', '0',    # 复制所有流
            '-map', '-0:v',  # 排除源视频流，免得生成两个视频流
            '-acodec', 'copy',
            '-vcodec', vcodec,
            '-c:s', 'copy', # 复制其它的字幕流
            '-preset', quality
        ])

        # Video quality control
        if use_cuda:
            # For nvidia encoder.
            cmd.extend(['-cq', crf])
        else:
            # For libx264 or libx265.
            cmd.extend(['-crf', crf])

        cmd.extend([
            '-filter_complex', q(vf),
            '-y',  # 覆盖输出文件
            output
        ])
        
        cmd_str = subprocess.list2cmdline(cmd)
        cmd_str = cmd_str.replace('\\"', '"')  # Fix the quote problem of video filters
        logger.info(f"添加硬字幕执行命令: {cmd_str}")

        try:
            if os.name == 'nt':
                # In windows system, the -filter_complex need quoting.
                process = subprocess.Popen(
                    cmd_str, 
                    stdout=subprocess.PIPE, 
                    stdin=subprocess.PIPE,
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                )
            else:
                process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stdin=subprocess.PIPE,
                    stderr=subprocess.STDOUT, 
                    text=True, 
                    encoding='utf-8',
                    errors='replace',
                    creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0,
                )
                

            # 实时读取输出并调用回调函数
            total_duration = None
            current_time = 0

            while process.poll() is None:
                output_line = process.stdout.readline().strip()
                if not output_line or not progress_callback:
                    continue

                if total_duration is None:
                    duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', output_line)
                    if duration_match:
                        h, m, s = map(float, duration_match.groups())
                        total_duration = h * 3600 + m * 60 + s
                        logger.info(f"视频总时长: {total_duration}秒")

                # 解析当前处理时间
                time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', output_line)
                if time_match:
                    logger.info(output_line)
                    h, m, s = map(float, time_match.groups())
                    current_time = h * 3600 + m * 60 + s

                # 计算进度百分比
                if total_duration:
                    progress = (current_time / total_duration) * 100
                    progress_callback(f"{round(progress)}", qoVideo.tr("正在合成"))
                
                # 强行终止
                if not allow_running[0]:
                    logger.error("视频合成强行中止")
                    process.communicate(input="q", timeout=5)
                    
                    raise Exception(qoVideo.tr("视频合成强行中止"))

            if progress_callback:
                progress_callback("100", qoVideo.tr("合成完成"))
            # 检查进程的返回码
            if process.returncode != 0:
                logger.error(f"视频合成失败。")
                raise Exception(process.returncode)
            logger.info("视频合成完成")

        except Exception as e:
            logger.exception(f"关闭 FFmpeg: {str(e)}")
            if process and process.poll() is None:  # 如果进程还在运行
                process.kill()  # 如果进程没有及时终止，强制结束它
            raise
        finally:
            # 删除临时文件
            if temp_subtitle.exists():
                temp_subtitle.unlink()

def get_video_info(filepath: str, thumbnail_path: str = "", post_url: str = None) -> dict:
    try:
        cmd = ["ffmpeg", "-i", filepath]
        logger.info(f"获取视频信息执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
        info = result.stderr

        video_info = {
            'file_name': Path(filepath).stem,
            'file_path': str( Path(filepath).parent ),
            'duration_seconds': 0,
            'bitrate_kbps': 0,
            'video_codec': '',
            'width': 0,
            'height': 0,
            'fps': 0,
            'audio_codec': '',
            'audio_sampling_rate': 0,
            'thumbnail_path': '',
            'audio_tracks': None,
        }

        # 提取时长
        if duration_match := re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', info):
            hours, minutes, seconds = map(float, duration_match.groups())
            video_info['duration_seconds'] = hours * 3600 + minutes * 60 + seconds
            logger.info(f"视频时长: {video_info['duration_seconds']}秒")

        # 提取比特率
        if bitrate_match := re.search(r'bitrate: (\d+) kb/s', info):
            video_info['bitrate_kbps'] = int(bitrate_match.group(1))

        # 提取视频流信息
        if video_stream_match := re.search(r'Stream #\d+:\d+.*Video: (\w+).*?, (\d+)x(\d+).*?, ([\d.]+) (?:fps|tb)',
                                           info, re.DOTALL):
            video_info.update({
                'video_codec': video_stream_match.group(1),
                'width': int(video_stream_match.group(2)),
                'height': int(video_stream_match.group(3)),
                'fps': float(video_stream_match.group(4))
            })
            
            if thumbnail_path:
                if post_url:
                    # If there is a post_url from imdb, use it.
                    if post_url and not post_url.endswith(".jpg"):
                        # save and convert the picture.
                        filename = post_url.split('/')[-1]
                        save_path = Path(thumbnail_path).parent / filename
                        img_data = requests.get(post_url, headers = {'user-agent': 'VideoCaptioner/3.5.4'}).content
                        with open(save_path, 'wb') as handler:
                            handler.write(img_data)
                        # Convert the image to jpg format
                        from PIL import Image
                        image = Image.open(save_path)
                        image.convert("RGB").save(thumbnail_path)
                    else:
                        # Save as thumbnail.jpg directly.
                        img_data = requests.get(post_url, headers = {'user-agent': 'VideoCaptioner/3.5.4'}).content
                        with open(thumbnail_path, 'wb') as handler:
                            handler.write(img_data)
                    video_info['thumbnail_path'] = thumbnail_path
                elif extract_thumbnail(filepath, video_info['duration_seconds'] * 0.3, thumbnail_path):
                    # Get thumbnail from ffmpeg extraction.
                    video_info['thumbnail_path'] = thumbnail_path
        else:
            video_info['thumbnail_path'] = thumbnail_path
            logger.warning("未找到视频流信息")

        # 提取音频流信息
        if audio_stream_match := re.search(r'Stream #\d+:\d+.*Audio: (\w+).* (\d+) Hz', info):
            video_info.update({
                'audio_codec': audio_stream_match.group(1),
                'audio_sampling_rate': int(audio_stream_match.group(2))
            })

        # 提取音频流语言列表信息
        if audio_track_match := re.findall(r"Stream #\d+:(\d+\(.+?\)): Audio:", info, re.DOTALL):
            video_info['audio_tracks'] = audio_track_match     # It's a list like ["1(eng)", "2(fra)", "3(ita)"]

        return video_info
    except Exception as e:
        logger.exception(f"获取视频信息时出错: {str(e)}")
        return {k: '' if isinstance(v, str) else 0 for k, v in video_info.items()}


def extract_thumbnail(video_path: str, seek_time: float, thumbnail_path: str) -> bool:
    """
    使用 FFmpeg 提取视频缩略图
    
    :param video_path: 输入视频文件的路径
    :param seek_time: 提取缩略图的时间点（秒）
    :param thumbnail_path: 输出缩略图文件的路径
    :return: True 表示成功，False 表示失败
    """    
    if not Path(video_path).is_file():
        logger.error(f"视频文件不存在: {video_path}")
        return False

    if not check_ffmpeg_available():
        logger.error(f"ffmpeg not available.")
        return False

    try:
        timestamp = f"{int(seek_time // 3600):02}:{int((seek_time % 3600) // 60):02}:{seek_time % 60:06.3f}"
        # 确保输出目录存在
        Path(thumbnail_path).parent.mkdir(parents=True, exist_ok=True)

        # 转换路径为合适的格式
        video_path = Path(video_path).as_posix()
        thumbnail_path = Path(thumbnail_path).as_posix()

        cmd = [
            "ffmpeg",
            "-ss", timestamp,
            "-i",
            video_path,
            "-vframes", "1",
            "-q:v", "2",
            "-y",
            thumbnail_path
        ]
        logger.info(f"执行命令: {' '.join(cmd)}")
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            encoding='utf-8', 
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        success = result.returncode == 0
        return success

    except Exception as e:
        logger.exception(f"提取缩略图时出错: {str(e)}")
        return False

def q(text):
    """Quote a string for use in a shell command."""
    return '"' + text + '"'

def check_ffmpeg_available():
    return True if shutil.which("ffmpeg") else False
    # try:
    #     process = subprocess.run( ["ffmpeg", "-version"], capture_output=True, text=True)
    #     return True
    # except FileNotFoundError:
    #     return False

if __name__ == "__main__":
    video_path = r"C:\Users\weifeng\Videos\example_video.mp4"
    thumbnail_path = "e:/example_thumbnail.jpg"
    success = extract_thumbnail(video_path, 2, thumbnail_path)
