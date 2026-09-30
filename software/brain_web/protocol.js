(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.RockyBrainProtocol = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const VALID_MODES = new Set(["MUSICAL", "TRANSLATED"]);
  const PHRASE_IDS = new Set([
    "HELLO",
    "YES",
    "NO",
    "THANK_YOU",
    "AMAZE",
    "PLEASE_REPEAT",
    "NOT_UNDERSTOOD",
    "STOP",
  ]);

  function parseBrainLine(rawLine) {
    const raw = String(rawLine || "").trim();
    if (!raw) return { type: "EMPTY", raw };
    const fields = raw.split("|");
    if (fields[0] !== "EVENT" || fields.length < 2) {
      return { type: "MALFORMED", raw };
    }
    const type = fields[1];
    if (type === "MODE") return { type, mode: fields[2], raw };
    if (type === "PHRASE") {
      return {
        type,
        id: fields[2],
        english: fields[3],
        tokens: fields.slice(4).join("|"),
        raw,
      };
    }
    if (type === "SELECTED" || type === "DONE" || type === "STOPPED") {
      return { type, id: fields[2], raw };
    }
    if (type === "ERROR") {
      return { type, code: fields[2], detail: fields.slice(3).join("|"), raw };
    }
    return { type, fields: fields.slice(2), raw };
  }

  function modeCommand(mode) {
    const normalized = String(mode || "").toUpperCase();
    if (!VALID_MODES.has(normalized)) throw new Error("Invalid brain mode");
    return `MODE ${normalized}\n`;
  }

  function playCommand(id) {
    const normalized = String(id || "").toUpperCase();
    if (!PHRASE_IDS.has(normalized)) throw new Error("Unknown phrase ID");
    return `PLAY ${normalized}\n`;
  }

  return { parseBrainLine, modeCommand, playCommand, VALID_MODES, PHRASE_IDS };
});
