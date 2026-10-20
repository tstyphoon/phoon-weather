"""單位換算。"""

# 蒲福風級的上限（m/s）：低於第 n 個數字就是 n 級
_BEAUFORT_LIMITS = [0.3, 1.6, 3.4, 5.5, 8.0, 10.8, 13.9, 17.2, 20.8, 24.5, 28.5, 32.7]


def beaufort(speed_ms: float) -> int:
    """風速（m/s）換算蒲福風級（0 到 12）。"""
    for level, limit in enumerate(_BEAUFORT_LIMITS):
        if speed_ms < limit:
            return level
    return 12
