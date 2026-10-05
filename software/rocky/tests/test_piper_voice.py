"""Optional Piper neural English voice sidecar tests."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
import json
from pathlib import Path
import tempfile
import threading
import unittest
import wave

from rocky.piper_voice import PiperSidecarError, PiperSidecarSpeechRenderer


def wav_bytes(seconds=0.25, rate=22050):
    frames=max(1, round(rate*seconds))
    out=BytesIO()
    with wave.open(out,"wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00"*frames)
    return out.getvalue()


class PiperFixtureHandler(BaseHTTPRequestHandler):
    token=""
    requests=[]
    voice="fixture-neural-voice"

    def log_message(self,*args):
        pass

    def _auth(self):
        return self.headers.get("X-Rocky-Piper-Token")==type(self).token

    def do_GET(self):
        type(self).requests.append(("GET",self.path,None))
        if not self._auth():
            self.send_response(403); self.end_headers(); return
        raw=json.dumps({"schema_version":1,"ready":True,"voice":type(self).voice}).encode()
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        length=int(self.headers["Content-Length"])
        body=json.loads(self.rfile.read(length))
        type(self).requests.append(("POST",self.path,body))
        if not self._auth():
            self.send_response(403); self.end_headers(); return
        raw=wav_bytes()
        self.send_response(200)
        self.send_header("Content-Type","audio/wav")
        self.send_header("Content-Length",str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


class PiperVoiceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.token=self.root/"piper.token"
        self.token.write_text("p"*48,encoding="utf-8")
        PiperFixtureHandler.token="p"*48
        PiperFixtureHandler.requests=[]
        self.server=ThreadingHTTPServer(("127.0.0.1",0),PiperFixtureHandler)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.temp.cleanup()

    def renderer(self,**kwargs):
        return PiperSidecarSpeechRenderer(
            self.server.server_port,
            self.token,
            timeout_seconds=5,
            **kwargs,
        )

    def test_status_is_token_authenticated_and_reports_loaded_voice(self):
        voice=self.renderer()
        try:
            self.assertEqual(voice.check_available(),("fixture-neural-voice",))
            self.assertEqual(PiperFixtureHandler.requests[0][:2],("GET","/v1/status"))
        finally:
            voice.close()

    def test_duration_uses_real_returned_wav_and_request_has_bounded_prosody(self):
        voice=self.renderer(rate_offset=1,volume_offset=-1)
        try:
            duration=voice.estimate_duration_seconds("Question interesting. Rocky think?")
            self.assertAlmostEqual(duration,0.25,places=2)
            method,path,body=PiperFixtureHandler.requests[-1]
            self.assertEqual((method,path),("POST","/v1/synthesize"))
            self.assertEqual(body["schema_version"],1)
            self.assertEqual(body["text"],"Question interesting. Rocky think?")
            self.assertGreaterEqual(body["length_scale"],0.60)
            self.assertLessEqual(body["length_scale"],1.60)
            self.assertGreaterEqual(body["volume"],0.35)
            self.assertLessEqual(body["volume"],1.50)
            self.assertEqual(voice.last_profile,"question")
        finally:
            voice.close()

    def test_prepared_wav_is_reused_for_playback_turn_instead_of_resynthesized(self):
        voice=self.renderer()
        try:
            voice.estimate_duration_seconds("Rocky ready. Good.")
            requests_before=len(PiperFixtureHandler.requests)
            prepared=voice._take_prepared("Rocky ready. Good.")
            self.assertEqual(len(PiperFixtureHandler.requests),requests_before)
            self.assertEqual(prepared[0],"Rocky ready. Good.")
            self.assertAlmostEqual(prepared[6],0.25,places=2)
        finally:
            voice.close()

    def test_nonzero_pitch_is_rejected_instead_of_silently_ignored(self):
        with self.assertRaisesRegex(ValueError,"pitch"):
            self.renderer(pitch_offset=1)

    def test_bad_token_or_mismatched_voice_fails_closed(self):
        self.token.write_text("bad",encoding="utf-8")
        voice=self.renderer()
        try:
            with self.assertRaisesRegex(PiperSidecarError,"token"):
                voice.check_available()
        finally:
            voice.close()
        self.token.write_text("p"*48,encoding="utf-8")
        voice=self.renderer(voice_name="different-voice")
        try:
            with self.assertRaisesRegex(PiperSidecarError,"does not match"):
                voice.check_available()
        finally:
            voice.close()

    def test_control_characters_and_oversized_speech_are_rejected_before_network(self):
        voice=self.renderer()
        try:
            before=len(PiperFixtureHandler.requests)
            with self.assertRaises(ValueError):
                voice.estimate_duration_seconds("bad\x00text")
            with self.assertRaises(ValueError):
                voice.estimate_duration_seconds("x"*385)
            self.assertEqual(len(PiperFixtureHandler.requests),before)
        finally:
            voice.close()


if __name__=="__main__":
    unittest.main()
