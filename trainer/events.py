"""Structured messages from the worker to the desktop application."""

import json
import math


def emit(kind, **fields):
    print("EVENT " + json.dumps({"kind": kind, **fields}, ensure_ascii=False), flush=True)


def progress(epoch, epochs, batch=0, batches=1):
    emit("progress", epoch=epoch, epochs=epochs, batch=batch, batches=max(int(batches), 1))


def metrics(values, fields):
    result = {}
    for name, candidates in fields.items():
        for key in candidates:
            if key in values:
                value = float(values[key])
                if math.isfinite(value):
                    result[name] = value
                    break
    return result
