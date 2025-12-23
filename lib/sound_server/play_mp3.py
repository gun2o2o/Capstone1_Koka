import pygame
import time
import os

# 파일 이름 설정 (같은 폴더에 있어야 함)
music_file = "1.mp3"

def play_music(file_path):
    # 1. 파일이 진짜 있는지 확인
    if not os.path.exists(file_path):
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return

    # 2. 믹서 초기화
    pygame.mixer.init()
    
    # 3. 파일 불러오기
    try:
        pygame.mixer.music.load(file_path)
        print(f"재생 시작: {file_path}")
    except pygame.error as e:
        print(f"파일 로드 오류: {e}")
        return

    # 4. 재생
    pygame.mixer.music.play()

    # 5. 재생이 끝날 때까지 대기 (이게 없으면 소리가 나자마자 프로그램이 꺼짐)
    while pygame.mixer.music.get_busy():
        time.sleep(1)
    
    print("재생 완료!")

if __name__ == "__main__":
    play_music(music_file)