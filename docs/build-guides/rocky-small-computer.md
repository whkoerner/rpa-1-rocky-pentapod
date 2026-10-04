# Preparing Rocky for a small onboard computer

**Do not buy a board from this page yet.** First establish a total budget, usable internal width × depth × height (including plugs/cooling), available power, and acceptable reply delay. Software configuration and repeatable desktop tests can be finished without those answers.

Specifications below were checked against manufacturer pages on 2026-10-04 UTC (2026-10-03 Los Angeles). None of these boards has run this Rocky upgrade here. No model speed, thermal performance, battery life or complete-system price was measured.

## Standalone versus PC-assisted

| Mode | Where inference runs | What remains required |
|---|---|---|
| Standalone | On Rocky's onboard computer, using locally stored runtime/model | No internet and no Windows PC needed after provisioning. Must fit RAM/storage/power/cooling and meet response-time target. |
| PC-assisted | On the Windows PC; onboard computer handles Rocky/terminal/audio over the local network | Can need **no internet**, but still needs the PC awake, its inference service running and a working LAN. This is not standalone. |

Both use the same brain/safety/communication chain. The local provider currently accepts only numeric loopback. This upgrade does not open an inference server to the LAN, change a firewall, or add unauthenticated remote hardware commands.

`software/rocky/config/rocky-pi-standalone.example.json` is a portable candidate using pygame audio and loopback Ollama. `qwen3:4b` there is an **unbenchmarked test candidate**, not an assertion that Pi performance is adequate or a download request. Select an already provisioned local model only after memory/latency testing.

`software/rocky/config/rocky-pc-assisted.example.json` uses loopback port 11435. It requires a separately established authenticated tunnel from the onboard computer to the PC's loopback Ollama port 11434. A typical OpenSSH forwarding shape is:

```sh
ssh -N -L 127.0.0.1:11435:127.0.0.1:11434 PC_USER@PC_LAN_ADDRESS
```

Replace the two placeholders; the PC must already have an authorized SSH server/account configured. This command does not set one up. Use a trusted private LAN and normal host-key verification. It is a deployment plan, **not a tested end-to-end feature or a guarantee that your Windows PC has SSH enabled**. Port conflict, sleep, disconnect or tunnel failure must produce a provider failure, never a fallback to cloud. Model inference stays on the PC; GUI/audio stays on the onboard computer. Any future native LAN adapter needs separate authenticated transport and disconnect tests.

## Three realistic candidates, not a shopping list

| Candidate | Official RAM/CPU and bare dimensions | Storage, power, cooling and extra parts | Expected role/limitations (engineering estimates) |
|---|---|---|---|
| Raspberry Pi 5, considering 8GB or 16GB variants | Quad-core Cortex-A76 2.4GHz; manufacturer offers RAM variants up to 16GB; PCB approximately 85 × 56mm | microSD; optional SSD needs adapter/enclosure. Recommended 5V/5A USB-C supply. Plan active cooler, ventilation, mounting/case, USB audio adapter or USB speaker, cabling and speaker power. | Easiest of these for a standalone experiment. CPU inference may be slow; 8GB has less model/context headroom than 16GB. Do not assume the Windows Qwen3 8B experience transfers. |
| Raspberry Pi Zero 2 W | Quad-core Cortex-A53 1GHz, 512MB RAM; 65 × 30mm | microSD, micro-USB power, manufacturer recommends 2A supply capacity; USB OTG adapter/hub if needed, USB audio/speaker, mount and ventilation. | Small PC-assisted client candidate, not a viable host for the existing multi-GB Qwen3 8B model. Even Python WAV synthesis/startup latency needs measurement. 2.4GHz Wi-Fi and limited ports/RAM constrain it. |
| Raspberry Pi Compute Module 5 | Quad-core Cortex-A76 2.4GHz; 2/4/8/16GB options; module 55 × 40 × 4.7mm | eMMC 0/16/32/64GB options; **carrier board required**, plus appropriate supply, connectors, cooler, audio/speaker and mount. Lite needs external storage. Carrier/power/cooling footprint must be added to the module dimensions. | Embedded alternative once body geometry is fixed. Similar CPU class to Pi 5, not inherently faster. Carrier cost/integration complexity can outweigh the smaller module. Not the first beginner purchase today. |

Supply ratings are provisioning requirements, **not measured continuous draw**. Pi 5's recommended supply is marketed as 27W; that does not mean Rocky consumes 27W continuously. A battery pack/regulator, protection, speaker power and charging solution would be separate design/measurement work. This upgrade specifies no battery wiring.

