// RPA-1 Rocky Brain v0.1
// Target: Arduino Uno R3, two momentary buttons, passive buzzer.
// Language: Chordic, encoded with CSP-1.
//
// The Uno is the deterministic reflex and musical-output controller. A browser
// app on the connected computer supplies English text-to-speech in translated
// mode. No external Arduino libraries are required.

#include <Arduino.h>
#include <avr/pgmspace.h>

constexpr uint8_t PIN_MODE_BUTTON = 2;
constexpr uint8_t PIN_PHRASE_BUTTON = 4;
constexpr uint8_t PIN_PIEZO = 9;
constexpr uint8_t PIN_STATUS_LED = LED_BUILTIN;

constexpr uint16_t NOTE_C4 = 262;
constexpr uint16_t NOTE_D4 = 294;
constexpr uint16_t NOTE_E4 = 330;
constexpr uint16_t NOTE_FS4 = 370;
constexpr uint16_t NOTE_A4 = 440;
constexpr uint16_t NOTE_B4 = 494;

constexpr uint16_t NOTE_MS = 140;
constexpr uint16_t NOTE_GAP_MS = 35;
constexpr uint16_t TOKEN_GAP_MS = 100;
constexpr uint16_t BUTTON_DEBOUNCE_MS = 30;
constexpr size_t SERIAL_LINE_CAPACITY = 64;

enum class OutputMode : uint8_t { MUSICAL, TRANSLATED };

struct NoteEvent {
  uint16_t frequencyHz;
  uint16_t gapAfterMs;
};

struct Phrase {
  const char* id;
  const char* english;
  const char* tokens;
  const NoteEvent* notes;
  uint8_t noteCount;
};

// The final note in each CSP-1 token gets the longer token gap. All sequences
// below were generated from language/specification/csp_v0_1.yaml.
const NoteEvent NOTES_HELLO[] PROGMEM = {
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_FS4, TOKEN_GAP_MS}};

const NoteEvent NOTES_YES[] PROGMEM = {
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_A4, TOKEN_GAP_MS}};

const NoteEvent NOTES_NO[] PROGMEM = {
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_E4, NOTE_GAP_MS},
    {NOTE_B4, TOKEN_GAP_MS}};

const NoteEvent NOTES_THANK_YOU[] PROGMEM = {
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_D4, TOKEN_GAP_MS}};

const NoteEvent NOTES_AMAZE[] PROGMEM = {
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_FS4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_B4, TOKEN_GAP_MS}};

// GRAM.imperative + SOCIAL.please + ACTION.repeat
const NoteEvent NOTES_PLEASE_REPEAT[] PROGMEM = {
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_E4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_A4, NOTE_GAP_MS}, {NOTE_A4, TOKEN_GAP_MS},
    {NOTE_E4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_FS4, NOTE_GAP_MS}, {NOTE_B4, TOKEN_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS}, {NOTE_FS4, NOTE_GAP_MS},
    {NOTE_B4, NOTE_GAP_MS}, {NOTE_A4, TOKEN_GAP_MS}};

// GRAM.declarative + GRAM.negation + ACTION.understand +
// GRAM.agent_role + ENTITY.self
const NoteEvent NOTES_NOT_UNDERSTOOD[] PROGMEM = {
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_E4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_D4, TOKEN_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_E4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_B4, NOTE_GAP_MS}, {NOTE_B4, TOKEN_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_D4, TOKEN_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_E4, NOTE_GAP_MS}, {NOTE_A4, NOTE_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_A4, TOKEN_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_FS4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_E4, TOKEN_GAP_MS}};

// SAFETY.warning + SAFETY.stop_now
const NoteEvent NOTES_STOP[] PROGMEM = {
    {NOTE_C4, NOTE_GAP_MS}, {NOTE_FS4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_D4, NOTE_GAP_MS}, {NOTE_A4, TOKEN_GAP_MS},
    {NOTE_C4, NOTE_GAP_MS}, {NOTE_FS4, NOTE_GAP_MS}, {NOTE_D4, NOTE_GAP_MS},
    {NOTE_FS4, NOTE_GAP_MS}, {NOTE_D4, TOKEN_GAP_MS}};

