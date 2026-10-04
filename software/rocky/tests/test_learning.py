from dataclasses import replace
from pathlib import Path
import unittest

from brain.controller import TaskController
from csp.conversation import Utterance, encode_text
from csp.core import CspCodec
from csp.learning import WORDS, Phrase, Unit, decode_phrase, encode_phrase
from rocky.audio import SAMPLE_RATE, events, estimated_duration, frequency, synthesize
from rocky.translation import decoded_text, learning_rows

# Independent golden data from CT2_LEARNING_V1.md; never derive from WORDS/YAML.
STARTER_GOLDENS = {
    'hello': ('SOCIAL.hello', 'E4 A4 D4 D4 Fsharp4'),
    'goodbye': ('SOCIAL.goodbye', 'E4 A4 D4 E4 A4'),
    'yes': ('SOCIAL.yes', 'E4 A4 E4 D4 A4'),
    'no': ('SOCIAL.no', 'E4 A4 E4 E4 B4'),
    'help': ('ACTION.help', 'D4 A4 A4 Fsharp4 Fsharp4'),
    'thank you': ('SOCIAL.thank_you', 'E4 A4 D4 A4 D4'),
    'please': ('SOCIAL.please', 'E4 A4 D4 Fsharp4 B4'),
    'sorry': ('SOCIAL.sorry', 'E4 A4 D4 B4 E4'),
    'ready': ('QUALITY.ready', 'A4 Fsharp4 D4 B4 Fsharp4'),
    'wait': ('ACTION.wait', 'D4 A4 Fsharp4 D4 B4'),
    'repeat': ('ACTION.repeat', 'D4 A4 Fsharp4 B4 A4'),
    'robot': ('ENTITY.robot', 'D4 Fsharp4 D4 B4 D4'),
    'music': ('ENTITY.music', 'D4 Fsharp4 B4 E4 E4'),
    'computer': ('ENTITY.computer', 'D4 Fsharp4 Fsharp4 A4 E4'),
    'project': ('ENTITY.project', 'D4 Fsharp4 A4 Fsharp4 E4'),
}


