import pygame
import time
import os
import math
import struct

# ==========================================
# ⚙️ 설정값
# ==========================================
os.environ["SDL_VIDEODRIVER"] = "dummy"
VIDEO_DURATION = 3382.91  # 영상 총 길이 (초)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MP3_DIR = os.path.join(BASE_DIR, "mp3")
TIMELINE_FILE = os.path.join(BASE_DIR, "rasptimeline.txt")

# ==========================================
# 🎵 부팅음 생성 함수
# ==========================================
def make_tone(freq, duration):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buffer = bytearray()
    for i in range(n_samples):
        val = int(32767.0 * math.sin(2.0 * math.pi * freq * i / sample_rate))
        buffer += struct.pack('h', val)
    return pygame.mixer.Sound(buffer=buffer)

def play_startup_sound():
    print("📢 부팅음 재생: 도 -> 레 -> 미")
    tones = [261.63, 293.66, 329.63]
    for freq in tones:
        sound = make_tone(freq, 0.5)
        sound.play()
        time.sleep(0.6)

# ==========================================
# 📝 텍스트 파싱 (새로운 포맷 대응)
# ==========================================
def parse_timeline(filepath):
    events = []
    
    if not os.path.exists(filepath):
        print(f"❌ 오류: {filepath} 파일이 없습니다.")
        return []

    print(f"📂 타임라인 파일 로드 중...")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        # 주석(#)이나 빈 줄 건너뛰기
        if not line or line.startswith("#"): 
            continue

        # '|' 기준으로 나누기
        parts = line.split('|')
        if len(parts) < 2:
            continue

        # 1. 시간 파싱
        try:
            start_time = int(parts[0].strip())
        except ValueError:
            continue # 숫자가 아니면 패스

        # 2. 파일명/명령 파싱
        name_cmd = parts[1].strip()
        
        # STOP 명령인 경우
        if name_cmd.upper() == "STOP":
            events.append({'time': start_time, 'type': 'stop', 'raw': line})
            continue

        # 3. 옵션 파싱 (x2, 10s 등)
        loops = 0      # 기본 1회 재생 (pygame loops=0)
        limit = None   # 재생 시간 제한 없음
        
        if len(parts) > 2:
            opt = parts[2].strip().lower()
            if opt.startswith('x'):       # 예: x2
                try:
                    loops = int(opt.replace('x', '')) - 1
                except:
                    loops = 0
            elif opt.endswith('s'):       # 예: 12s
                try:
                    limit = int(opt.replace('s', ''))
                except:
                    limit = None

        events.append({
            'time': start_time,
            'type': 'play',
            'file': f"{name_cmd}.mp3",
            'loops': loops,
            'limit': limit,
            'raw': line
        })
    
    # 시간 순서대로 정렬
    events.sort(key=lambda x: x['time'])
    return events

# ==========================================
# 🚀 메인 실행 로직
# ==========================================
def main():
    # 버퍼 사이즈를 줄여 딜레이 최소화
    pygame.mixer.pre_init(44100, -16, 1, 2048)
    pygame.init()
    pygame.mixer.init()

    play_startup_sound()

    timeline = parse_timeline(TIMELINE_FILE)
    if not timeline:
        print("❌ 타임라인 데이터가 없습니다.")
        return

    print(f"✅ 총 {len(timeline)}개의 이벤트 로드 완료.")
    print(f"🔄 영상 싱크 시작 (총 길이: {VIDEO_DURATION}초)")

    while True:
        cycle_start_time = time.time()
        event_idx = 0
        current_limit_time = None
        
        print("🎬 --- New Cycle Start ---")

        while True:
            elapsed = time.time() - cycle_start_time
            
            if elapsed >= VIDEO_DURATION:
                pygame.mixer.music.stop()
                break

            # 재생 시간 제한 체크 (예: 12초만 재생)
            if current_limit_time and elapsed >= current_limit_time:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.fadeout(500)
                    print(f"   [Time: {elapsed:.1f}s] 지정 시간 종료 (Fadeout)")
                current_limit_time = None

            # 타임라인 이벤트 체크
            if event_idx < len(timeline):
                event = timeline[event_idx]
                
                if elapsed >= event['time']:
                    print(f"⏰ [{elapsed:.1f}초] {event['raw']}")
                    
                    if event['type'] == 'stop':
                        pygame.mixer.music.stop()
                        current_limit_time = None
                    
                    elif event['type'] == 'play':
                        file_path = os.path.join(MP3_DIR, event['file'])
                        if os.path.exists(file_path):
                            try:
                                pygame.mixer.music.load(file_path)
                                pygame.mixer.music.play(loops=event['loops'])
                                
                                if event['limit']:
                                    current_limit_time = elapsed + event['limit']
                                else:
                                    current_limit_time = None
                            except Exception as e:
                                print(f"❌ 재생 에러: {e}")
                        else:
                            print(f"❌ 파일 없음: {file_path}")
                    
                    event_idx += 1

            time.sleep(0.05) # 반응 속도를 위해 0.05초로 단축

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pygame.quit()