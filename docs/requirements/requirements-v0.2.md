# RPA-1 Preliminary Requirements v0.2

**Date:** 2026-09-30
**Status:** Draft for prototype validation; supersedes v0.1 as the current requirements baseline
**Verification codes:** I = inspection, A = analysis, T = test, D = demonstration

These are engineering targets, not claims of certification. Requirements are not considered VERIFIED until their stated verification has been completed and linked to a test result.

**v0.2 change summary:** adds the 3–5 hour normal-use runtime target, online/offline connectivity behavior, and staged door, chair, book, drawing, paper-folding, and puppet-show manipulation goals. No battery capacity, actuator torque, grip force, door force, chair force, or untested payload value is inferred by this revision.

## Mission and scope

RPA-1 shall be a modular, repairable, five-limbed embodied assistant and research platform inspired by Rocky's visible form, musical communication, and expressive behavior. It shall support non-medical companionship, study assistance, deterministic musical language, safe supervised movement, and very lightweight manipulation.

## Governing constraints

| ID | Requirement | Verification |
|---|---|---|
| CON-001 | Locomotion shall not use wheels, concealed rollers, or a powered rolling base. | I, D |
| CON-002 | Purchases shall average no more than $100 per month. | I |
| CON-003 | Portfolio Release 1.0 shall remain at or below $2,000 cumulative spending through May 2028, assuming that academic date is confirmed. | I |
| CON-004 | The central-body working volume shall be 22 L until authoritative reference analysis replaces it. | A |
| CON-005 | Mobile-system mass shall target 8–10 kg; integration shall stop for review above 12 kg. | I, A |
| CON-006 | Full-scale unsupported walking is outside the sophomore-year release requirement. | I |

## Power, runtime, and connectivity

| ID | Requirement | Verification |
|---|---|---|
| PWR-001 | Under a documented normal-use duty cycle, RPA-1 shall remain powered, responsive, sensing, and available for commands for at least 3 hours per charge, with 5 hours as the design goal. This does not mean 3–5 hours of continuous walking or maximum-load actuation. | T |
| PWR-002 | Battery state shall be monitored and the system shall provide a low-battery indication and enter a documented safe park/shutdown behavior before the selected battery system reaches an unsafe discharge condition. Exact thresholds shall come from the selected battery/BMS specifications and test data. | I, T |
| PWR-003 | RPA-1 shall support network-connected operation while retaining required core safe operation when internet access is unavailable. Loss of internet shall not disable the physical E-stop, local safety checks, basic sensing, or required local Chordic/translation functions. | I, T |

## Safety requirements

| ID | Requirement | Verification |
|---|---|---|
| SAF-001 | A latching, normally closed physical E-stop shall remove actuator energy without depending on Linux, AI, or wireless communication. | I, T |
| SAF-002 | Resetting an E-stop shall never initiate motion. | T |
| SAF-003 | Startup shall default to actuator output disabled and require an explicit enable after self-test. | T |
| SAF-004 | Stale commands, heartbeat loss, invalid feedback, overcurrent, overtemperature, and travel-limit activation shall produce a documented bounded state. | T |
| SAF-005 | Early powered limbs shall operate on a rigid stand or rated restraint behind an exclusion boundary. | I |
| SAF-006 | The first gait tests shall use a tether, level compliant test surface, remote dead-man enable, and no bystanders or pets. | I, D |
| SAF-007 | Accessible pinch/shear points shall be guarded or shown by test to remain within the released force/speed limits. | I, T |
| SAF-008 | Each energized branch shall have accessible overcurrent protection and a labeled disconnect. | I, T |
| SAF-009 | No homemade pressure vessel, superheated working fluid, mercury, steam mechanism, or high-pressure hydraulic system shall be used. | I |
| SAF-010 | Any pneumatic experiment shall use rated components, a regulator, relief device, minimal stored volume, a guard, and remote actuation. | I, T |
| SAF-011 | A load-bearing fault shall use controlled lowering, braking, or restraint when immediate torque removal would cause a fall. | A, T |
| SAF-012 | Initial autonomous motion shall not occur around people, pets, stairs, public spaces, or unprotected property. | I |
| SAF-013 | Door and chair manipulation tests shall begin on controlled fixtures or authorized user-controlled property, at reduced speed, with a clear pinch/crush exclusion area and an accessible physical E-stop. | I, D |