Total cost must include **board + RAM variant + boot/model storage + suitable power supply + cooling + audio output/speaker + adapters/cables + mounting**, and CM5 also requires a carrier. Board-only prices are not comparable total costs; no price quote or cost total is asserted here. For PC-assisted use, the existing PC and LAN are also required resources. Get current local quotes only after the budget/body/speed constraints are known.

Official sources:

- [Pi 5 specification, RAM, power and cooling](https://www.raspberrypi.com/products/raspberry-pi-5/)
- [Pi 5 mechanical drawing](https://pip.raspberrypi.com/documents/RP-008347-DS-1-raspberry-pi-5-mechanical-drawing.pdf)
- [Zero 2 W processor, memory and dimensions](https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/)
- [Manufacturer power supply table, including Zero 2 W](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#power-supply)
- [CM5 specification and memory/storage choices](https://www.raspberrypi.com/products/compute-module-5/)
- [CM5 datasheet for carrier/power/thermal design](https://pip.raspberrypi.com/documents/RP-008180-DS-cm5-datasheet.pdf)

## Code and configuration transfer

Use Git to transfer/update **code**, never a directory mirror of the Windows installation. Current full-source checkout is required because the CSP YAML loader is not wheel-independent.

1. Record `git rev-parse HEAD` for the Windows-tested version. Fetch the same repository on the target and explicitly check out that reviewed commit/branch. For a subsequent clean-branch update, `git fetch origin` then `git merge --ff-only origin/feat/rocky-desktop-v1-1`. Stop if the target has local edits or diverged commits.
2. Recreate the target Python environment. The repository unfortunately still contains a historical tracked Windows `.venv`; ignore it on Linux and do not run it. Use a fresh `.venv-rocky` on the target:

   ```sh
   python3 -m venv .venv-rocky
   .venv-rocky/bin/python -m pip install -e '.[audio]'
   ```

   Python 3.10+ and a functioning Linux audio stack are required. OS-level packages may need initial provisioning. Installation can need internet; runtime tests later establish offline operation.
3. Export **only the selected runtime configuration and personality**, not the whole `.rpa1` directory. Example Windows PowerShell for the default profile pair (use a new export directory name if it already exists):

   ```powershell
   $rockyExport = Join-Path $env:USERPROFILE 'Rocky-config-export'
   New-Item -ItemType Directory -Path $rockyExport -ErrorAction Stop
   Copy-Item "$env:USERPROFILE\.rpa1\settings\rocky.json" $rockyExport
   Copy-Item "$env:USERPROFILE\.rpa1\settings\personality.json" $rockyExport
   ```

   If you selected another profile, export that exact file instead and update `personality_profile` in the **export copy** to its relative filename. Review the profile for personal text before transfer. Use a USB stick or an authenticated file transfer you control. Keep the original Windows files.
4. On Linux, copy the reviewed pair into `~/.rpa1/settings` without replacing an existing setup without review. Set `audio_backend` to `pygame`; retain a relative profile path. Compare one of the portable examples above to set the provider port/model deliberately. Settings validation will identify unsupported fields/types.
5. Provision model weights using the runtime's documented installation process **separately**. Do not blindly sync Windows model stores. Do not transfer venvs, `.rocky-python-path.txt`, secrets, recordings/WAVs, Ollama logs/databases, private history, or output folders. Offline provisioning can use predownloaded compatible packages/models if their runtime/license permits it.

## Deployment acceptance checklist

- [ ] Record OS/CPU/RAM/storage, code SHA, Python/runtime/model versions, settings used and audio output device.
- [ ] Run `.venv-rocky/bin/python scripts/run_tests.py`; record Python results and any unavailable Node check separately.
- [ ] Run `.venv-rocky/bin/python -m rocky check --provider dummy`, then `audio-test`; distinguish generated WAV from actual listening.
- [ ] Measure cold and warm reply time, worst of several turns, peak memory/swap, render time, playback delay, sustained temperature/throttling and input/stop responsiveness in the intended enclosure. These measurements do not exist yet.
- [ ] For standalone, turn off internet **and the PC**, restart runtime/Rocky, and repeat multi-turn/audio/stop tests. Do not treat cached one-turn success as complete offline acceptance.
- [ ] For PC-assisted, disconnect internet while preserving the LAN; repeat chat. Then disconnect LAN or stop the tunnel and verify a bounded error with local stop still working. State explicitly that the PC remains necessary.
- [ ] Verify no model tools, new hardware permissions or physical success claims are interpreted as robot state. No motor/sensor backend is part of this deployment.
- [ ] Compare measured worst-case latency, memory headroom, full dimensions and full cost to the user's limits before choosing/buying hardware.

Replaceable seams remain `AIProvider`/`LocalAIProvider`, `TerminalInput` (future `SpeechInput` protocol only), `AudioPlayer` and `HardwareInterface`. No framework or new hardware protocol is needed for this preparation.
