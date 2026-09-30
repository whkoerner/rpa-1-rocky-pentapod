# AI-Assisted Rocky Project Workflow

This file explains which AI model to use, how to split the Rocky project into small tasks, and which six questions are reserved for the hardest design decisions.

The goal is to keep the project understandable, affordable, and visibly student-built. AI may help with planning, code review, documentation, and debugging, but every result must be tested and labeled as an assumption or demonstrated result.

## Model and thinking rules

Use the least expensive model that can do the job.

| Task | Recommended model | Thinking |
|---|---|---|
| Small wording change, README edit, simple explanation | GPT-5.6 Luna or the fastest available standard model | Low |
| One-file Arduino/Python change, beginner instructions, test checklist | GPT-5.6 Terra or GPT-6 Luna | Medium |
| Multi-file software feature, hardware/software interface, simulation integration | GPT-5.6 Sol or GPT-6 Sol | Medium |
| Safety-critical architecture, actuator trade study, full-system conflict, or major redesign | GPT-6 Astra | Medium or High, only when necessary |

Model names and limits depend on the account and workspace. The model picker and Settings > Usage are the source of truth. Work and Codex usage can have both five-hour and weekly limits, and higher reasoning or larger tasks generally use more allowance. Check usage before a large task. OpenAI describes Astra as the model for especially demanding work, Sol as the capability/efficiency balance, Terra as the everyday balance, and Luna as the fast economical option.

Practical rule for this project:

1. Use Luna for narrow, repetitive tasks.
2. Use Terra/standard Medium for most prompts in this file.
3. Use Sol Medium when the prompt touches several files or needs real engineering judgment.
4. Do not use Astra for routine coding, formatting, shopping lists, or beginner explanations.
5. Keep the six Astra prompts below unused until the problem cannot be safely divided into smaller questions.

## Required prompt wrapper

Add this short wrapper to every prompt:

> I am a freshman electrical-engineering student building RPA-1, a low-cost Rocky-inspired five-limb robot. Stay within the stated scope. Do not invent test results, measurements, prices, or movie facts. Prefer inexpensive, repairable, beginner-buildable parts. Give exact file paths, commands, wiring or interfaces, tests, acceptance criteria, safety risks, and a short next step. If information is missing, state the assumption instead of expanding the project.

After every AI response, ask:

> Convert your answer into a small GitHub-ready change. List files to add or edit, explain each change in beginner language, and give a test I can run before committing it.

## Project prompt sequence

Run these in order. Do not ask one model to solve all of them at once.

### 00 — Repository navigation and project rules

Ask the standard model:

> Review the current RPA-1 repository structure and propose a simple navigation system for a student-built robotics project. Keep the existing safety rules, Chordic/CSP-1 naming, and staged-release philosophy. Recommend only small documentation changes: an index, status labels, milestone pages, and a consistent format for build guides. Do not redesign the robot.

Expected result: repository map, suggested README links, status labels, and a documentation template.

### 01 — Project requirements baseline

> Turn the current RPA-1 goals into a requirements table with IDs. Separate must-have, later, and explicitly out-of-scope requirements. Include budget, portability, safety, offline operation, simulation, musical communication, sensing, manipulation, and locomotion. Every requirement must have a verification method.

Expected result: `docs/requirements/requirements-v0.2.md`.

### 02 — GitHub milestone and evidence system

> Design a milestone system for RPA-1 that lets each stage be a portfolio project. For each milestone, define the question, deliverable, test, evidence to record, cost limit, failure conditions, and GitHub release note. Keep milestones small enough for a freshman EE student.

Expected result: `docs/roadmap/milestones.md` and a reusable test-report template.

### 03 — Rocky Brain v0.1 on the UNO R3

> Give me a complete beginner build for Rocky Brain v0.1 using an Elegoo Super Starter Kit UNO R3, two buttons, a passive buzzer, and a computer. It must support a simple communication mode and a normal-language translation mode selected by a button. Include wiring, Arduino IDE setup, code files, serial commands, tests, and troubleshooting. Do not add motors, internet, AI, or Raspberry Pi yet.

