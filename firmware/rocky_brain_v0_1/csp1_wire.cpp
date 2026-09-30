#include "csp1_wire.h"

#include <string.h>

static bool validIntentSyntax(const char* value) {
  if (value == nullptr || value[0] == '\0') return false;

  byte dots = 0;
  for (const char* p = value; *p != '\0'; ++p) {
    if (*p == '.') {
      dots++;
      if (p == value || *(p + 1) == '\0') return false;
    } else if (*p < 'A' || *p > 'Z') {
      return false;
    }
  }
  return dots == 1;
}

static bool validArgumentSyntax(const char* value) {
  for (const char* p = value; *p != '\0'; ++p) {
    const bool upper = *p >= 'A' && *p <= 'Z';
    const bool digit = *p >= '0' && *p <= '9';
    if (!upper && !digit && *p != '_') return false;
  }
  return true;
}

static Csp1Intent parseIntent(const char* value) {
  if (strcmp(value, "SOCIAL.HELLO") == 0) return CSP1_SOCIAL_HELLO;
  if (strcmp(value, "RESPONSE.YES") == 0) return CSP1_RESPONSE_YES;
  if (strcmp(value, "RESPONSE.NO") == 0) return CSP1_RESPONSE_NO;
  if (strcmp(value, "REQUEST.HELP") == 0) return CSP1_REQUEST_HELP;
  if (strcmp(value, "SOCIAL.THANKS") == 0) return CSP1_SOCIAL_THANKS;
  if (strcmp(value, "SOCIAL.GOODBYE") == 0) return CSP1_SOCIAL_GOODBYE;
  return CSP1_UNKNOWN;
}

Csp1Error csp1Decode(char* line, Csp1Message& output) {
  output.intent = CSP1_UNKNOWN;
  output.argument[0] = '\0';

  if (line == nullptr) return CSP1_ERR_FORMAT;

  size_t length = strlen(line);
  while (length > 0 && (line[length - 1] == '\n' || line[length - 1] == '\r')) {
    line[--length] = '\0';
  }

  if (length > CSP1_MAX_MESSAGE_LENGTH) return CSP1_ERR_TOO_LONG;

  char* first = strchr(line, '|');
  if (first == nullptr) return CSP1_ERR_FORMAT;

  char* second = strchr(first + 1, '|');
  if (second == nullptr) return CSP1_ERR_FORMAT;

  if (strchr(second + 1, '|') != nullptr) return CSP1_ERR_FORMAT;

  *first = '\0';
  *second = '\0';

  const char* version = line;
  const char* intentText = first + 1;
  const char* argument = second + 1;

  if (strcmp(version, "C1") != 0) return CSP1_ERR_VERSION;
  if (!validIntentSyntax(intentText)) return CSP1_ERR_INTENT;

  const Csp1Intent intent = parseIntent(intentText);
  if (intent == CSP1_UNKNOWN) return CSP1_ERR_INTENT;

  if (!validArgumentSyntax(argument)) return CSP1_ERR_ARGUMENT;
  if (argument[0] != '\0') return CSP1_ERR_ARGUMENT;

  output.intent = intent;
  output.argument[0] = '\0';
  return CSP1_OK;
}

const __FlashStringHelper* csp1IntentName(Csp1Intent intent) {
  switch (intent) {
    case CSP1_SOCIAL_HELLO: return F("SOCIAL.HELLO");
    case CSP1_RESPONSE_YES: return F("RESPONSE.YES");
    case CSP1_RESPONSE_NO: return F("RESPONSE.NO");
    case CSP1_REQUEST_HELP: return F("REQUEST.HELP");
    case CSP1_SOCIAL_THANKS: return F("SOCIAL.THANKS");
    case CSP1_SOCIAL_GOODBYE: return F("SOCIAL.GOODBYE");
    default: return F("UNKNOWN");
  }
}

const __FlashStringHelper* csp1CanonicalText(Csp1Intent intent) {
  switch (intent) {
    case CSP1_SOCIAL_HELLO: return F("Hello.");
    case CSP1_RESPONSE_YES: return F("Yes.");
    case CSP1_RESPONSE_NO: return F("No.");
    case CSP1_REQUEST_HELP: return F("Help.");
    case CSP1_SOCIAL_THANKS: return F("Thank you.");
    case CSP1_SOCIAL_GOODBYE: return F("Goodbye.");
    default: return F("");
  }
}

const __FlashStringHelper* csp1ChordicToken(Csp1Intent intent) {
  switch (intent) {
    case CSP1_SOCIAL_HELLO: return F("SOCIAL.hello");
    case CSP1_RESPONSE_YES: return F("SOCIAL.yes");
    case CSP1_RESPONSE_NO: return F("SOCIAL.no");
    case CSP1_REQUEST_HELP: return F("ACTION.help");
    case CSP1_SOCIAL_THANKS: return F("SOCIAL.thank_you");
    case CSP1_SOCIAL_GOODBYE: return F("SOCIAL.goodbye");
    default: return F("");
  }
}
