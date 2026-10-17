# Status

Updated: 2026-10-17

- Phase 0: not started. PLAN.md written, Proteus exports copied to `source/`.
- Next: tools/kicad_env.sh, tools/ipc356.py, reference/pin_nets_by_component.md.
- Last verification: none yet.

## Next prompt

```
Read PLAN.md and STATUS.md in /home/jari/dev/ac_psu_kicad. Use Opus 5.5.
Start Phase 0 (PLAN.md section 2): create tools/kicad_env.sh (mount the AppImage at
~/kicad/kicad-10.0.7-x86_64.AppImage with --appimage-mount; do not run it with --version,
it hangs; expose kicad-cli and a `kipy` wrapper around <mount>/bin/python3.11 with
PYTHONPATH=<mount>/shared/lib/python3.11/dist-packages so `import pcbnew` works),
tools/ipc356.py (parse source/cadcam/*Netlist.IPC into JSON/CSV; fix the six truncated
refdes AFE_OU, FILTER x2, DAB_PR x2, DAB_SE x2, INU_OU by coordinate; alias GND=POWER
-> GND and VCC/VDD=POWER -> VCC), and reference/pin_nets_by_component.md.
Done when: the parser reports 208 nets, 265 refdes, 562 THT + 513 SMD pads; `kipy -c
"import pcbnew; print(pcbnew.GetBuildVersion())"` prints 10.0.7; tools/check_all.sh runs
the parser self-check. Update STATUS.md, commit, and end with the handoff prompt for
Phase 1 as described in PLAN.md "Handoff prompt".
```
