#ifndef RPA1_CSP1_WIRE_H
#define RPA1_CSP1_WIRE_H

#include <Arduino.h>

const byte CSP1_MAX_MESSAGE_LENGTH = 63;
const byte CSP1_MAX_ARGUMENT_LENGTH = 16;

enum Csp1Intent {
  CSP1_SOCIAL_HELLO,
  CSP1_RESPONSE_YES,
  CSP1_RESPONSE_NO,
  CSP1_REQUEST_HELP,
  CSP1_SOCIAL_THANKS,
  CSP1_SOCIAL_GOODBYE,
  CSP1_UNKNOWN
};

enum Csp1Error {
  CSP1_OK,
  CSP1_ERR_FORMAT,
  CSP1_ERR_VERSION,
  CSP1_ERR_INTENT,
  CSP1_ERR_ARGUMENT,
  CSP1_ERR_TOO_LONG
};

struct Csp1Message {
  Csp1Intent intent;
  char argument[CSP1_MAX_ARGUMENT_LENGTH + 1];
};

Csp1Error csp1Decode(char* line, Csp1Message& output);
const __FlashStringHelper* csp1IntentName(Csp1Intent intent);
const __FlashStringHelper* csp1CanonicalText(Csp1Intent intent);
const __FlashStringHelper* csp1ChordicToken(Csp1Intent intent);

#endif