Expected result: a working tabletop prototype and `docs/build-guides/brain-v0.1-build.md`.

### 04 — Chordic and CSP-1

> Review the current Chordic/CSP-1 idea and define the smallest deterministic, reversible message format that can run on an Arduino and later on a Raspberry Pi. Use named semantic intents rather than copyrighted dialogue. Include message fields, encoding rules, decoding rules, examples, error handling, and unit tests.

Expected result: language specification, encoder/decoder tests, and no unverified linguistic claims.

### 05 — Computer-only Rocky simulation

> Design a computer-only Rocky simulation that can run before physical hardware. Start with a simple 2D or 3D body, five limbs, joint limits, contact states, gait timing, actuator placeholders, safety stops, and Chordic messages. Recommend the lowest-setup tools that can export logs and later connect to a Raspberry Pi. Do not add advanced AI or realistic graphics unless they help testing.

Expected result: simulation choice, install steps, folder structure, first demo, and a clear boundary between simulated and measured behavior.

### 06 — Simulation-to-hardware interface

> Define a hardware-independent command and telemetry interface between the Rocky simulator, a Linux computer, a Raspberry Pi, and real-time microcontrollers. Include message schemas, timestamps, units, heartbeat, timeout behavior, emergency-stop behavior, and a fake-hardware mode. Prefer a simple local/offline interface before ROS 2.

Expected result: interface specification plus a small reference implementation and tests.

### 07 — Offline Raspberry Pi brain

> Design the first offline Raspberry Pi brain for RPA-1. It should run the simulator interface, Chordic encoder/decoder, local state machine, event logging, and safe commands to a microcontroller without cloud access. Recommend hardware only when necessary. Include installation from a fresh Raspberry Pi, services, startup behavior, recovery behavior, and tests.

Expected result: `software/pi_brain/` and a fresh-device setup guide.

### 08 — Offline phone translation app

> Design the smallest offline phone companion for RPA-1 that can translate Chordic messages into normal language and convert a small set of approved text commands into Chordic intents. Start with local Bluetooth or Wi-Fi Direct only if it is practical. Do not require cloud AI. Compare the easiest beginner-friendly options and choose one.

Expected result: a minimal app or local web interface, message schema, pairing steps, and offline test.

### 09 — Perception and “seeing”

> Create a staged perception plan beginning with simulated sensors and inexpensive sensors already reasonable for a student prototype. Compare IMU, ToF, bump/contact, encoders, and optional LiDAR. Define what each sensor proves, where it connects, how it fails, and how to test it without claiming human-like vision.

Expected result: sensor experiment matrix and first low-cost test.

### 10 — Actuator comparison rig

> Design a guarded, low-cost comparison experiment for electric tendon drives, joint servos, low-pressure pneumatic artificial muscles, and manual low-pressure syringe hydraulics. Measure force, travel, speed, repeatability, hysteresis, mass, noise, cost, and failure behavior. Exclude homemade pressure vessels and high-pressure hydraulic systems.

Expected result: test rig, data sheet, risk controls, and decision gate.

### 11 — One compliant limb

> Design a small, non-load-bearing compliant limb with one closed-loop joint, tendon or servo actuation, a spring element, encoder or position feedback, and a hard stop. Include CAD dimensions only where justified, wiring, firmware behavior, calibration, and acceptance tests. The limb must fail safely when disconnected or overloaded.

Expected result: one-joint demonstrator before any walking robot.

### 12 — Three-finger expressive manipulator

> Design a small three-finger compliant clamp for stationary object interaction. Prioritize safe gripping, replaceable fingertips, low cost, and expressive puppet-like motion. Define objects it may handle, objects it must not handle, force limits, tests, and how it connects to the common command interface.

Expected result: safe stationary manipulation module.

### 13 — Small pentapod gait

> Using the tested limb assumptions, design a 1:3-scale five-limb walking prototype with no wheels or hidden rolling elements. Begin with tethered or supervised walking. Define the conservative gait, support conditions, stop behavior, calibration, test surface, and success criteria. Do not design full-scale walking yet.

Expected result: gait simulator update, small prototype plan, and test report format.

