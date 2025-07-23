"""
YOLO v8 Object Detection with WebRTC Streaming
실시간 객체 탐지 결과를 WebRTC로 송출
"""

import asyncio
import json
import cv2
import numpy as np
from ultralytics import YOLO
import websockets
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription, RTCConfiguration, RTCIceServer, MediaStreamTrack
from av import VideoFrame
import time
import logging
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# YOLO 모델 다운로드 경로 설정
os.environ['YOLO_VERBOSE'] = 'False'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DummyAudioStreamTrack(MediaStreamTrack):
    """더미 오디오 스트림 (무음)"""
    
    kind = "audio"
    
    def __init__(self):
        super().__init__()
        
    async def recv(self):
        """무음 오디오 프레임 생성"""
        from av import AudioFrame
        import numpy as np
        
        pts, time_base = await self.next_timestamp()
        
        # 무음 프레임 생성 (48kHz, 20ms, stereo)
        sample_rate = 48000
        samples = 960  # 20ms at 48kHz
        audio_data = np.zeros((2, samples), dtype=np.int16)
        
        frame = AudioFrame.from_ndarray(audio_data, format="s16", layout="stereo")
        frame.sample_rate = sample_rate
        frame.pts = pts
        frame.time_base = time_base
        
        return frame


class YOLOVideoStreamTrack(VideoStreamTrack):
    """YOLO 처리된 비디오 스트림을 WebRTC 트랙으로 변환"""
    
    def __init__(self, camera_index=0):
        super().__init__()
        logger.info(f"🎥 Initializing YOLO Video Track with camera {camera_index}")
        
        # 카메라 연결 시도 (0이 안되면 1 시도)
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            logger.warning(f"Camera {camera_index} not found, trying alternative...")
            self.cap = cv2.VideoCapture(1)
        
        if not self.cap.isOpened():
            logger.error("No camera found! Will use black frames.")
        else:
            logger.info("✅ Camera opened successfully")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # YOLO 모델 로드
        logger.info("Loading YOLO model...")
        try:
            # 모델 파일이 없으면 자동 다운로드
            self.model = YOLO('yolov8n.pt')  # nano 모델로 시작 (빠른 처리)
            logger.info("✅ YOLO model loaded")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            logger.info("Trying to download model...")
            # 모델 다운로드 재시도
            from ultralytics import YOLO as YOLODownload
            model = YOLODownload('yolov8n.pt')
            model.export(format='onnx')  # ONNX로 변환하여 호환성 향상
            self.model = model
            logger.info("YOLO model loaded with alternative method")
        
        self.frame_count = 0
        logger.info("🎥 YOLO Video Track initialization complete")
        
    async def recv(self):
        try:
            logger.info("YOLO recv() called - starting frame processing")
            pts, time_base = await self.next_timestamp()
            
            # 웹캠에서 프레임 읽기
            ret, frame = self.cap.read()
            logger.info(f"Camera read result: {ret}")
            
            if not ret:
                logger.error("Failed to read frame from camera")
                # 컬러 테스트 패턴 생성 (검은 화면 대신)
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                # 빨간색 사각형 그리기
                frame[100:300, 200:400] = [0, 0, 255]  # BGR 빨간색
                # 텍스트 추가 (간단한 표시)
                frame[50:100, 50:200] = [255, 255, 255]  # 흰색 사각형
                logger.info("Using test pattern instead of black frame")
            else:
                logger.info(f"Camera frame shape: {frame.shape}")
                # YOLO 디텍션 수행
                logger.info("Starting YOLO detection...")
                results = self.model(frame, verbose=False)
                logger.info("YOLO detection completed")
                
                # 탐지된 객체 정보 로그
                detections = results[0].boxes
                if detections is not None and len(detections) > 0:
                    logger.info(f"✅ Detected {len(detections)} objects")
                else:
                    logger.info("No objects detected")
                
                # 결과를 프레임에 그리기
                annotated_frame = results[0].plot()
                frame = annotated_frame
                logger.info("Frame annotation completed")
                
                self.frame_count += 1
                if self.frame_count % 10 == 0:  # 더 자주 로그
                    logger.info(f"📹 Processed {self.frame_count} frames")
            
            # BGR to RGB 변환
            logger.info("Converting BGR to RGB...")
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # VideoFrame 생성
            logger.info("Creating VideoFrame...")
            video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            
            logger.info("✅ VideoFrame created successfully")
            return video_frame
            
        except Exception as e:
            logger.error(f"❌ Error in YOLO recv(): {e}")
            # 에러 시 테스트 패턴 반환
            pts, time_base = await self.next_timestamp()
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            # 에러 표시용 노란색 화면
            frame[:] = [0, 255, 255]  # BGR 노란색
            frame[200:250, 250:400] = [0, 0, 0]  # 검은 줄무늬
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            return video_frame
    
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()