const Phrase PHRASES[] = {
    {"HELLO", "Hello, friend.", "SOCIAL.hello", NOTES_HELLO,
     sizeof(NOTES_HELLO) / sizeof(NoteEvent)},
    {"YES", "Yes.", "SOCIAL.yes", NOTES_YES,
     sizeof(NOTES_YES) / sizeof(NoteEvent)},
    {"NO", "No.", "SOCIAL.no", NOTES_NO,
     sizeof(NOTES_NO) / sizeof(NoteEvent)},
    {"THANK_YOU", "Thank you.", "SOCIAL.thank_you", NOTES_THANK_YOU,
     sizeof(NOTES_THANK_YOU) / sizeof(NoteEvent)},
    {"AMAZE", "Amaze!", "SOCIAL.amaze", NOTES_AMAZE,
     sizeof(NOTES_AMAZE) / sizeof(NoteEvent)},
    {"PLEASE_REPEAT", "Please repeat that.",
     "GRAM.imperative SOCIAL.please ACTION.repeat", NOTES_PLEASE_REPEAT,
     sizeof(NOTES_PLEASE_REPEAT) / sizeof(NoteEvent)},
    {"NOT_UNDERSTOOD", "I did not understand.",
     "GRAM.declarative GRAM.negation ACTION.understand GRAM.agent_role ENTITY.self",
     NOTES_NOT_UNDERSTOOD, sizeof(NOTES_NOT_UNDERSTOOD) / sizeof(NoteEvent)},
    {"STOP", "Warning. Stop now.", "SAFETY.warning SAFETY.stop_now",
     NOTES_STOP, sizeof(NOTES_STOP) / sizeof(NoteEvent)},
};

constexpr uint8_t PHRASE_COUNT = sizeof(PHRASES) / sizeof(Phrase);

class DebouncedButton {
 public:
  explicit DebouncedButton(uint8_t pin) : pin_(pin) {}

  void begin() {
    pinMode(pin_, INPUT_PULLUP);
    raw_ = digitalRead(pin_);
    stable_ = raw_;
    changedAtMs_ = millis();
  }

  bool fell() {
    const bool sample = digitalRead(pin_);
    const uint32_t now = millis();
    if (sample != raw_) {
      raw_ = sample;
      changedAtMs_ = now;
    }
    if (sample != stable_ && now - changedAtMs_ >= BUTTON_DEBOUNCE_MS) {
      const bool old = stable_;
      stable_ = sample;
      return old == HIGH && stable_ == LOW;
    }
    return false;
  }

 private:
  uint8_t pin_;
  bool raw_ = HIGH;
  bool stable_ = HIGH;
  uint32_t changedAtMs_ = 0;
};

DebouncedButton modeButton(PIN_MODE_BUTTON);
DebouncedButton phraseButton(PIN_PHRASE_BUTTON);

OutputMode outputMode = OutputMode::MUSICAL;
uint8_t selectedPhrase = 0;
const Phrase* activePhrase = nullptr;
uint8_t activeNoteIndex = 0;
bool toneActive = false;
uint32_t nextAudioChangeMs = 0;
char serialLine[SERIAL_LINE_CAPACITY] = {};
size_t serialLineLength = 0;

const char* modeName() {
  return outputMode == OutputMode::TRANSLATED ? "TRANSLATED" : "MUSICAL";
}

void updateStatusLed() {
  digitalWrite(PIN_STATUS_LED,
               outputMode == OutputMode::TRANSLATED ? HIGH : LOW);
}

void emitMode() {
  Serial.print(F("EVENT|MODE|"));
  Serial.println(modeName());
}

void emitSelection() {
  Serial.print(F("EVENT|SELECTED|"));
  Serial.println(PHRASES[selectedPhrase].id);
}

void setMode(OutputMode newMode) {
  outputMode = newMode;
  updateStatusLed();
  emitMode();
}

void toggleMode() {
  setMode(outputMode == OutputMode::MUSICAL ? OutputMode::TRANSLATED
                                            : OutputMode::MUSICAL);
}

void stopPhrase(bool emitStopped) {
  noTone(PIN_PIEZO);
  toneActive = false;
  activeNoteIndex = 0;
  if (activePhrase != nullptr && emitStopped) {
    Serial.print(F("EVENT|STOPPED|"));
    Serial.println(activePhrase->id);
  }
  activePhrase = nullptr;
}

void startPhrase(const Phrase& phrase) {
  stopPhrase(false);
  activePhrase = &phrase;
  activeNoteIndex = 0;
  toneActive = false;
  nextAudioChangeMs = millis();

  // The computer uses this deterministic event to show the exact CSP tokens
  // and, only in translated mode, speak the matching English phrase.
  Serial.print(F("EVENT|PHRASE|"));
  Serial.print(phrase.id);
  Serial.print('|');
  Serial.print(phrase.english);
  Serial.print('|');
  Serial.println(phrase.tokens);
}

