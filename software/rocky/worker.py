"""Spawned, bounded inference worker. No hardware object crosses this boundary."""

import json
import multiprocessing
import time


def _run(sender, provider, text, context):
    try:
        value = {"candidate": provider.propose(text, context)}
        raw = json.dumps(value, ensure_ascii=True).encode("utf-8")
        if len(raw) > 65536:
            raise ValueError("provider result exceeds worker limit")
    except Exception as exc:
        raw = json.dumps({"error": f"{type(exc).__name__}: {str(exc)[:300]}"}).encode("utf-8")
    try:
        sender.send_bytes(raw)
    finally:
        sender.close()


class InferenceWorker:
    def __init__(self, provider, timeout=120):
        self.provider = provider
        self.timeout = timeout
        self.process = None
        self.receiver = None

    def start(self, text, context):
        if self.process is not None:
            raise RuntimeError("BUSY")
        mp = multiprocessing.get_context("spawn")
        receiver, sender = mp.Pipe(duplex=False)
        process = mp.Process(target=_run, args=(sender, self.provider, text, context), daemon=True)
        try:
            process.start()
        except BaseException:
            receiver.close()
            sender.close()
            raise
        sender.close()
        self.receiver = receiver
        self.process = process
        self.deadline = time.monotonic() + self.timeout

    def poll(self):
        if self.process is None:
            return None
        if time.monotonic() >= self.deadline:
            self.cancel()
            return {"error": "PROVIDER_TIMEOUT: local inference exceeded the configured deadline"}
        if self.receiver.poll():
            try:
                result = json.loads(self.receiver.recv_bytes(65536))
            except (EOFError, OSError, ValueError):
                result = {"error": "PROVIDER_FAILED: invalid worker reply"}
            self.cancel()
            return result
        if not self.process.is_alive():
            self.cancel()
            return {"error": "PROVIDER_FAILED: worker exited"}
        return None

    def cancel(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=0.25)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=0.25)
            self.process.close()
            self.receiver.close()
            self.process = self.receiver = None
