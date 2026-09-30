"use strict";

const protocol = window.RockyBrainProtocol;
const connectButton = document.querySelector("#connect");
const modeButton = document.querySelector("#mode-toggle");
const stopButton = document.querySelector("#stop");
const phraseButtons = document.querySelectorAll("[data-phrase]");
const connectionText = document.querySelector("#connection-state");
const modeText = document.querySelector("#mode-state");
const englishText = document.querySelector("#english-output");
const tokenText = document.querySelector("#token-output");
const logText = document.querySelector("#event-log");
const speakCheckbox = document.querySelector("#speak-english");

let port = null;
let writer = null;
let reader = null;
let currentMode = "MUSICAL";

function appendLog(message) {
  const timestamp = new Date().toLocaleTimeString();
  logText.textContent = `[${timestamp}] ${message}\n${logText.textContent}`.slice(0, 8000);
}

function setConnected(connected) {
  connectionText.textContent = connected ? "Connected" : "Disconnected";
  connectionText.className = connected ? "status good" : "status bad";
  connectButton.textContent = connected ? "Disconnect" : "Connect to Uno";
  modeButton.disabled = !connected;
  stopButton.disabled = !connected;
  phraseButtons.forEach((button) => (button.disabled = !connected));
}

function setMode(mode) {
  currentMode = mode;
  const translated = mode === "TRANSLATED";
  modeText.textContent = translated ? "Translated English" : "Chordic only";
  modeText.className = translated ? "status translated" : "status musical";
  modeButton.textContent = translated
    ? "Switch to Chordic only"
    : "Switch to translated English";
}

function speakEnglish(text) {
  if (!speakCheckbox.checked || currentMode !== "TRANSLATED") return;
  if (!("speechSynthesis" in window)) {
    appendLog("Browser speech synthesis is unavailable; English remains visible as text.");
    return;
  }
  window.speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 0.92;
  utterance.pitch = 0.88;
  window.speechSynthesis.speak(utterance);
}

function handleLine(line) {
  const event = protocol.parseBrainLine(line);
  appendLog(event.raw || event.type);
  if (event.type === "MODE") setMode(event.mode);
  if (event.type === "PHRASE") {
    englishText.textContent = event.english;
    tokenText.textContent = event.tokens;
    speakEnglish(event.english);
  }
  if (event.type === "ERROR") {
    englishText.textContent = `Brain error: ${event.code}`;
  }
}

async function send(command) {
  if (!writer) throw new Error("Uno is not connected");
  await writer.write(new TextEncoder().encode(command));
}

async function readLoop() {
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (port && port.readable) {
      reader = port.readable.getReader();
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split(/\r?\n/);
          buffer = lines.pop();
          lines.forEach(handleLine);
        }
      } finally {
        reader.releaseLock();
        reader = null;
      }
    }
  } catch (error) {
    appendLog(`Read stopped: ${error.message}`);
  }
}

async function connect() {
  if (!("serial" in navigator)) {
    throw new Error("Use desktop Chrome or Edge; this browser lacks Web Serial.");
  }
  port = await navigator.serial.requestPort();
  await port.open({ baudRate: 115200 });
  writer = port.writable.getWriter();
  setConnected(true);
  appendLog("Connected at 115200 baud");
  readLoop();
  // Opening a serial connection resets most Uno boards. Give setup() time to run.
  await new Promise((resolve) => setTimeout(resolve, 1800));
  await send("STATUS\n");
}

async function disconnect() {
  if (!port) return;
  try {
    if (reader) await reader.cancel();
    if (writer) {
      writer.releaseLock();
      writer = null;
    }
    await port.close();
  } finally {
    port = null;
    setConnected(false);
    appendLog("Disconnected");
  }
}

connectButton.addEventListener("click", async () => {
  try {
    if (port) await disconnect();
    else await connect();
  } catch (error) {
    appendLog(error.message);
    await disconnect();
  }
});

modeButton.addEventListener("click", async () => {
  const target = currentMode === "MUSICAL" ? "TRANSLATED" : "MUSICAL";
  await send(protocol.modeCommand(target));
});

stopButton.addEventListener("click", () => send("STOP\n"));

phraseButtons.forEach((button) => {
  button.addEventListener("click", () => send(protocol.playCommand(button.dataset.phrase)));
});

window.addEventListener("beforeunload", () => {
  if (writer) writer.releaseLock();
});

setConnected(false);
setMode("MUSICAL");
