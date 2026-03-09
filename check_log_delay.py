"""
ESO Chat.log 쓰기 지연 측정 도구.
실행 후 인게임에서 채팅 입력 → 콘솔에서 지연 시간 확인.

사용법: python check_log_delay.py "C:/Users/.../Documents/Elder Scrolls Online/live/Logs/Chat.log"
"""
import os, sys, time

log_path = sys.argv[1] if len(sys.argv) > 1 else "Chat.log"

print(f"감시 중: {log_path}")
print("인게임에서 채팅 입력 후 엔터 → 지연 시간이 여기 표시됩니다\n")

try:
    last_size  = os.path.getsize(log_path)
    last_mtime = os.path.getmtime(log_path)
except FileNotFoundError:
    print("파일 없음")
    sys.exit(1)

input_time = None
while True:
    try:
        stat = os.stat(log_path)
        if stat.st_size > last_size or stat.st_mtime != last_mtime:
            detected = time.perf_counter()
            if input_time:
                delay = detected - input_time
                print(f"  파일 변경 감지! 지연: {delay:.2f}초")
                input_time = None
            else:
                print(f"  파일 변경 감지 (입력 시간 미기록)")
            last_size  = stat.st_size
            last_mtime = stat.st_mtime
    except Exception:
        pass
    time.sleep(0.05)
