# Risk Register v0.1

Ratings are preliminary. “Critical” means the next relevant test is blocked until the listed control exists.

| ID | Risk | Level | Current controls | Next evidence |
|---|---|---|---|---|
| R-001 | Full-scale tip, fall, or crush | Critical | no unsupported full-scale motion; stands, restraint, exclusion zone | supported load and fault test |
| R-002 | Joint pinch or shear | High | low speed/force, guards, remote test, hard stops | guarded-joint inspection and force test |
| R-003 | Runaway or stale motor command | Critical | local timeout, limits, hardwired actuator-energy isolation, manual reset | injected timeout and sensor-fault tests |
| R-004 | Battery fire or peak-current failure | Critical | tether first; protected commercial pack later; branch fusing | measured current profile and faculty review |
| R-005 | Wiring overheat or short | High | current-limited supply, sized wire/connectors, fuse, inspection | thermal/current test |
| R-006 | Drop-off or sensor blind spot | High | level closed course, bumpers, downward/near ranging | obstacle and cliff-fixture tests |
| R-007 | False clap/voice activation | Medium | convenience functions only, timing/confidence/cooldown | negative-audio test set |
| R-008 | AI generates unsafe action | High | semantic schema, allowlist, local validator, no direct motor path | adversarial command tests |
| R-009 | Scope and cost burnout | High | $100/month cap, dated gates, $2,000 release ceiling | monthly BOM review |
| R-010 | Derivative-IP misuse | Medium | unofficial label; no studio assets in repository | release asset audit |
| R-011 | Door or property damage | High | instrumented fixture, permission, supervision, force limit | fixture force tests |
| R-012 | Excessive or animal-disturbing sound | Medium | ≤70 dBA day/≤55 dBA night targets; off mode | characterized sound test |
| R-013 | Mass growth invalidates walking design | Critical | 8–10 kg budget; mandatory review above 12 kg | subsystem weigh-in at every design review |
| R-014 | Three-leg interaction transition tips robot | Critical | five-foot stop, rearward shift, foot-load and COM-margin checks, one arm at a time | 20 restrained scale transitions |
| R-015 | Tendon slack, stretch, fatigue, routing friction, or break | High | pretensioner, large pulleys, guards, tension/deflection measurement, inspection interval | 500-cycle and cut/slack fault test |
| R-016 | Pneumatic burst or hose release | High | low stored volume, rated parts, regulator, relief, guard, remote test, no tank | proof and leak test behind barrier |
| R-017 | Hydraulic injection, leak, or slippery floor | Critical at high pressure | no high-pressure system; manual syringe fixture only; tray and eye protection | low-pressure fixture inspection |
| R-018 | Sharp claw injures or damages | High | no spike mode; rounded compliant pads; mechanical load plate | edge-radius and contact-force inspection |
| R-019 | Incomplete documentation weakens reproducibility | Medium | issue/PR/test templates and release checklist | independent reproduction attempt |
| R-020 | Admissions pressure produces shallow or unsafe work | High | optimize for learning, measurement, and authenticity; no admission claims | quarterly scope review with mentor |
