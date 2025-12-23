import requests
import time
import json
import os
import re 

# ===================================================================
# 설정 변수: 이 URL만 변경하면 다른 경기도 모니터링 가능
# ===================================================================
USER_INPUT_URL = "https://m.sports.naver.com/game/88881115KRJP02025/relay#0"
POLLING_INTERVAL = 3  # 갱신 주기 (3초)
# ===================================================================


def extract_game_id(url):
    """입력받은 URL에서 Game ID를 추출합니다."""
    # Game ID에 문자가 포함될 수 있으므로 (\d+) -> ([\w]+)로 수정
    match = re.search(r'/game/([\w]+)/relay', url)
    
    if match:
        return match.group(1)
    else:
        return None

# GAME_ID와 API URL, 헤더 자동 설정
GAME_ID = extract_game_id(USER_INPUT_URL)
if not GAME_ID:
    print(f"오류: 입력한 URL에서 Game ID를 찾을 수 없습니다.\nURL 형식: .../game/GAME_ID/relay...")
    exit()

HEADERS = {
    "Referer": f"https://m.sports.naver.com/game/{GAME_ID}/relay",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
}

# 전역 변수 설정
last_processed_seqno = 0
current_inning = 1 
current_pitcher_name = "---"
current_batter_name = "---"
first_run = True # ⚾ [추가] 첫 번째 실행인지 확인하는 플래그

def clear_terminal():
    """터미널 화면을 지웁니다."""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_player_name_by_pcode(result_data, pcode):
    """pcode를 받아서 선수 이름을 찾아 반환하는 헬퍼 함수"""
    lineups = [
        result_data.get('textRelayData', {}).get('homeLineup', {}).get('batter', []),
        result_data.get('textRelayData', {}).get('homeLineup', {}).get('pitcher', []),
        result_data.get('textRelayData', {}).get('awayLineup', {}).get('batter', []),
        result_data.get('textRelayData', {}).get('awayLineup', {}).get('pitcher', [])
    ]
    
    for lineup in lineups:
        for player in lineup:
            if player.get('pcode') == pcode:
                return player.get('name', 'Unknown')
    return 'Unknown'


def print_current_status(result_data):
    """현재 게임 상황을 터미널에 출력합니다."""
    global current_batter_name, current_pitcher_name, current_inning
    
    try:
        game = result_data['game']
        data = result_data['textRelayData']
        state = data['currentGameState']
        
        current_inning = data.get('inn', current_inning) 
        
        is_home_attack = (data['homeOrAway'] == "1")
        defense_lineup = data['awayLineup'] if is_home_attack else data['homeLineup']
        attack_lineup = data['homeLineup'] if is_home_attack else data['awayLineup']

        pitcher_pcode = state.get('pitcher')
        batter_pcode = state.get('batter')

        current_pitcher_name = get_player_name_by_pcode(result_data, pitcher_pcode)
        current_batter_name = get_player_name_by_pcode(result_data, batter_pcode)

        # ⚾ [수정] 화면을 지우는 clear_terminal()이 여기로 이동
        clear_terminal()
        print(f"⚾ [{GAME_ID}] 실시간 중계 모니터링 중...")
        print(f"   (원본 URL: {USER_INPUT_URL})")
        print("=====================================================")
        print(f"   {game['awayTeamName']} {state['awayScore']} : {state['homeScore']} {game['homeTeamName']}")
        print(f"   {game['statusInfo']} (B:{state['ball']} S:{state['strike']} O:{state['out']})")
        print("-----------------------------------------------------")
        print(f"   투수: {current_pitcher_name}")
        print(f"   타자: {current_batter_name}")
        print("=====================================================\n")

    except KeyError as e:
        print(f"상태 업데이트 중 오류: 키 {e}를 찾을 수 없습니다.")
    except Exception as e:
        print(f"상태 업데이트 중 알 수 없는 오류: {e}")


