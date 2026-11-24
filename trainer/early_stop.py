"""RF-DETR patience policy for raw validation mAP on the 0–1 scale."""

import math

PATIENCE = 3
MIN_DELTA = 0.001


class ValidationPatience:
    def __init__(self):
        self.baseline = None
        self.best_score = None
        self.best_epoch = None
        self.stale = 0
        self.zeros = 0

    def observe(self, epoch, value):
        score = None if value is None else float(value)
        reason = None
        if score is not None and math.isfinite(score) and 0 <= score <= 1:
            if self.best_score is None or score > self.best_score:
                self.best_score, self.best_epoch = score, epoch
            self.zeros = self.zeros + 1 if score == 0 else 0
            if self.baseline is None or score >= self.baseline + MIN_DELTA:
                self.baseline, self.stale = score, 0
            else:
                self.stale += 1
            if self.zeros >= PATIENCE:
                reason = "连续 3 个有效验证轮 mAP@50–95 为 0"
            elif self.stale >= PATIENCE:
                reason = "连续 3 个有效验证轮 mAP@50–95 未改善至少 0.001"
        return {"epoch": epoch, "score": repr(score) if score is not None else None,
                "best_epoch": self.best_epoch, "best_score": self.best_score,
                "stale": self.stale, "zeros": self.zeros, "patience": PATIENCE, "reason": reason}
