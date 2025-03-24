import os
import time
import subprocess
import sys
import random
import itertools

## conf area

frame_per_second = 30
fps_sampling_count = frame_per_second * 2
wait_enter = False
loop_play = False
random_delay_max = 0
stdout_byte_rate = 0
stdout_byte_rate_interval = 1

## 

# 获取当前脚本所在的目录
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
# 设置 frames-ascii 文件夹路径
FRAMES_DIR = os.path.join(SCRIPT_DIR, 'frames-ascii')

# 启动 mpv 播放器
#subprocess.Popen(['mpv', '--audio-device=alsa', 'bad_apple.mp4'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def main():

    print(f"The directory of the currently executing script is: {SCRIPT_DIR}")
    
    interval = 1 / frame_per_second
    T_STDOUT = ThrottledStdout(stdout_byte_rate, stdout_byte_rate_interval) if stdout_byte_rate > 0 else sys.stdout
    
    # 读取所有帧文件并存储在内存中
    frames = []
    for filename in sorted(os.listdir(FRAMES_DIR)):
        file_path = os.path.join(FRAMES_DIR, filename)
        
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                frames.append(f.read())  # 将每一帧存储到列表中
    
    frame_quantity = len(frames)
    print(f"loaded {frame_quantity} frames")

    if wait_enter:
        input("press enter to start playing...")

    # 启动 soc play 播放器
    subprocess.Popen(['play', '-q', 'bad_apple.mp3'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    next_loop_start_time = time.perf_counter()
    skip_frames_counter = 0

    cost_time = 0

    frame_tick_record = [next_loop_start_time - interval * fps_sampling_count] * fps_sampling_count
    frame_tick_record_loop_index = 0
    
    # 播放所有帧

    print(ANSI.CLEAR_SCREEN, ANSI.CURSOR_HOME, ANSI.HIDE_CURSOR, end='', sep='')

    frame_index = 0
    while loop_play or frame_index < frame_quantity:
        skipped_frame_count = 1

        frame = frames[frame_index % frame_quantity]

        # 打印当前帧内容

        frame_start_time = time.perf_counter()

        frame_act_per_second = 1 / ((next_loop_start_time - min(frame_tick_record)) / fps_sampling_count)
        frame_tick_record[frame_tick_record_loop_index % fps_sampling_count] = next_loop_start_time
        frame_tick_record_loop_index += 1

        frame_info = f"frames: {frame_index + 1}/{frame_quantity}, fps: {frame_act_per_second:.2f}"
        time_info = f'times: {format_time(interval + frame_index * interval)}' 
        skip_frame_info = f'skip frames: {skip_frames_counter}, cost_time: {int(cost_time*1000000)}us, prop: {int(cost_time / interval * 100)}%'

        print(ANSI.CURSOR_HOME,
            frame, '\n' + ANSI.CLEAR_LINE,
            frame_info, '\n' + ANSI.CLEAR_LINE,
            time_info, '\n' + ANSI.CLEAR_LINE,
            skip_frame_info, '\n' + ANSI.CLEAR_LINE,
                sep='', end='', file=T_STDOUT
            )

        # random delay
        if random_delay_max > 0:
            time.sleep(abs(random.gauss(0, random_delay_max)) / frame_per_second)

        frame_end_time = time.perf_counter()
        cost_time = frame_end_time - frame_start_time
        
        # 计算剩余时间来确保每帧间隔一致
        frame_interval = next_loop_start_time - time.perf_counter()
        frame_interval_normalized = max(0.0, frame_interval)
        
        if frame_interval < 0:
            loose_frames = int(-frame_interval // interval)
            skipped_frame_count += loose_frames
            skip_frames_counter += loose_frames

        # 根据剩余时间进行休眠
        if frame_interval_normalized > 0:
            time.sleep(frame_interval_normalized)

        next_loop_start_time += interval * skipped_frame_count
        frame_index += skipped_frame_count

def format_time(seconds):
    # 分离整数部分和小数部分
    integer_part = int(seconds)
    decimal_part = seconds - integer_part

    # 计算分钟和秒
    minutes = integer_part // 60
    seconds = integer_part % 60

    # 格式化输出
    formatted_time = f"{minutes:02}:{seconds:02}.{int(decimal_part * 1000):03}"
    return formatted_time

class ANSI:
    ESC = "\x1b"

    # 文字样式
    RESET = ESC + "[0m"
    BOLD = ESC + "[1m"
    UNDERLINE = ESC + "[4m"

    # 颜色
    RED = ESC + "[31m"
    GREEN = ESC + "[32m"
    BLUE = ESC + "[34m"

    # 光标控制
    """显示光标"""
    SHOW_CURSOR = ESC + "[?25h"
    """隐藏光标"""
    HIDE_CURSOR = ESC + "[?25l"
    """光标移动到左上角"""
    CURSOR_HOME = ESC + "[H"

    # 屏幕控制
    """清屏"""
    CLEAR_SCREEN = ESC + "[2J"
    """清除光标所在行"""
    CLEAR_LINE = ESC + "[2K"

class ThrottledStdout:
    def __init__(self, byte_rate, interval=1):
        self.byte_rate = byte_rate  # 每秒钟允许输出的字节数
        self.interval = interval
        self.start_time = time.perf_counter()  # 上次写入的时间
        self.out_bytes_counter = 0

    def write(self, text):
        self.__write_all(text.encode('utf-8'))
        self.flush()
    
    def __write_all(self, buf):
        chunk_size = int(self.byte_rate * self.interval)
        sliced_chunks = [];
        for i in range(0, len(buf), chunk_size):
            sliced_chunks.append(buf[i:i+chunk_size])

        for chunk in sliced_chunks:
            current_time = time.perf_counter()
            esp_time = self.start_time + self.interval - current_time

            if esp_time <= 0:
                self.out_bytes_counter = 0
                self.start_time = current_time
            elif self.out_bytes_counter >= chunk_size:
                time.sleep(esp_time)

            self.__write_chunk(chunk)
            self.out_bytes_counter += len(chunk)

    def __write_chunk(self, chunk):
        sys.__stdout__.buffer.write(chunk)

    def flush(self):
        sys.__stdout__.flush()

try:
    main()
finally:
    print(ANSI.RESET)
