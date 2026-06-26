"""추론 device 자동 선택.

우선순위: CUDA(엔비디아) > MPS(애플 실리콘 GPU) > CPU.
분석기를 맥미니(M4)에 두는 구성에서 MPS를 자동으로 쓰기 위함.
"""
import torch


def get_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


DEVICE = get_device()
