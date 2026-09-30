# RPA-1 Preliminary Requirements v0.1

**Date:** 2026-09-30
**Status:** Draft for prototype validation
**Verification codes:** I = inspection, A = analysis, T = test, D = demonstration

These are engineering targets, not claims of certification.

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