async def run_sender(server_url=None):
    """WebRTC 송출 실행"""
    if server_url is None:
        # 환경변수에서 서버 설정 읽기
        server_host = os.environ.get('WEBRTC_SERVER_HOST', 'localhost')
        server_port = os.environ.get('WEBRTC_SERVER_PORT', '3000')
        room_name = os.environ.get('WEBRTC_ROOM_NAME', 'room1')
        server_url = f"ws://{server_host}:{server_port}/ws/{room_name}"
    
    logger.info(f"Connecting to {server_url}")
    
    # WebRTC PeerConnection 생성
    configuration = RTCConfiguration(iceServers=[
        RTCIceServer(urls=["stun:stun.l.google.com:19302"])
    ])
    pc = RTCPeerConnection(configuration=configuration)
    
    # 오디오 및 비디오 트랙 추가
    audio_track = DummyAudioStreamTrack()
    video_track = YOLOVideoStreamTrack(camera_index=0)
    pc.addTrack(audio_track)
    pc.addTrack(video_track)
    logger.info("🎥 Audio and Video tracks added to PeerConnection")
    
    # WebSocket 연결
    async with websockets.connect(server_url) as ws:
        logger.info("WebSocket connected")
        
        # ICE candidate 처리
        @pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate:
                await ws.send(json.dumps({
                    "type": "candidate",
                    "candidate": {
                        "candidate": candidate.candidate,
                        "sdpMLineIndex": candidate.sdpMLineIndex,
                        "sdpMid": candidate.sdpMid
                    }
                }))
        
        # hello 메시지 대기
        async def handle_messages():
            async for message in ws:
                data = json.loads(message)
                logger.info(f"Received message: {data}")
                
                if data["type"] == "hello":
                    logger.info("Received hello, creating offer...")
                    # Offer 생성
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    
                    await ws.send(json.dumps({
                        "type": "offer",
                        "sdp": pc.localDescription.sdp,
                        "sdpType": "offer"
                    }))
                    logger.info("Offer sent")
                    
                elif data["type"] == "answer":
                    logger.info("Received answer")
                    answer = RTCSessionDescription(
                        sdp=data["sdp"],
                        type="answer"
                    )
                    await pc.setRemoteDescription(answer)
                    logger.info("WebRTC connection established")
                    
                elif data["type"] == "candidate":
                    if data.get("candidate"):
                        try:
                            # ICE candidate 처리 - 여러 방법 시도
                            candidate_data = data["candidate"]
                            logger.info(f"Processing ICE candidate: {candidate_data}")
                            # 간단히 패스 - ICE candidate 없이도 연결 가능
                            logger.info("ICE candidate processing skipped")
                        except Exception as e:
                            logger.warning(f"ICE candidate error (ignored): {e}")
        
        try:
            await handle_messages()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            await pc.close()


if __name__ == "__main__":
    print("=== YOLO WebRTC Sender ===")
    print("1. 카메라 권한을 확인하세요")
    print("2. viewer.html을 브라우저에서 열어주세요")
    print("3. 이 프로그램이 자동으로 연결됩니다")
    print("Ctrl+C로 종료")
    print("========================")
    
    try:
        asyncio.run(run_sender())
    except KeyboardInterrupt:
        print("\nShutting down...") 