def check_for_new_events(plays, latest_seqno, result_data, is_first_run): # ⚾ is_first_run 파라미터 추가
    """모든 새 이벤트를 선수 이름과 함께 출력합니다."""
    
    global last_processed_seqno
    new_events_found = False

    new_plays = [p for p in plays if p.get('seqno', 0) > last_processed_seqno]
    
    if new_plays:
        new_plays.sort(key=lambda p: p.get('seqno', 0))
        
        # ⚾ [수정] 첫 실행이 아닐 때만 "새 이벤트 감지" 문구 출력
        if not is_first_run: 
            print("[새 이벤트 감지!]")
        
        for play in new_plays:
            play_text = play.get('text', '')
            event_type = play.get('type', 0)

            batter_pcode = play.get('currentGameState', {}).get('batter')
            batter_name = get_player_name_by_pcode(result_data, batter_pcode)
            
            # --- 모든 주요 이벤트 출력 ---
            
            # type 1: 투구 (볼, 스트라이크, 파울, 헛스윙)
            if event_type == 1:
                print(f"  [{batter_name}]: {play_text}")
                new_events_found = True
            
            # type 13: 타석 결과 (안타, 아웃, 볼넷, 사구)
            # type 23: 홈런
            # type 2: 교체
            # type 14: 주루
            # type 24: 득점
            # type 7: 기타 이벤트 (투수판 이탈 등)
            elif event_type in [13, 23, 2, 14, 24, 7]:
                clean_text = play_text.replace(' : ', ': ')
                print(f"  [GAME]: {clean_text}")
                new_events_found = True
            
        last_processed_seqno = latest_seqno
    
    return new_events_found

# 7. 메인 루프 (3초마다 반복)
try:
    while True:
        try:
            API_URL = f"https://api-gw.sports.naver.com/schedule/games/{GAME_ID}/game-polling?inning={current_inning}&isHighlight=false"
            
            response = requests.get(API_URL, headers=HEADERS, timeout=5)
            response.raise_for_status()
            data = response.json()

            if not data.get('success') or 'result' not in data:
                # ⚾ [수정] 오류 발생 시 화면을 지우지 않고 현재 시간만 출력
                print(f"[{time.strftime('%H:%M:%S')}] API 오류: {data.get('message', '알 수 없는 오류')}")
                time.sleep(POLLING_INTERVAL)
                continue

            result_data = data['result']

            # 8. ⚾ [수정] 새 이벤트가 있는지 *먼저* 확인
            all_plays = []
            current_max_seqno = last_processed_seqno
            
            relays = result_data.get('textRelayData', {}).get('textRelays', [])
            if not relays:
                if first_run: # 처음 실행인데 데이터가 없으면
                     print(f"[{time.strftime('%H:%M:%S')}] 중계 데이터가 없습니다. (경기 종료 또는 대기 중)")
                # (이미 실행 중이었다면, 마지막 상태를 유지하고 아무것도 안함)
                time.sleep(POLLING_INTERVAL)
                continue

            for at_bat in relays:
                for play in at_bat.get('textOptions', []):
                    all_plays.append(play)
                    current_max_seqno = max(current_max_seqno, play.get('seqno', 0))

            # 9. ⚾ [수정] 마지막 seqno와 비교하여 갱신할지 결정
            if current_max_seqno > last_processed_seqno or first_run:
                
                # 10. 터미널에 현재 상황판 출력 (이 함수 안에서 clear_terminal() 호출)
                print_current_status(result_data)

                # 11. 새로운 이벤트가 있는지 확인 및 출력 (first_run 플래그 전달)
                check_for_new_events(all_plays, current_max_seqno, result_data, first_run)
                
                first_run = False # 첫 실행 플래그 비활성화
            
            # else:
            #   (새 이벤트가 없으면 아무것도 하지 않음)

            # 12. 3초 대기
            time.sleep(POLLING_INTERVAL)

        except requests.exceptions.RequestException as e:
            print(f"[{time.strftime('%H:%M:%S')}] 네트워크 오류: {e}")
            time.sleep(POLLING_INTERVAL)
        except json.JSONDecodeError:
            print(f"[{time.strftime('%H:%M:%S')}] JSON 파싱 오류. (데이터 형식 문제)")
            time.sleep(POLLING_INTERVAL)
        except Exception as e:
            print(f"[{time.strftime('%H:%M:%S')}] 알 수 없는 오류: {e}")
            time.sleep(POLLING_INTERVAL)

except KeyboardInterrupt:
    print("\n👋 모니터링을 종료합니다.")