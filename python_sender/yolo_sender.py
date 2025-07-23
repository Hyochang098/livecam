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
from aiortc import RTCPeerConnection, VideoStreamTrack, RTCSessionDescription
from av import VideoFrame
import time
import logging
import os

# YOLO 모델 다운로드 경로 설정
os.environ['YOLO_VERBOSE'] = 'False'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class YOLOVideoStreamTrack(VideoStreamTrack):
    """YOLO 처리된 비디오 스트림을 WebRTC 트랙으로 변환"""
    
    def __init__(self, camera_index=0):
        super().__init__()
        # 카메라 연결 시도 (0이 안되면 1 시도)
        self.cap = cv2.VideoCapture(camera_index)
        if not self.cap.isOpened():
            logger.warning(f"Camera {camera_index} not found, trying alternative...")
            self.cap = cv2.VideoCapture(1)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        
        # YOLO 모델 로드
        logger.info("Loading YOLO model...")
        try:
            # 모델 파일이 없으면 자동 다운로드
            self.model = YOLO('yolov8n.pt')  # nano 모델로 시작 (빠른 처리)
            logger.info("YOLO model loaded")
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
        
    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        # 웹캠에서 프레임 읽기
        ret, frame = self.cap.read()
        if not ret:
            logger.error("Failed to read frame from camera")
            # 검은 화면 반환
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            # YOLO 디텍션 수행
            results = self.model(frame, verbose=False)
            
            # 결과를 프레임에 그리기
            annotated_frame = results[0].plot()
            frame = annotated_frame
            
            self.frame_count += 1
            if self.frame_count % 30 == 0:
                logger.info(f"Processed {self.frame_count} frames")
        
        # BGR to RGB 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # VideoFrame 생성
        video_frame = VideoFrame.from_ndarray(frame_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame
    
    def __del__(self):
        if hasattr(self, 'cap'):
            self.cap.release()


async def run_sender(server_url="ws://localhost:3000/ws/room1"):
    """WebRTC 송출 실행"""
    logger.info(f"Connecting to {server_url}")
    
    # WebRTC PeerConnection 생성
    pc = RTCPeerConnection(configuration={
        "iceServers": [{"urls": "stun:stun.l.google.com:19302"}]
    })
    
    # YOLO 비디오 트랙 추가
    video_track = YOLOVideoStreamTrack(camera_index=0)
    pc.addTrack(video_track)
    
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
                
                if data["type"] == "hello":
                    logger.info("Received hello, creating offer...")
                    # Offer 생성
                    offer = await pc.createOffer()
                    await pc.setLocalDescription(offer)
                    
                    await ws.send(json.dumps({
                        "type": "offer",
                        "sdp": pc.localDescription.sdp
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
                        await pc.addIceCandidate(data["candidate"])
        
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