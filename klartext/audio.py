"""Mikrofonaufnahme."""
import numpy as np

SAMPLE_RATE = 16000
MIN_SECONDS = 0.25


class Recorder:
    def __init__(self):
        self.frames = []
        self.stream = None

    def start(self):
        import sounddevice as sd

        self.frames = []
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._callback
        )
        self.stream.start()

    def _callback(self, indata, frames, time_info, status):
        self.frames.append(indata[:, 0].copy())

    def stop(self):
        self.stream.stop()
        self.stream.close()
        self.stream = None
        if not self.frames:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self.frames)