### 14 — Three-leg/two-arm transition

> Design a stationary transition where five limbs establish contact, a verified three-foot support triangle remains stable, and two limbs perform a simple expressive or object-interaction motion. Include stability assumptions, force limits, motion sequence, failure states, and a manual emergency stop. Treat this as a research demonstration, not proof of full-scale mobility.

Expected result: simulation first, then a guarded physical demonstration.

### 15 — Offline integration demonstration

> Combine the simulator, Chordic communication, offline phone translator, Raspberry Pi brain, microcontroller safety layer, sensors, and one tested actuator module into one end-to-end demonstration. Keep the scenario small and reproducible. List every subsystem, interface, test, log file, and known limitation.

Expected result: a portfolio-quality integration demo without pretending the final Rocky exists.

## Six reserved Astra questions

Use these only after the relevant smaller prompts and experiments are complete. Save one question for one conversation. Attach the current repository files, measurements, logs, and failed attempts. Do not paste the entire project if a smaller evidence set is enough.

### Astra 1 — Whole-system architecture review

> Given the attached RPA-1 requirements, repository map, interfaces, test evidence, and budget, identify the most serious architecture conflicts and propose one staged architecture that preserves offline operation, safety, repairability, and future simulation-to-hardware transfer. Separate demonstrated facts, assumptions, and recommendations. Do not redesign parts that are not causing a conflict.

### Astra 2 — Actuation decision

> Given the attached actuator test data, determine which actuation approach should be used for the next RPA-1 milestone. Compare electric tendons, servos, pneumatics, and low-pressure hydraulics using measured performance, safety, mass, control difficulty, cost, maintenance, and scalability. Show what evidence would overturn the decision.

### Astra 3 — Simulation-to-real validation

> Audit the attached Rocky simulator and hardware interface for sim-to-real failure modes. Find mismatched units, timing, contact assumptions, actuator limits, sensor assumptions, safety gaps, and untestable claims. Return a prioritized validation plan with the smallest experiments needed before physical walking.

### Astra 4 — Stability and safe locomotion

> Given the attached geometry, mass estimates, contact data, and gait logs, evaluate the proposed five-limb gait and three-leg/two-arm transition. Identify stability margins and unsafe assumptions, then recommend a conservative test sequence with hard stop conditions. Do not approve full-scale motion unless the evidence supports it.

### Astra 5 — Offline system and cybersecurity review

> Audit the attached Raspberry Pi, microcontroller, phone, and local-network design for reliable fully offline operation and authorized-only device control. Check startup, pairing, authentication, replayed commands, lost connection, corrupted messages, watchdogs, emergency stop, updates, and recovery. Return concrete fixes that fit a student budget.

### Astra 6 — Portfolio and research-quality review

> Review the attached RPA-1 documentation and test evidence as an engineering mentor evaluating a freshman project for future MIT applications. Identify the strongest genuine contribution, unsupported claims, missing controls, weak experiments, and most valuable next milestone. Recommend edits that make the work clearer and more credible without exaggerating the result or making it sound professionally ghostwritten.

## Commit rhythm

Use small commits that match real progress:

- `docs: clarify requirements`
- `language: add CSP-1 encoder tests`
- `firmware: add brain v0.1 button modes`
- `simulation: add five-limb contact state`
- `software: add offline pi message bridge`
- `hardware: document one-joint test`
- `docs: record failed actuator experiment`

A commit should contain one understandable change, one test or verification note, and no claims beyond the evidence.

## Definition of done for every milestone

A milestone is not finished until it has:

- a short question it answers;
- a build or experiment someone else can repeat;
- a bill of materials and actual cost;
- source files and setup steps;
- a test procedure and result;
- known failures and limitations;
- dated photos, video, logs, or measurements;
- a clear next decision.

## Important boundary

The final Rocky is a long-term goal. The credible near-term project is a sequence of tested modules: tabletop communication, deterministic musical protocol, computer simulation, offline Raspberry Pi brain, offline phone translator, actuator comparison, one compliant limb, stationary manipulation, and only then supervised pentapod locomotion.
