"""Ports of block E (V6_PLAN.md section 16): where each crossing signal net leaves the block (IPC mm, y up).

Every port is a stub end exactly on the E edge, one net per point, >= 0.5 mm apart. Order (see block_E.md): the
trunks outside E keep this order without crossing.

- south edge y -46 (window E-C, x 41 .. 66): the nine primary PWMs to the card headers J21 / J22 / J23 in the order
  of their header groups (J21 trunks turn west, J23 east, J22 straight south between them); all on In3 because
  F.Cu there is the DC+ pour and B.Cu the PGND pour, and west of C12 (its DC+ pad at (62.1, -36.6) keeps 2.5 mm);
  the In3 channel between R41 / C12 holds six lanes, so four nets come on In2 (no plane south of y -20.7; their
  vias stand in the strip x 40 .. 42.5 west of the P planes, where F.Cu has no pour)
- west edge x 40 (window E-A): MDATA new on In3; ADCLK, GPIO_BYPASS_RLY, Net-(R2-Pad1), Net-(R5-Pad1), Net-(U1A-+),
  Net-(U1A--) leave on their kept v4 inner-layer copper (EXISTING)
- north edge y 46 (window E-D, x 59 .. 117): all ISO crossing nets (the windows E-B and E-F at x 40, y > 5.8 lie in
  the C|I barrier strip and C land: no I net can reach them). West to east: the J25 group (straight north), the
  path-A group (to J24 / the relay line, south lanes of the westward corridor), the sigma-delta pair and the six
  divider taps (north lanes, through the via column between the J37 / J38 tongues), the J26 group (straight north)
"""

PORT_IN = 0.5    # the router's port pad sits this far inside the edge; block_E_fence.py adds the piece to the edge


def _p(edge, x, y, layer, dest):
    return {"edge": edge, "at": (x, y), "layer": layer, "dest": dest}


PORTS = {
    # E-C, y -46
    "PWM_G1": _p("S", 41.5, -46.0, "In3.Cu", "J21-1 (1.46, -51.13)"),
    "PWM_G2": _p("S", 42.0, -46.0, "In2.Cu", "J21-3 (2.73, -51.13)"),
    "PWM_TRANS1": _p("S", 42.5, -46.0, "In3.Cu", "J21-5 (4.00, -51.13)"),
    "PWM_G3": _p("S", 43.0, -46.0, "In3.Cu", "J22-1 (51.21, -60.13)"),
    "PWM_G4": _p("S", 43.5, -46.0, "In3.Cu", "J22-3 (52.48, -60.13)"),
    "PWM_TRANS2": _p("S", 44.0, -46.0, "In2.Cu", "J22-5 (53.75, -60.13)"),
    "DAB_PWM_PRI_HI": _p("S", 44.5, -46.0, "In2.Cu", "J23-1 (88.01, -59.44)"),
    "DAB_PWM_PRI_LO": _p("S", 45.0, -46.0, "In2.Cu", "J23-3 (89.28, -59.44)"),
    "PWM_TRANS3": _p("S", 45.5, -46.0, "In3.Cu", "J23-5 (90.55, -59.44)"),
    # E-A, x 40
    "MDATA": _p("W", 40.0, -22.0, "In3.Cu", "R55-2 (-27.49, -76.00)"),
    # E-D, y 46. The band under the edge (y 40 .. 46, the I-side pins of U19 / U21 / U20 at y 40.15) has only B.Cu
    # (F.Cu: ISOPGND pour east of x 68; In3: the sdm reserve x 58.5 .. 78; In1 / In2 / In4: ISO planes), so most
    # ports stand straight above their isolator pin and the trunks in D sort the order (D has the inner layers;
    # the J25 / J26 pads are through-hole, so crossings there need no via). "p1": the end of D's pass-1 copper.
    "PWM_TRANS5": _p("N", 60.5, 46.0, "B.Cu", "p1, above U19-10; J25-5 (62.50, 49.66)"),
    "PWM_Q8": _p("N", 61.3, 46.0, "B.Cu", "beside U19-11 (clear of the p1 GPIO run); J24-3 (13.27, 46.07), path A"),
    "PWM_Q6": _p("N", 63.0, 46.0, "F.Cu", "p1, above U19-12; J25-3 (61.23, 49.66)"),
    "PWM_Q5": _p("N", 63.6, 46.0, "B.Cu", "p1; J25-1 (59.96, 49.66)"),
    "GPIO_BYPASS_RLY_ISO": _p("N", 65.0, 46.0, "B.Cu", "near U19-15; R88-1 / R78-2 (-66.6, 13.0), path A"),
    "PWM_TRANS6": _p("N", 71.2, 46.0, "B.Cu", "p1; J24-5 (13.27, 44.80), path A"),
    "MDATA_INU": _p("N", 73.5, 46.0, "B.Cu", "R50-2 (-96.58, 64.53), path B"),
    "INU_ADCLK": _p("N", 74.0, 46.0, "B.Cu", "U4-7 (-94.06, 64.45), path B"),
    "PWM_Q7": _p("N", 83.64, 46.0, "B.Cu", "above U20-11; J24-1 (13.27, 47.34), path A"),
    "PWM_TRANS4": _p("N", 86.19, 46.0, "B.Cu", "above U20-13; J26-5 (94.70, 49.66)"),
    "DAB_PWM_LO_SEC": _p("N", 87.45, 46.0, "B.Cu", "above U20-14; J26-3 (93.43, 49.66)"),
    "DAB_PWM_HI_SEC": _p("N", 88.72, 46.0, "B.Cu", "above U20-15; J26-1 (92.16, 49.66)"),
    "Net-(U7B--)": _p("N", 90.9, 46.0, "In3.Cu", "p1; R68-1 (-2.17, 33.60), path B"),
    "Net-(U7B-+)": _p("N", 91.5, 46.0, "In3.Cu", "p1; R67-1 (-2.22, 37.30), path B"),
    "Net-(U7A--)": _p("N", 92.1, 46.0, "In3.Cu", "p1; R256-1 (-6.67, 48.00), path B"),
    "Net-(U7A-+)": _p("N", 92.7, 46.0, "In3.Cu", "p1; R71-1 (-6.72, 43.70), path B"),
    "Net-(U2--)": _p("N", 93.3, 46.0, "In3.Cu", "p1; R85-1 (-10.50, 27.68), path B"),
    "Net-(U2-+)": _p("N", 93.9, 46.0, "In3.Cu", "p1; R82-1 (-14.60, 27.98), path B"),
    "15V_ISO": _p("N", 95.0, 46.0, "B.Cu", "from C158-1; D's 15V_ISO run ends at (58.89, 46) F.Cu (pass 1)"),
    "5V_ISOL": _p("N", 96.15, 46.0, "B.Cu", "p1 (0.28 mm stub), from C159-1; D's run ends at (64.2, 46) F.Cu"),
}
# crossing nets that leave E on kept (v4 / Proteus) copper: net -> (edge, point, layer)
EXISTING = {
    "Net-(R2-Pad1)": ("W", (40.0, -11.3), "In2.Cu"),
    "Net-(R5-Pad1)": ("W", (40.0, -13.6), "In2.Cu"),
    "Net-(U1A-+)": ("W", (40.0, -15.7), "In2.Cu"),
    "Net-(U1A--)": ("W", (40.0, -18.21), "In2.Cu"),
    "ADCLK": ("W", (40.0, -19.98), "In2.Cu"),
    "GPIO_BYPASS_RLY": ("W", (40.0, -27.56), "In1.Cu"),
}
