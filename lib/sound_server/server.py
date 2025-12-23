import json
import socket
import serial
import time
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)

# --- 설정 구간 ---
# 1. 라즈베리파이 (스피커) 설정
RPI_IP = "192.168.0.XX"  # 라즈베리파이 IP 주소 입력 필수!
RPI_PORT = 12345

# 2. 아두이노 (LED) 설정
# 아두이노를 PC USB에 연결 후 장치관리자에서 포트 확인 (예: COM3)
try:
    arduino = serial.Serial('COM3', 9600, timeout=1) 
    time.sleep(2) # 연결 대기
    print("✅ 아두이노 연결 성공")
except:
    arduino = None
    print("⚠️ 아두이노 연결 실패 (테스트 모드로 진행)")

# 3. 소켓(UDP) 준비 (라즈베리파이 통신용)
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# 4. 시나리오 로드
with open('scenario.json', 'r', encoding='utf-8') as f:
    scenario = json.load(f)

# 마지막으로 실행된 이벤트 인덱스
last_event_index = -1

@app.route('/')
def index():
    return render_template('index.html') # 웹페이지(전광판+영상) 렌더링

# 브라우저에서 영상 시간이 업데이트 될 때마다 호출됨 (1초에 여러 번)
@socketio.on('time_update')
def handle_time_update(data):
    global last_event_index
    current_time = data['time'] # 영상의 현재 시간 (초)

    # 시나리오를 순회하며 아직 실행 안 된 이벤트 중, 시간이 된 것을 찾음
    # (순차적으로 실행되도록 로직 구성)
    next_index = last_event_index + 1
    
    if next_index < len(scenario):
        event = scenario[next_index]
        
        # 영상 시간이 이벤트 시간보다 같거나 커지면 실행
        if current_time >= event['time']:
            print(f"⚾ 이벤트 발생! [{event['time']}초] {event['text']}")
            
            # 1. PC 화면(전광판) 업데이트 신호 전송
            emit('update_ui', event)

            # 2. 라즈베리파이(스피커)로 소리 재생 신호 전송 (UDP)
            if 'sound' in event and event['sound']:
                msg = event['sound'] # 예: "hit.mp3"
                try:
                    sock.sendto(msg.encode(), (RPI_IP, RPI_PORT))
                except:
                    print("라즈베리파이 전송 실패")

            # 3. 아두이노(LED)로 제어 신호 전송 (Serial)
            if arduino and 'led' in event:
                # LED 패턴 정의 (아두이노 코드와 맞춰야 함)
                # S: 스트라이크(빨강), B: 볼(노랑), H: 안타(초록), R: 홈런(RGB)
                cmd = b'0'
                if event['led'] == 'STRIKE_RED': cmd = b'S'
                elif event['led'] == 'BALL_YELLOW': cmd = b'B'
                elif event['led'] == 'HIT_GREEN': cmd = b'H'
                elif event['led'] == 'HOMERUN': cmd = b'R'
                
                if cmd != b'0':
                    arduino.write(cmd)

            last_event_index = next_index

# 영상을 탐색(Seek)했을 때 싱크 재설정
@socketio.on('seek_event')
def handle_seek(data):
    global last_event_index
    seek_time = data['time']
    # 탐색한 시간보다 이전에 있는 가장 마지막 이벤트로 인덱스 조정
    new_index = -1
    for i, event in enumerate(scenario):
        if event['time'] <= seek_time:
            new_index = i
        else:
            break
    last_event_index = new_index
    print(f"영상 탐색됨: {seek_time}초, 다음 이벤트 인덱스: {last_event_index + 1}")

if __name__ == '__main__':
    print("⚾ 야구 중계 시스템 서버 시작...")
    print(f"👉 http://localhost:5000 접속하세요")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)