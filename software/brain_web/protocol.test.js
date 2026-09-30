"use strict";

const assert = require("node:assert/strict");
const protocol = require("./protocol.js");

assert.deepEqual(protocol.parseBrainLine("EVENT|MODE|TRANSLATED"), {
  type: "MODE",
  mode: "TRANSLATED",
  raw: "EVENT|MODE|TRANSLATED",
});

assert.deepEqual(protocol.parseBrainLine("EVENT|PHRASE|HELLO|Hello, friend.|SOCIAL.hello"), {
  type: "PHRASE",
  id: "HELLO",
  english: "Hello, friend.",
  tokens: "SOCIAL.hello",
  raw: "EVENT|PHRASE|HELLO|Hello, friend.|SOCIAL.hello",
});

assert.equal(protocol.modeCommand("translated"), "MODE TRANSLATED\n");
assert.equal(protocol.playCommand("hello"), "PLAY HELLO\n");
assert.throws(() => protocol.modeCommand("unsafe"));
assert.throws(() => protocol.playCommand("made_up"));

console.log("Rocky Brain protocol tests passed");