## Mobility and stability

| ID | Requirement | Verification |
|---|---|---|
| MOB-001 | The robot shall use five mechanically similar limb modules wherever practical. | I |
| MOB-002 | The first released gait shall lift no more than one foot at a time, leaving four contacts. | D, T |
| MOB-003 | Initial full-scale target speed shall not exceed 0.05 m/s; the scale robot may receive a separately tested limit. | T |
| MOB-004 | A stationary interaction transition shall begin with five verified contacts. | T |
| MOB-005 | Two limbs may enter arm mode only after three stance feet report valid support and estimated center-of-mass margin is at least 30 mm full-scale equivalent. | A, T |
| MOB-006 | The scale robot shall complete a 2 m forward course and a 90° turn without a tether catch before Portfolio Release 1.0. | T, D |
| MOB-007 | The scale robot shall complete 20 consecutive five-foot-to-three-foot/two-arm-to-five-foot transitions without a fall. | T |
| MOB-008 | Loss of one required foot-contact signal during weight transfer shall stop the transition and return to a tested safe behavior. | T |
| MOB-009 | Before manipulation that can create significant external reaction force, including door or chair tasks, the controller shall establish the required stable support state. The manipulation command shall be rejected if that support state is not valid. | A, T |

## Limb and actuation

| ID | Requirement | Verification |
|---|---|---|
| ACT-001 | Each mature limb shall target two controlled axes at the body and one mid-limb hinge axis. | I, D |
| ACT-002 | The full-scale development architecture shall investigate body-mounted electric drives with tendons and deliberate series compliance. | I, T |
| ACT-003 | Actuators shall be selected using measured continuous torque, thermal behavior, duty cycle, and efficiency—not stall torque alone. | I, T |
| ACT-004 | Tendons shall have guarded routing, documented pretension, inspection criteria, and a detectable slack/break failure response. | I, T |
| ACT-005 | A joint shall include local position feedback and current sensing; a series-elastic version shall measure spring deflection or tendon force. | I, T |
| ACT-006 | Joint motion shall use mechanical stops plus stricter software limits. | I, T |
| ACT-007 | A literal unlimited 360° shoulder is not required; cable-safe joint ranges shall be measured and documented. | I, T |
| ACT-008 | Initial joint repeatability shall be within 3° at its released test load. | T |

## Hands, feet, and expression

| ID | Requirement | Verification |
|---|---|---|
| END-001 | Each eventual limb end shall visually present three fingers and support interchangeable or mechanically transformed hand/foot behavior. | I, D |
| END-002 | The first gripper shall use underactuated tendon closure, elastic opening, compliant pads, and no sharp exposed point. | I, T |
| END-003 | Walking load shall pass through a broad pad and mechanical structure, not depend on continuous tension in delicate finger hinges. | I, T |
| END-004 | Initial prop payload shall be 50 g; progression to 250 g requires renewed torque, grip, and stability tests. | T |
| END-005 | The system shall demonstrate point, compare, sequence, question, caution, and celebrate gestures with standardized lightweight props. | D |

## Manipulation task requirements

