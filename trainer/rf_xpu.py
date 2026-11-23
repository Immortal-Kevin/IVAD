"""Single-device XPU integration for Lightning."""

import torch
from pytorch_lightning.accelerators import Accelerator


class XPULightningAccelerator(Accelerator):
    def setup_device(self, device):
        torch.xpu.set_device(device)

    def get_device_stats(self, device):
        return torch.xpu.memory_stats(device)

    def teardown(self):
        torch.xpu.empty_cache()

    @staticmethod
    def parse_devices(devices):
        if devices != 1:
            raise ValueError("IVAD supports a single XPU")
        return [0]

    @staticmethod
    def get_parallel_devices(devices):
        return [torch.device("xpu", index) for index in devices]

    @staticmethod
    def auto_device_count():
        return 1

    @staticmethod
    def is_available():
        return torch.xpu.is_available()

    @staticmethod
    def name():
        return "xpu"
