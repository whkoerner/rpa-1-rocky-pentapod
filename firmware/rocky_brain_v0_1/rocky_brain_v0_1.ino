// RPA-1 Rocky Brain v0.1
// Target: Elegoo/Arduino Uno R3, two momentary buttons, passive buzzer, USB computer.
// Language: Chordic, encoded with CSP-1.
// Scope: no motors, internet, AI, Raspberry Pi, microphone, or external libraries.

#include <Arduino.h>

const byte MODE_BUTTON_PIN = 2;
const byte SPEAK_BUTTON_PIN = 3;
const byte BUZZER_PIN = 9;

const unsigned long DEBOUNCE_MS = 200;

bool translationMode = false;
bool previousModeButton = HIGH;
bool previousSpeakButton = HIGH;
unsigned long lastModePress = 0;
unsigned long lastSpeakPress = 0;
byte currentMessage = 0;

struct NoteEvent {
  unsigned int frequencyHz;
  unsigned int durationMs;
};

struct Message {
  const char* name;
  const char* token;
  const char* english;
  const NoteEvent* notes;
  byte noteCount;
};

// CSP-1 pitch symbols from language/specification/csp_v0_1.yaml.
// Names include NOTE_ so NOTE_A4 does not collide with Arduino's A4 pin macro.
// Integer frequencies are rounded for Arduino tone().
const unsigned int NOTE_D4 = 294;
const unsigned int NOTE_E4 = 330;
const unsigned int NOTE_FS4 = 370;
const unsigned int NOTE_A4 = 440;
const unsigned int NOTE_B4 = 494;

const unsigned int NOTE_MS = 140;
const unsigned int GAP_MS = 35;

const NoteEvent NOTES_HELLO[] = {
  {NOTE_E4, NOTE_MS}, {NOTE_A4, NOTE_MS}, {NOTE_D4, NOTE_MS},
  {NOTE_D4, NOTE_MS}, {NOTE_FS4, NOTE_MS}
};

const NoteEvent NOTES_YES[] = {
  {NOTE_E4, NOTE_MS}, {NOTE_A4, NOTE_MS}, {NOTE_E4, NOTE_MS},
  {NOTE_D4, NOTE_MS}, {NOTE_A4, NOTE_MS}
};

const NoteEvent NOTES_NO[] = {
  {NOTE_E4, NOTE_MS}, {NOTE_A4, NOTE_MS}, {NOTE_E4, NOTE_MS},
  {NOTE_E4, NOTE_MS}, {NOTE_B4, NOTE_MS}
};

const NoteEvent NOTES_HELP[] = {
  {NOTE_D4, NOTE_MS}, {NOTE_A4, NOTE_MS}, {NOTE_A4, NOTE_MS},
  {NOTE_FS4, NOTE_MS}, {NOTE_FS4, NOTE_MS}
};

const NoteEvent NOTES_THANK_YOU[] = {
  {NOTE_E4, NOTE_MS}, {NOTE_A4, NOTE_MS}, {NOTE_D4, NOTE_MS},
  {NOTE_A4, NOTE_MS}, {NOTE_D4, NOTE_MS}
};

const NoteEvent NOTES_GOODBYE[] = {
  {NOTE_E4, NOTE_MS}, {NOTE_A4, NOTE_MS}, {NOTE_D4, NOTE_MS},
  {NOTE_E4, NOTE_MS}, {NOTE_A4, NOTE_MS}
};

const Message MESSAGES[] = {
  {"HELLO", "SOCIAL.hello", "Hello", NOTES_HELLO, 5},
  {"YES", "SOCIAL.yes", "Yes", NOTES_YES, 5},
  {"NO", "SOCIAL.no", "No", NOTES_NO, 5},
  {"HELP", "ACTION.help", "Help", NOTES_HELP, 5},
  {"THANK_YOU", "SOCIAL.thank_you", "Thank you", NOTES_THANK_YOU, 5},
  {"GOODBYE", "SOCIAL.goodbye", "Goodbye", NOTES_GOODBYE, 5}
};

const byte MESSAGE_COUNT = sizeof(MESSAGES) / sizeof(MESSAGES[0]);

void printMode() {
  if (translationMode) {
    Serial.println(F("MODE: TRANSLATION"));
  } else {
    Serial.println(F("MODE: COMMUNICATION"));
  }
}

void printMessage(const Message& message) {
  Serial.print(F("CSP-1: "));
  Serial.println(message.token);

  if (translationMode) {
    Serial.print(F("ENGLISH: "));
    Serial.println(message.english);
  }
}