void serviceAudio() {
  if (activePhrase == nullptr) return;
  const uint32_t now = millis();
  if (static_cast<int32_t>(now - nextAudioChangeMs) < 0) return;

  const NoteEvent event = {
      pgm_read_word(&activePhrase->notes[activeNoteIndex].frequencyHz),
      pgm_read_word(&activePhrase->notes[activeNoteIndex].gapAfterMs)};

  if (!toneActive) {
    tone(PIN_PIEZO, event.frequencyHz);
    toneActive = true;
    nextAudioChangeMs = now + NOTE_MS;
    return;
  }

  noTone(PIN_PIEZO);
  toneActive = false;
  ++activeNoteIndex;
  if (activeNoteIndex >= activePhrase->noteCount) {
    Serial.print(F("EVENT|DONE|"));
    Serial.println(activePhrase->id);
    activePhrase = nullptr;
    activeNoteIndex = 0;
    return;
  }
  nextAudioChangeMs = now + event.gapAfterMs;
}

int8_t findPhrase(const char* id) {
  for (uint8_t index = 0; index < PHRASE_COUNT; ++index) {
    if (strcmp(id, PHRASES[index].id) == 0) return index;
  }
  return -1;
}

void printHelp() {
  Serial.println(F("EVENT|HELP|MODE MUSICAL"));
  Serial.println(F("EVENT|HELP|MODE TRANSLATED"));
  Serial.println(F("EVENT|HELP|MODE TOGGLE"));
  Serial.println(F("EVENT|HELP|PLAY <phrase_id>"));
  Serial.println(F("EVENT|HELP|LIST"));
  Serial.println(F("EVENT|HELP|STATUS"));
  Serial.println(F("EVENT|HELP|STOP"));
}

void printList() {
  for (uint8_t index = 0; index < PHRASE_COUNT; ++index) {
    Serial.print(F("EVENT|ITEM|"));
    Serial.print(PHRASES[index].id);
    Serial.print('|');
    Serial.println(PHRASES[index].english);
  }
}

void printStatus() {
  Serial.print(F("EVENT|STATUS|MODE="));
  Serial.print(modeName());
  Serial.print(F("|SELECTED="));
  Serial.print(PHRASES[selectedPhrase].id);
  Serial.print(F("|PLAYING="));
  Serial.println(activePhrase == nullptr ? "NONE" : activePhrase->id);
}

void processCommand(char* command) {
  while (*command == ' ') ++command;
  for (char* cursor = command; *cursor != '\0'; ++cursor) {
    if (*cursor >= 'a' && *cursor <= 'z') *cursor -= ('a' - 'A');
  }

  if (strcmp(command, "HELP") == 0) {
    printHelp();
  } else if (strcmp(command, "LIST") == 0) {
    printList();
  } else if (strcmp(command, "STATUS") == 0) {
    printStatus();
  } else if (strcmp(command, "STOP") == 0) {
    stopPhrase(true);
  } else if (strcmp(command, "MODE MUSICAL") == 0) {
    setMode(OutputMode::MUSICAL);
  } else if (strcmp(command, "MODE TRANSLATED") == 0) {
    setMode(OutputMode::TRANSLATED);
  } else if (strcmp(command, "MODE TOGGLE") == 0) {
    toggleMode();
  } else if (strncmp(command, "PLAY ", 5) == 0) {
    const int8_t phraseIndex = findPhrase(command + 5);
    if (phraseIndex < 0) {
      Serial.print(F("EVENT|ERROR|UNKNOWN_PHRASE|"));
      Serial.println(command + 5);
    } else {
      startPhrase(PHRASES[phraseIndex]);
    }
  } else if (*command != '\0') {
    Serial.print(F("EVENT|ERROR|UNKNOWN_COMMAND|"));
    Serial.println(command);
  }
}

void serviceSerial() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());
    if (incoming == '\r') continue;
    if (incoming == '\n') {
      serialLine[serialLineLength] = '\0';
      processCommand(serialLine);
      serialLineLength = 0;
      continue;
    }
    if (serialLineLength + 1 >= SERIAL_LINE_CAPACITY) {
      serialLineLength = 0;
      Serial.println(F("EVENT|ERROR|COMMAND_TOO_LONG"));
      continue;
    }
    serialLine[serialLineLength++] = incoming;
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_PIEZO, OUTPUT);
  pinMode(PIN_STATUS_LED, OUTPUT);
  modeButton.begin();
  phraseButton.begin();
  updateStatusLed();

  // Safe startup: silence, musical-only mode, no movement.
  noTone(PIN_PIEZO);
  Serial.println(F("EVENT|READY|RPA1_BRAIN_0.1|LANGUAGE=CHORDIC|PROTOCOL=CSP-1"));
  emitMode();
  emitSelection();
}

void loop() {
  serviceAudio();
  serviceSerial();

  if (modeButton.fell()) toggleMode();

  if (phraseButton.fell()) {
    startPhrase(PHRASES[selectedPhrase]);
    selectedPhrase = (selectedPhrase + 1) % PHRASE_COUNT;
    emitSelection();
  }
}
