import json
import socket
import serial
import time
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

# --- 설정 구간 ---
# 1. 라즈베리파이 (스피커)
RPI_IP = "192.168.0.XX"  # 라즈베리파이 IP 주소!
RPI_PORT = 12345

# 2. 아두이노 (LED)
try:
    arduino = serial.Serial('COM3', 9600, timeout=1)
    time.sleep(2)
    print("✅ 아두이노 연결 성공")
except:
    arduino = None
    print("⚠️ 아두이노 연결 실패 (테스트 모드 진행)")

# 3. 라즈베리파이용 소켓 준비
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 4. 시나리오 로드
with open('scenario.json', 'r', encoding='utf-8') as f:
    scenario = json.load(f)

# 마지막으로 실행한 이벤트 인덱스
last_event_index = -1


@app.route('/')
def index():
    return render_template('index.html')


# -------------------------------------------
# 🔥 핵심 수정된 부분: time_update 이벤트 처리
# -------------------------------------------
@socketio.on('time_update')
def handle_time_update(data):
    global last_event_index
    current_time = data["time"]

    # 현재 시간보다 작거나 같은 이벤트 중,
    # 아직 실행되지 않은 이벤트는 모두 실행한다.
    while last_event_index + 1 < len(scenario):
        next_event = scenario[last_event_index + 1]

        if current_time >= next_event["time"]:
            print(f"⚾ 이벤트 발생! [{next_event['time']}초] {next_event['text']}")

            # 1. 웹 UI 업데이트
            emit("update_ui", next_event)

            # 2. 라즈베리파이 사운드 출력
            if "sound" in next_event and next_event["sound"]:
                try:
                    sock.sendto(next_event["sound"].encode(), (RPI_IP, RPI_PORT))
                except:
                    print("⚠️ 라즈베리파이 UDP 전송 실패")

            # 3. 아두이노 LED 제어
            if arduino and "led" in next_event:
                led_map = {
                    "STRIKE_RED": b"S",
                    "BALL_YELLOW": b"B",
                    "HIT_GREEN": b"H",
                    "HOMERUN": b"R",
                    "RESET": b"0",
                }
                cmd = led_map.get(next_event["led"], b"0")
                arduino.write(cmd)

            last_event_index += 1

        else:
            # 아직 시간이 안 된 이벤트가 나오면 반복 종료
            break


# -------------------------------------------
# 영상 탐색(Seek) 시 이벤트 포인터 재조정
# -------------------------------------------
@socketio.on('seek_event')
def handle_seek(data):
    global last_event_index

    seek_time = data["time"]
    new_index = -1

    # 탐색한 시간 이전의 이벤트는 모두 "실행된 것으로" 처리
    for i, event in enumerate(scenario):
        if event["time"] <= seek_time:
            new_index = i
        else:
            break

    last_event_index = new_index
    print(f"⏩ 영상 탐색됨: {seek_time:.2f}초 → 다음 이벤트 인덱스 {last_event_index + 1}")


# -------------------------------------------
# 서버 실행
# -------------------------------------------
if __name__ == "__main__":
    print("⚾ 야구 중계 시스템 서버 시작")
    print("👉 http://localhost:5000 접속")
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