void playMessage(byte index) {
  if (index >= MESSAGE_COUNT) return;

  const Message& message = MESSAGES[index];
  printMessage(message);

  for (byte i = 0; i < message.noteCount; ++i) {
    tone(BUZZER_PIN, message.notes[i].frequencyHz, message.notes[i].durationMs);
    delay(message.notes[i].durationMs);
    noTone(BUZZER_PIN);
    delay(GAP_MS);
  }
}

void toggleMode() {
  translationMode = !translationMode;
  printMode();
}

void playNext() {
  playMessage(currentMessage);
  currentMessage++;
  if (currentMessage >= MESSAGE_COUNT) {
    currentMessage = 0;
  }
}

void checkButtons() {
  const bool modeButton = digitalRead(MODE_BUTTON_PIN);
  const bool speakButton = digitalRead(SPEAK_BUTTON_PIN);
  const unsigned long now = millis();

  if (modeButton == LOW &&
      previousModeButton == HIGH &&
      now - lastModePress > DEBOUNCE_MS) {
    lastModePress = now;
    toggleMode();
  }

  if (speakButton == LOW &&
      previousSpeakButton == HIGH &&
      now - lastSpeakPress > DEBOUNCE_MS) {
    lastSpeakPress = now;
    playNext();
  }

  previousModeButton = modeButton;
  previousSpeakButton = speakButton;
}

void printHelp() {
  Serial.println(F("Commands:"));
  Serial.println(F("  HELP"));
  Serial.println(F("  STATUS"));
  Serial.println(F("  LIST"));
  Serial.println(F("  NEXT"));
  Serial.println(F("  MODE COMM"));
  Serial.println(F("  MODE TRANSLATE"));
  Serial.println(F("  SAY HELLO"));
  Serial.println(F("  SAY YES"));
  Serial.println(F("  SAY NO"));
  Serial.println(F("  SAY HELP"));
  Serial.println(F("  SAY THANK_YOU"));
  Serial.println(F("  SAY GOODBYE"));
}

void printStatus() {
  Serial.println(F("RPA-1 ROCKY BRAIN v0.1"));
  printMode();
  Serial.print(F("NEXT: "));
  Serial.println(MESSAGES[currentMessage].name);
}

void printList() {
  Serial.println(F("Chordic / CSP-1 beginner vocabulary:"));
  for (byte i = 0; i < MESSAGE_COUNT; ++i) {
    Serial.print(MESSAGES[i].name);
    Serial.print(F(" = "));
    Serial.print(MESSAGES[i].token);
    Serial.print(F(" = "));
    Serial.println(MESSAGES[i].english);
  }
}

int findMessage(String name) {
  name.trim();
  name.toUpperCase();

  for (byte i = 0; i < MESSAGE_COUNT; ++i) {
    if (name == MESSAGES[i].name) {
      return i;
    }
  }
  return -1;
}

void processCommand(String command) {
  command.trim();
  command.toUpperCase();

  if (command.length() == 0) return;

  if (command == "HELP") {
    printHelp();
  } else if (command == "STATUS") {
    printStatus();
  } else if (command == "LIST") {
    printList();
  } else if (command == "NEXT") {
    playNext();
  } else if (command == "MODE COMM") {
    translationMode = false;
    printMode();
  } else if (command == "MODE TRANSLATE") {
    translationMode = true;
    printMode();
  } else if (command.startsWith("SAY ")) {
    const int index = findMessage(command.substring(4));
    if (index < 0) {
      Serial.println(F("ERROR: unknown message. Type LIST."));
    } else {
      playMessage((byte)index);
    }
  } else {
    Serial.println(F("ERROR: unknown command. Type HELP."));
  }
}

void checkSerial() {
  if (Serial.available() <= 0) return;
  String command = Serial.readStringUntil('\n');
  processCommand(command);
}

void setup() {
  pinMode(MODE_BUTTON_PIN, INPUT_PULLUP);
  pinMode(SPEAK_BUTTON_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);

  noTone(BUZZER_PIN);
  Serial.begin(9600);
  Serial.setTimeout(100);

  delay(300);
  Serial.println();
  Serial.println(F("=============================="));
  Serial.println(F("RPA-1 ROCKY BRAIN v0.1"));
  Serial.println(F("Chordic / CSP-1"));
  Serial.println(F("=============================="));
  printMode();
  Serial.println(F("Type HELP for commands."));
}

void loop() {
  checkButtons();
  checkSerial();
}
