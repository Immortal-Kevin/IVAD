"""Observe an actual finite gradient and parameter change on the requested device."""

import torch


class UpdateEvidence:
    def __init__(self, device):
        self.device = device
        self.result = None
        self.sample = None

    def before(self, optimizer):
        if self.result:
            return
        for group in optimizer.param_groups:
            for param in group["params"]:
                if param.grad is None or param.device.type != self.device:
                    continue
                flat = param.grad.detach().reshape(-1)
                index = int(flat.abs().argmax())
                gradient = float(flat[index])
                if gradient != 0 and torch.isfinite(flat).all().item():
                    self.sample = param, index, gradient, float(param.detach().reshape(-1)[index])
                    return

    def after(self):
        if self.result or self.sample is None:
            return
        param, index, gradient, before = self.sample
        after = float(param.detach().reshape(-1)[index])
        if after != before and torch.isfinite(torch.tensor(after)).item():
            self.result = {"device": str(param.device), "gradient": gradient,
                           "parameter_before": before, "parameter_after": after}
            print(f"Optimizer update verified on {param.device}: {before:.8g} -> {after:.8g}", flush=True)
