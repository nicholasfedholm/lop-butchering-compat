# LoP Butchering Compat (lopbutcheringcompat)

Optional compat mod for Vintage Story 1.22.7: makes Legacy of the Phanerozoic dinosaur families work with the Butchering mod (1.14.3). Pick up the carcass, hang it on the butcher hook, bleed it into a bucket, skin it, and butcher it on the table.

- 24 LoP families covered (14 official + 10 gap-fill builds). Each family turns on only when its LoP mod is loaded (`dependsOn`), so you can run it with any subset of LoP.
- Hard dependencies: game 1.22.7, butchering 1.14.3.
- Yields come from each species' own LoP harvest drops (Butchering copies the entity's harvestable drops into the carcass). The compat only adds Butchering's extras (prime meat, offal, sinew), blood amount, carry weight, and work load. These are copied from a Butchering creature of the same size class (see AUDIT.md section 6).
- Size classes small / medium / large / giant / colossal. Giants (tyrannosaurs, big hadrosaurs) carry like Butchering's elephants (mass 0.16). Sauropods (colossal) use mass 0.4, which hits Butchering's -80% walk-speed clamp.
- Only appends a `butcherable` behavior. Existing behavior indices (which ConfigLib patches address) do not change.

Build: `python -I scripts/gen_family.py <family...>` then `python -I scripts/build_verify.py <version>` (set `VS_MODS` to your Mods folder; the scripts need the Butchering 1.14.3 assets extracted to `work/ex/butchering`).

Coverage tables per family: `coverage/*.csv`. In-game test steps: TEST.md.
