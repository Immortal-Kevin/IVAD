"""Native checkpoint layout check, without importing a neural framework."""
from collections.abc import Mapping

def require_native_weights(checkpoint):
    # Upstream best-total PTH can also contain optimizer/Lightning metadata.
    # Native inference weights require its explicit model state mapping; a
    # training-only CKPT with state_dict is not accepted merely by renaming it.
    if not isinstance(checkpoint,Mapping) or not isinstance(checkpoint.get('model'),Mapping) or not checkpoint['model'] or not ('args' in checkpoint or 'model_config' in checkpoint):
        raise ValueError('RF native PTH model weights required; renamed training CKPT is not accepted')