class LearningTests(unittest.TestCase):
    def setUp(self):
        self.codec = CspCodec.from_default_spec()
        self.tasks = TaskController(self.codec)

    def test_roundtrip_whitespace_case_punctuation_unicode(self):
        for text in ('Hello, robot! Thank you.', 'HELLO  project; YES?', 'hELLo music… café 🎵', 'no\u00a0robot', "nobody no's underscore_no", 'thank  you', 'thank You', '你好'):
            with self.subTest(text=text):
                phrase = encode_phrase(text)
                self.assertEqual(decode_phrase(phrase), text)
                self.assertEqual(phrase, encode_phrase(text))
                output = self.tasks.build_communication(Utterance(text))
                self.assertEqual(decoded_text(output)[0], text)

    def test_stable_patterns_across_sentences_and_golden_notes(self):
        expected = ('E4', 'A4', 'D4', 'D4', 'Fsharp4')
        self.assertEqual(self.codec.encode_token(WORDS['hello']).notes, expected)
        for text in ('hello', 'please hello robot', 'hello, project'):
            tokens = [u.value for u in encode_phrase(text).units if u.kind == 'token']
            self.assertIn('SOCIAL.hello', tokens)
            rendered = list(events(self.tasks.build_communication(Utterance(text)), self.codec))
            from rocky.audio import frequency
            pattern = [((frequency(n),), 140, 35) for n in expected]
            self.assertTrue(any(rendered[i:i+5] == pattern for i in range(len(rendered)-4)))

    def test_every_documented_starter_has_its_golden_five_note_core(self):
        self.assertEqual(WORDS, {word: token for word, (token, _) in STARTER_GOLDENS.items()})
        spec = Path(__file__).resolve().parents[3] / 'language/specification/CT2_LEARNING_V1.md'
        dictionary = spec.read_text(encoding='utf-8').split('## Starter dictionary', 1)[1].split('## ', 1)[0]
        rows = [tuple(cell.strip().strip('`') for cell in line.split('|')[1:-1])
                for line in dictionary.splitlines()
                if line.startswith('| ') and '`' in line and len(line.split('|')) == 5]
        self.assertEqual(rows, [(word, token, notes) for word, (token, notes) in STARTER_GOLDENS.items()])
        for word, (token, notes) in STARTER_GOLDENS.items():
            with self.subTest(word=word):
                core = tuple(notes.split())
                self.assertEqual(len(core), 5)
                self.assertEqual(self.codec.encode_token(token).notes, core)
                for surface, case in ((word, 'lower'), (word.capitalize(), 'initial'), (word.upper(), 'upper')):
                    for text in (surface, f'please {surface}, robot!'):
                        with self.subTest(text=text):
                            phrase = encode_phrase(text)
                            self.assertIn(Unit('token', token, case), phrase.units)
                            self.assertEqual(decode_phrase(phrase), text)
                            output = self.tasks.build_communication(Utterance(text))
                            self.assertEqual(decoded_text(output)[0], text)
                            for multiplier in (1, 3):
                                rendered = list(events(output, self.codec, multiplier))
                                pattern = [((frequency(note),), 140*multiplier, 35*multiplier) for note in core]
                                self.assertTrue(any(rendered[i:i+5] == pattern for i in range(len(rendered)-4)),
                                                (text, multiplier, core))

    def test_phrases_and_word_boundaries(self):
        self.assertEqual(encode_phrase('thank you').units, (Unit('token', 'SOCIAL.thank_you'),))
        self.assertTrue(all(u.kind == 'utf8' for u in encode_phrase("nobody no's no_way").units))
        self.assertTrue(all(u.kind == 'utf8' for u in encode_phrase('hELLo').units))
        self.assertTrue(any('fallback' in label for _, label in learning_rows(self.tasks.build_communication(Utterance('unknown 🎵')))))

    def test_old_ct1_decode_and_translation_mismatch(self):
        old = TaskController(self.codec, 'ct1').build_communication(Utterance('An older response.'))
        self.assertEqual(old.symbols, encode_text('An older response.'))
        self.assertEqual(decoded_text(old), ('An older response.', 'CT1'))
        new = self.tasks.build_communication(Utterance('hello robot'))
        for output in (old, new):
            with self.assertRaisesRegex(ValueError, 'match'):
                decoded_text(replace(output, canonical_text='different'))
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                list(events(replace(output, canonical_text='different'), self.codec))

    def test_invalid_representation_rejected(self):
        for phrase in (Phrase((), 'CT3'), Phrase((Unit('token', 'ACTION.invented'),)), Phrase((Unit('utf8', ((4,4,4,4),)),)), Phrase((Unit('token', 'SOCIAL.hello', 'random'),))):
            with self.assertRaises(ValueError):
                decode_phrase(phrase)

    def test_three_times_duration_unchanged_pitch_and_exact_estimate(self):
        for text in ('Hello.', 'hello robot', 'xyz'):
            output = self.tasks.build_communication(Utterance(text))
            slow, normal = list(events(output, self.codec, 3)), list(events(output, self.codec))
            self.assertEqual([f for f, _, _ in normal], [f for f, _, _ in slow])
            self.assertEqual([(d*3,g*3) for _,d,g in normal], [(d,g) for _,d,g in slow])
            # PCM rounding is at most one frame per event boundary.
            self.assertAlmostEqual(estimated_duration(output,self.codec,3), 3*estimated_duration(output,self.codec), delta=len(slow)*2/SAMPLE_RATE)
        output = self.tasks.build_communication(Utterance('hello'))
        pcm = synthesize(output, self.codec, 0, 3)
        self.assertEqual(len(pcm)//2, round(estimated_duration(output,self.codec,3)*SAMPLE_RATE))
        self.assertEqual(set(pcm), {0})
