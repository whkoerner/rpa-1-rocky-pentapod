// RPA-1 Rocky Communication Core v0.1
// Target: Arduino Uno/Nano-class board, passive piezo, common-cathode RGB LED.
// Safety: USB/5 V logic only. Do not connect motors or a loud speaker directly.

#include <Arduino.h>

constexpr uint8_t PIN_TRANSLATION_BUTTON = 2;
constexpr uint8_t PIN_PHRASE_BUTTON = 4;
constexpr uint8_t PIN_LED_R = 5;
constexpr uint8_t PIN_LED_G = 6;
constexpr uint8_t PIN_LED_B = 10;
constexpr uint8_t PIN_PIEZO = 9;

constexpr uint16_t NOTE_C4 = 262;
constexpr uint16_t NOTE_D4 = 294;
constexpr uint16_t NOTE_E4 = 330;
constexpr uint16_t NOTE_FS4 = 370;
constexpr uint16_t NOTE_A4 = 440;

constexpr uint16_t TOKEN_NOTE_MS = 140;
constexpr uint16_t TOKEN_GAP_MS = 35;

struct Step {
  uint16_t frequencyHz;
  uint16_t durationMs;
  uint16_t gapMs;
};

// CSP-1 token sequences from language/specification/csp_v0_1.yaml.
const Step PHRASE_HELLO[] = {
    {NOTE_E4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_A4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_D4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_D4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_FS4, TOKEN_NOTE_MS, 120},
};

const Step PHRASE_YES[] = {
    {NOTE_E4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_A4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_E4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_D4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_A4, TOKEN_NOTE_MS, 120},
};

const Step PHRASE_QUESTION[] = {
    {NOTE_D4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_E4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_D4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_E4, TOKEN_NOTE_MS, TOKEN_GAP_MS},
    {NOTE_E4, TOKEN_NOTE_MS, 120},
};

const Step PHRASE_WARNING[] = {
    {NOTE_C4, 180, 45},
    {NOTE_FS4, 180, 45},
    {NOTE_D4, 180, 45},
    {NOTE_D4, 180, 45},
    {NOTE_A4, 220, 160},
};

const Step CONFIRM_ON[] = {{NOTE_D4, 90, 30}, {NOTE_A4, 140, 100}};
const Step CONFIRM_OFF[] = {{NOTE_A4, 90, 30}, {NOTE_D4, 140, 100}};

struct Phrase {
  const Step* steps;
  uint8_t count;
  const char* label;
};

const Phrase PHRASES[] = {
    {PHRASE_HELLO, sizeof(PHRASE_HELLO) / sizeof(Step), "SOCIAL.hello"},
    {PHRASE_YES, sizeof(PHRASE_YES) / sizeof(Step), "SOCIAL.yes"},
    {PHRASE_QUESTION, sizeof(PHRASE_QUESTION) / sizeof(Step), "GRAM.yes_no_question"},
    {PHRASE_WARNING, sizeof(PHRASE_WARNING) / sizeof(Step), "SAFETY.warning"},
};

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
    if (sample != stable_ && now - changedAtMs_ >= 25) {
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

DebouncedButton translationButton(PIN_TRANSLATION_BUTTON);
DebouncedButton phraseButton(PIN_PHRASE_BUTTON);

bool translationMode = false;
uint8_t selectedPhrase = 0;

const Step* activeSteps = nullptr;
uint8_t activeCount = 0;
uint8_t activeIndex = 0;
bool playingTone = false;
uint32_t nextChangeMs = 0;

void setRgb(uint8_t red, uint8_t green, uint8_t blue) {
  analogWrite(PIN_LED_R, red);
  analogWrite(PIN_LED_G, green);
  analogWrite(PIN_LED_B, blue);
}

void updateStatusLed() {
  if (activeSteps != nullptr) {
    setRgb(80, 0, 120);  // Phrase in progress: violet.
  } else if (translationMode) {
    setRgb(0, 80, 20);   // Translation enabled: green.
  } else {
    setRgb(0, 10, 70);   // Translation disabled: blue.
  }
}

void startPhrase(const Step* steps, uint8_t count) {
  if (steps == nullptr || count == 0) return;
  noTone(PIN_PIEZO);
  activeSteps = steps;
  activeCount = count;
  activeIndex = 0;
  playingTone = false;
  nextChangeMs = millis();
  updateStatusLed();
}

void servicePhrasePlayer() {
  if (activeSteps == nullptr) return;
  const uint32_t now = millis();
  if (static_cast<int32_t>(now - nextChangeMs) < 0) return;

  const Step& step = activeSteps[activeIndex];
  if (!playingTone) {
    tone(PIN_PIEZO, step.frequencyHz);
    playingTone = true;
    nextChangeMs = now + step.durationMs;
    return;
  }

  noTone(PIN_PIEZO);
  playingTone = false;
  ++activeIndex;
  if (activeIndex >= activeCount) {
    activeSteps = nullptr;
    activeCount = 0;
    activeIndex = 0;
    updateStatusLed();
    return;
  }
  nextChangeMs = now + step.gapMs;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED_R, OUTPUT);
  pinMode(PIN_LED_G, OUTPUT);
  pinMode(PIN_LED_B, OUTPUT);
  pinMode(PIN_PIEZO, OUTPUT);
  translationButton.begin();
  phraseButton.begin();
  updateStatusLed();

  Serial.println(F("RPA-1 Communicator v0.1 ready"));
  Serial.println(F("Translation mode: OFF"));
}

void loop() {
  servicePhrasePlayer();

  if (translationButton.fell()) {
    translationMode = !translationMode;
    Serial.print(F("Translation mode: "));
    Serial.println(translationMode ? F("ON") : F("OFF"));
    if (translationMode) {
      startPhrase(CONFIRM_ON, sizeof(CONFIRM_ON) / sizeof(Step));
    } else {
      startPhrase(CONFIRM_OFF, sizeof(CONFIRM_OFF) / sizeof(Step));
    }
  }

  if (phraseButton.fell()) {
    const Phrase& phrase = PHRASES[selectedPhrase];
    Serial.print(F("Playing: "));
    Serial.println(phrase.label);
    startPhrase(phrase.steps, phrase.count);
    selectedPhrase = (selectedPhrase + 1) % (sizeof(PHRASES) / sizeof(Phrase));
  }
}
