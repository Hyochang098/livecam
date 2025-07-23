# LiveCam - 실시간 YOLO 객체 탐지 WebRTC 스트리밍

LAN/인터넷 환경에서 YOLO 객체 탐지가 적용된 실시간 영상을 WebRTC로 스트리밍하는 시스템입니다.

## 🎯 주요 기능

- **실시간 객체 탐지**: YOLOv8을 사용한 80개 클래스 객체 인식
- **저지연 스트리밍**: WebRTC P2P 연결로 최소 지연
- **다양한 송출 방식**: 브라우저(일반 웹캠) 또는 Python(YOLO 적용)
- **Room 기반**: 동일 roomId로 1:N 스트리밍 가능

## 🏗️ 시스템 구조

```
[카메라] → [YOLO 처리] → [WebRTC 송출] → [시그널링 서버] → [브라우저 뷰어]
   ↓           ↓              ↓                ↓                 ↓
웹캠 영상   객체 탐지      RTP 스트림      WebSocket       실시간 시청
           바운딩박스                      (room 기반)
```

## 📦 설치 및 실행

### 사전 요구사항
- Node.js 14+
- Python 3.8+
- 웹캠

### 1. 프로젝트 클론 및 의존성 설치

```bash
# 프로젝트 클론
git clone <repo>
cd livecam

# Node.js 패키지 설치
npm install

# Python 가상환경 생성 및 패키지 설치
python -m venv venv
source venv/Scripts/activate  # Windows
# source venv/bin/activate    # Linux/Mac

pip install -r requirements.txt
```

### 2. 서버 실행

```bash
node server.js
# 출력: http/ws :3000
```

### 3. 사용 방법

#### 옵션 A: 일반 웹캠 스트리밍
```bash
# 송출자 (노트북/웹캠)
http://<서버IP>:3000/sender.html

# 시청자 (데스크톱/브라우저)
http://<서버IP>:3000/viewer.html
```

#### 옵션 B: YOLO 객체 탐지 스트리밍
```bash
# 시청자 먼저 열기
http://<서버IP>:3000/viewer.html

# YOLO 송출 시작 (Python)
python python_sender/yolo_sender.py
```

#### 옵션 C: Jetson/카메라 센서 직접 연결
```bash
# WebSocket 엔드포인트
ws://<서버IP>:3000/ws/room1
# 공인서버: wss://<도메인>:3000/ws/room1
```

## 📁 프로젝트 구조

```
livecam/
├── server.js              # Node.js 시그널링 서버
├── public/
│   ├── sender.html        # 브라우저 송출 페이지
│   └── viewer.html        # 시청자 페이지
├── python_sender/
│   └── yolo_sender.py     # YOLO + WebRTC 송출
├── requirements.txt       # Python 패키지 목록
└── package.json          # Node.js 패키지 목록
```

## 🔄 시그널링 흐름

```
viewer → server: {"type": "hello"}
server → sender: {"type": "hello"}
sender → server: {"type": "offer", "sdp": "..."}
server → viewer: {"type": "offer", "sdp": "..."}  
viewer → server: {"type": "answer", "sdp": "..."}
server → sender: {"type": "answer", "sdp": "..."}
```

## ⚡ 성능 최적화

### YOLO 모델 선택
```python
# nano (가장 빠름, 기본값)
self.model = YOLO('yolov8n.pt')

# 더 정확한 탐지가 필요한 경우
# self.model = YOLO('yolov8s.pt')  # small
# self.model = YOLO('yolov8m.pt')  # medium
```

### GPU 사용 (CUDA 지원 시)
```python
self.model = YOLO('yolov8n.pt')
self.model.to('cuda')
```

### 해상도 조정
```python
# 낮은 해상도로 더 빠른 처리
self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
```

## 🔧 문제 해결

| 문제 | 해결 방법 |
|------|----------|
| 카메라 접근 오류 | `camera_index=1` 로 변경 (외부 카메라) |
| 브라우저 권한 팝업 안 뜸 | Firefox 사용 또는 Chrome `--unsafely-treat-insecure-origin-as-secure` |
| WebSocket 연결 실패 | 방화벽 확인, 실제 IP 주소 사용 |
| 검은 화면 | `muted` 속성 확인, autoplay 정책 |
| YOLO 모델 다운로드 | 첫 실행 시 자동 다운로드 (50MB) |

## 🚀 확장 가능성

- **다중 카메라**: 여러 room으로 동시 송출
- **커스텀 YOLO 모델**: 특정 객체 탐지 특화
- **녹화 기능**: 탐지 결과 저장
- **알림 시스템**: 특정 객체 감지 시 알림
- **TURN 서버**: 제한된 네트워크 환경 지원

## 📝 주의사항

- 프로덕션 환경에서는 HTTPS/WSS 사용 권장
- Room ID 기반 인증 추가 고려
- 네트워크 대역폭 확인 (720p 기준 약 2-3Mbps)
