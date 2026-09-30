# Actuation Trade Study v0.1

**Decision:** Use electric motors with tendon transmission and series elasticity as the leading full-scale architecture. Use inexpensive joint-mounted servos for the first scale walker. Test pneumatic artificial muscle and manual low-pressure hydraulic specimens on a common guarded rig.

## What biology contributes

Biology does not place a rigid rotary motor at every joint. Muscle produces tension, bones carry structural load, tendons transmit force, antagonistic groups create bidirectional torque and adjustable stiffness, and elastic tissues absorb shock and return energy. Useful engineering translations are:

- keep heavy actuators close to the central body;
- keep distal links light;
- transmit tension with tendons or cables;
- use opposed tendons or a bidirectional cable loop;
- place a known spring in the force path;
- estimate force from spring deflection, (F=kx);
- use passive elastic return and gravity compensation where possible;
- measure contact and load rather than commanding pose blindly.

This does **not** justify copying fictional superheated-fluid biology.

## Load anchor

For an 8 kg robot, equal static loading gives:

\[
F_{4\,feet}=\frac{8(9.81)}{4}=19.6\;N/foot
\]

\[
F_{3\,feet}=\frac{8(9.81)}{3}=26.2\;N/foot
\]

At a 0.15 m horizontal moment arm, nominal proximal-joint torque is about 2.9 N·m on four supports or 3.9 N·m on three. A preliminary 2× design factor produces about 5.9–7.8 N·m. At an unfavorable 0.25 m arm, the three-support design value becomes roughly 13 N·m. Final actuator selection requires measured mass distribution, linkage geometry, dynamic loads, and duty cycle.

## Candidate systems

Weights: cost 25%, safety 20%, controllability/debugging 20%, mobile mass/packaging 15%, biological/visual fidelity 10%, portable efficiency 10%. Scores are 1–5.

| Option | Cost | Safety | Control | Mass/package | Bio fidelity | Efficiency | Weighted |
|---|---:|---:|---:|---:|---:|---:|---:|
| Joint-mounted electric servos | 4 | 3 | 5 | 2 | 2 | 3 | 3.40 |
| Body-mounted electric + tendon + series spring | 4 | 4 | 4 | 4 | 5 | 4 | **4.10** |
| Pneumatic artificial muscles | 2 | 3 | 2 | 2 | 5 | 1 | 2.40 |
| Onboard hydraulic cylinders | 1 | 1 | 3 | 2 | 4 | 3 | 2.05 |
| Electric linear actuators | 3 | 3 | 4 | 2 | 3 | 4 | 3.15 |

## Pneumatic artificial muscles

A McKibben-style pneumatic artificial muscle contracts when its elastomeric bladder expands against a braided sleeve. It is genuinely muscle-like: light, tensile, compliant, and capable of useful force.

Festo's small DMSP-5 data sheet lists up to 20% contraction, operation up to 0.6 MPa (6 bar), and 140 N theoretical force at maximum pressure. Those numbers demonstrate useful actuator force, but not a complete mobile system. A 15-DOF antagonistic implementation could require approximately 30 muscle elements or a comparably complex tendon/valve arrangement, many controlled valve channels, pressure sensors, a regulator, relief device, compressor or rated reservoir, air preparation, and nonlinear control.

Key drawbacks for RPA-1:

- compressed-air production and storage dominate system mass and noise;
- air compressibility reduces positional stiffness and complicates control;
- force changes with pressure, contraction, braid geometry, temperature, and hysteresis;
- single-acting muscles require antagonism or return springs;
- leaks reduce endurance;
- burst or hose-release energy requires guarding and rated parts.

**Disposition:** one low-energy guarded experiment is worthwhile. Do not design all five limbs around it before data.

## Hydraulics

Hydraulic cylinders produce high force from a compact area:

\[
F=P A
\]

A 10 mm bore cylinder at 3 MPa has ideal extension force of approximately 236 N. That attractive number omits the pump, motor, reservoir, accumulator if used, servo valves, filters, pressure sensors, hoses, seals, cooling, containment, and maintenance. Research hydraulic quadrupeds use purpose-built high-pressure components and extensive sensing; this is not a cheap substitute for electric servos.

Key drawbacks for RPA-1:

- injection and burst hazards at high pressure;
- leaks contaminate floors and create slip hazards;
- pump and valve cost exceeds the early prototype budget;
- hoses add routing stiffness to all five role-fluid limbs;
- the system is difficult to debug safely in a dorm or beginner shop.

**Disposition:** use paired water-filled syringes only as a manual, low-pressure comparison specimen inside a tray. No onboard pump or stored high pressure.

## Electric tendon and series-elastic drive

The preferred module uses a centrally mounted motor/gearbox and capstan. A bidirectional cable loop or two opposed tendons drives the joint. A spring or flexure in series absorbs impact and exposes force through measured deflection.

Benefits:

- batteries and motor controls fit the rest of the electrical architecture;
- actuators can be concentrated in the 22 L body;
- distal links remain light, lowering joint torque and collision energy;
- springs create physically meaningful compliance;
- current, position, spring deflection, and tendon tension are measurable;
- a broken tendon can be detected through loss of tension or implausible motion.

Engineering problems to test:

- tendon stretch and creep;
- capstan slip;
- slack during reversal;
- pulley friction and changing moment arms;
- cable fatigue at small bend radii;
- coupled routing through two-axis body joints;
- safe behavior when a load-bearing tendon fails.

The first shoulder should be a cable-safe two-axis gimbal, not a literal unlimited ball joint. The mid-limb joint is a single hinge. This yields three controlled limb axes without twisting tendons and wires indefinitely.

## Hand/foot mechanism

Use three fingers linked by one underactuated closing tendon, elastic opening, and compliant TPU/rubber pads. A cam, over-center linkage, or structural foot plate shall carry walking load so that a small finger actuator does not continuously support the robot. Sharp spike behavior is excluded.

## Decision gate

The architecture may change only after all three comparison specimens are tested with the same joint geometry and metrics:

- force versus displacement;
- loaded travel and repeatability;
- rise and settling time;
- hysteresis;
- electrical or fluid energy per motion where measurable;
- complete actuator-system mass and cost;
- sound level;
- thermal behavior;
- controllability;
- failure behavior and repair time.

See [`../test-plans/actuator-comparison-test.md`](../test-plans/actuator-comparison-test.md).

## Starting references

- Festo, [DMSP-5 Fluidic Muscle data sheet](https://ftp.festo.com/Public/PNEUMATIC/SOFTWARE_SERVICE/Datasheet/EN_US/3733012.pdf).
- Semini et al., [Design of HyQ—A Hydraulically and Electrically Actuated Quadruped Robot](https://doi.org/10.1177/0959651811402275).
- Zou et al., [Modeling and Control of a Cable-Driven Series Elastic Actuator](https://arxiv.org/abs/1701.03913).
- Badri-Spröwitz et al., [Series Elastic Behavior of Biarticular Muscle-Tendon Structure in a Robotic Leg](https://doi.org/10.3389/fnbot.2019.00064).
