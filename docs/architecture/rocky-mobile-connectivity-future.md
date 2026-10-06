# Future phone and mobile connectivity progression

**Date:** 2026-10-05  
**Status:** Architecture guidance only — no hardware purchase required

Early Rocky does not need an onboard cellular modem.

Recommended progression:

1. **Phone hotspot** — simplest way to give the future onboard computer ordinary Wi-Fi internet when Connected Mode is deliberately enabled.
2. **Wi-Fi tethering / known LAN** — preserve the same outbound-only connected gateway boundary.
3. **USB tethering** — useful when stable power/data and reduced Wi-Fi dependence matter.
4. **Bluetooth companion** — later option for bounded companion controls/status, not raw motor authority.
5. **Dedicated LTE/5G** — only after onboard power, thermal, antenna, carrier, security, and recurring-cost requirements are justified by real use.

## Security boundary

Changing the transport must not change Rocky's authority model:

- OFFLINE remains default;
- online state is explicit;
- credentials remain outside the model;
- no public unauthenticated Rocky service;
- no internet-facing raw UI or hardware endpoint;
- connected capabilities remain allowlisted/audited;
- network loss must not weaken deterministic safety;
- the LLM still has no raw motor/gait/charger authority.

A phone hotspot is merely a network path. It is not permission for the model to browse freely.

## Physical autonomy

This roadmap deliberately does not start walking, docking, or charger control. Future autonomy remains below deterministic navigation/safety/charging controllers, with the LLM limited to high-level intent such as "Rocky need charge."
