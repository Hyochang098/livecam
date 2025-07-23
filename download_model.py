"""
YOLO 모델 다운로드 스크립트
PyTorch 2.6 호환성 문제 해결을 위한 사전 다운로드
"""

import torch
# PyTorch 2.6 이전 버전의 동작 방식으로 설정
torch.serialization.set_default_load_endianness('native')

from ultralytics import YOLO
import os

# 모델 저장 경로
MODEL_PATH = 'yolov8n.pt'

if not os.path.exists(MODEL_PATH):
    print("YOLOv8n 모델 다운로드 중...")
    # 모델 다운로드
    model = YOLO('yolov8n.pt')
    print("다운로드 완료!")
    
    # 테스트
    print("모델 테스트 중...")
    import numpy as np
    dummy_image = np.zeros((640, 480, 3), dtype=np.uint8)
    results = model(dummy_image, verbose=False)
    print("모델 정상 작동 확인!")
else:
    print(f"모델이 이미 존재합니다: {MODEL_PATH}")

print("\n이제 python python_sender/yolo_sender.py 를 실행하세요.") 