// server.js
const express = require('express');
const cors = require('cors');
const axios = require('axios'); // 'node-fetch' 대신 'axios' 사용

const app = express();
const port = 3000;

app.use(cors()); // 모든 도메인의 요청을 허용 (로컬 테스트용)

// '/api/relay' 주소로 요청이 오면, 네이버 서버에 데이터를 대신 요청
app.get('/api/relay', async (req, res) => {
    try {
        // 사용자가 알려준 실시간 게임 ID
        const gameId = "88881115KRJP02025";

        // 현재 이닝 값을 쿼리에서 받음 (없으면 1로 시작)
        const inning = req.query.inning || '1'; 

        const naverApiUrl = `https://api-gw.sports.naver.com/schedule/games/${gameId}/game-polling?inning=${inning}&isHighlight=false`;

        // axios를 사용해 네이버 API에 요청
        const response = await axios.get(naverApiUrl, {
            headers: {
                // 우리가 네이버 모바일 페이지에서 요청한 것처럼 위장
                'Referer': `https://m.sports.naver.com/game/${gameId}/relay`,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36'
            }
        });

        // 네이버에서 받은 데이터를 클라이언트(html)로 그대로 전송
        res.json(response.data);

    } catch (error) {
        console.error("API 요청 오류:", error.message);
        res.status(500).json({ error: '네이버 API에서 데이터를 가져오는 데 실패했습니다.' });
    }
});

app.listen(port, () => {
    console.log(`⚾ 야구 중계 프록시 서버가 http://localhost:${port} 에서 실행 중입니다.`);
    console.log(`이제 my_relay.html 파일을 'Open with Live Server'로 실행하세요.`);
});