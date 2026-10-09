"""Prevent automatic Windows sleep while measuring; never change power settings."""

import ctypes
import os
import time


def set_awake(enabled: bool) -> None:
    if os.name == "nt":
        flags = 0x80000000 | (0x00000001 if enabled else 0)
        if not ctypes.windll.kernel32.SetThreadExecutionState(flags):
            raise RuntimeError("Could not hold Windows execution state")


def main() -> None:
    set_awake(True)
    print("Automatic sleep guard active; Ctrl+C releases it.", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        set_awake(False)


if __name__ == "__main__":
    main()
