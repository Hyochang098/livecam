# LiveCam MVP 정리

## 1. 개요

LAN 환경에서 노트북(송출)‑>데스크톱(뷰어) 1 : 1 단방향 WebRTC 스트리밍을 최소한의 코드로 확인하는 MVP다. 시그널링은 Node + ws, 정적 파일도 같은 서버에서 서빙한다.

```
[노트북] sender.html ──WS/SDP──> Node(ws) ──WS/SDP──> viewer.html [데스크톱]
                    ↖───RTP media direct / TURN───↗
```

## 2. 설치 & 실행

```bash
# 1) 소스 받기
$ git clone <repo>
$ cd livecam

# 2) 패키지 설치
$ npm i ws mime

# 3) 개발 서버 실행 (데스크톱)
$ node server.js   # http & ws :3000

# 4) 접속
데스크톱  ➜  http://localhost:3000/      # viewer
노트북    ➜  http://<데스크톱IP>:3000/sender.html  # sender
```

## 3. 주요 파일

| 파일                   | 역할                                               |
| -------------------- | ------------------------------------------------ |
| `server.js`          | 정적 파일 서빙 + WebSocket 시그널링 브로커                    |
| `public/sender.html` | 카메라 캡처 → RTCPeerConnection 생성 + "hello/offer" 논리 |
| `public/viewer.html` | 새로고침마다 hello 전송 → offer 수신 후 answer 전송           |

## 4. 문제 & 해결 메모

| 증상               | 원인·해결                                                                          |
| ---------------- | ------------------------------------------------------------------------------ |
| JSON.parse 오류    | ws 모듈이 Buffer 로 수신 → `data.toString()` 후 브로드캐스트                                |
| 브라우저 권한 팝업 안 뜸   | 크롬 로컬 HTTP 제한 → Firefox 사용 or `--unsafely-treat-insecure-origin-as-secure` 플래그 |
| 검은 화면(트랙 없음)     | 트랙 추가 전에 `createOffer()` 호출 → 트랙 붙인 뒤 offer 생성                                 |
| 검은 화면(ontrack 후) | autoplay 차단 → muted 속성 + `video.play()` 후 catch                                |
| 새로고침 시 다시 안 보임   | viewer `hello` → sender 새 `offer` 패턴 추가                                        |

## 5. 추가 구현 아이디어

* JWT 인증   : Spring 발급 → WS 쿼리 `token` → Node 에서 검증
* TURN 지원 : coturn 도커 + `iceServers` 배열에 추가해 외부망/LTE 대응
* HTTPS    : mkcert 로 로컬 CA 작성 → Node 서버 TLS
* UI 개선  : 연결 상태 표시, 스트림 해상도 선택, 전체화면 토글
* 다자간   : 뷰어 N 명 허용 (대역폭 패널티) or SFU mediasoup 연동
* 로그     : winston + prom-client 로 요청·프레임 전송량 수집