These are end-state or later-stage goals. They do not authorize skipping the actuator, single-limb, restrained-motion, and stability gates above.

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| MAN-001 | Must-have end-state | RPA-1 shall be capable of securely gripping a compatible lever-style door handle on an unlocked, authorized test door or fixture without damaging the handle. | I, D, T |
| MAN-002 | Must-have end-state | After MAN-001 and the applicable stability requirements pass, RPA-1 shall be capable of actuating the compatible handle and moving the unlocked door in a commanded direction, then releasing it while remaining stable. Required handle torque and door force remain TBD until measured on the target test hardware. | D, T |
| MAN-003 | Must-have end-state | RPA-1 shall be capable of pushing and pulling a compatible lightweight chair in a clear supervised test area. Required force and allowed chair mass shall be measured before actuator selection or acceptance testing. | A, D, T |
| MAN-004 | Must-have end-state | RPA-1 shall be capable of picking up, holding, moving, placing, and releasing defined test books that are within the released gripper and stability limits. | D, T |
| MAN-005 | Later | RPA-1 should support controlled drawing with a pen, pencil, marker, or similar lightweight tool after basic gripper control is verified. Initial acceptance geometry and accuracy remain TBD until the drawing test is written. | D, T |
| MAN-006 | Later / advanced | RPA-1 should support paper-manipulation primitives needed for simple origami: hold, reposition, crease, and release. A complete origami capability shall not be claimed until a named folding sequence is completed under a written test. | D, T |
| MAN-007 | Later | RPA-1 should be capable of using lightweight books, drawings, folded-paper objects, or similar props in a scripted puppet-show demonstration after each required manipulation primitive is separately verified. | D, T |
| MAN-008 | Must-have engineering constraint | Battery capacity, gripper force, limb payload, handle torque, door force, chair force, and required actuator torque shall be selected from measurement and analysis rather than guessed values. | I, A |

## Interaction, language, and AI

| ID | Requirement | Verification |
|---|---|---|
| INT-001 | Musical phrases shall be generated from a versioned semantic representation and dictionary, not improvised notes with invented translations. | I, T |
| INT-002 | Valid software messages shall round-trip through encoder and decoder with at least 99% exact semantic accuracy. | T |
| INT-003 | A physical button shall control translation mode without network access. | T |
| INT-004 | Voice and clap triggers shall remain convenience inputs and shall never function as emergency stops or motor enables. | I, T |
| INT-005 | Assistant-generated actions shall pass schema validation, authorization, motion limits, and local safety checks. | I, T |
| INT-006 | Long-term memory shall be opt-in, inspectable, correctable, and deletable. | I, D |
| INT-007 | The system shall make no medical, diagnostic, therapeutic, or crisis-response claims. | I |
| INT-008 | Network connectivity may add services or remote information, but required local Chordic/CSP-1 communication and translation behavior shall have a documented offline operating path. | I, T |

## Perception and privacy

| ID | Requirement | Verification |
|---|---|---|
| PER-001 | Required near-body safety shall not depend on optional LiDAR. | I, T |
| PER-002 | Initial mobility sensing shall include IMU, joint position, motor current, foot contact/load, bumpers, and downward or short-range ranging as justified by the test course. | I, T |
| PER-003 | Optional cameras and microphones shall have visible state indicators and physical disable/mute controls. | I, T |
| PER-004 | LiDAR, if added, shall pass optical-window, blind-spot, lighting, motion-distortion, and loss-of-sensor tests before controlling movement. | T |
| PER-005 | Camera data shall default to local processing and no retention unless the operator explicitly enables storage. | I, T |

## Documentation and portfolio evidence

| ID | Requirement | Verification |
|---|---|---|
| DOC-001 | Every demonstration shall identify firmware, software, CAD, electronics, and test-procedure revisions. | I |
| DOC-002 | Each phase shall include requirements, design rationale, BOM, risks, test plan, raw data, result, limitations, failures, and next decision. | I |
| DOC-003 | The repository shall distinguish movie evidence, book evidence, engineering assumptions, and demonstrated results. | I |
| DOC-004 | Portfolio Release 1.0 shall include build-process photos, concise explanations, working code, and no more than two minutes of selected moving-system video for a possible MIT Maker Portfolio. | I, D |
