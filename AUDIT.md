# AUDIT: Butchering x LoP compat mechanism (Phase 0, 2026-11-02)

Evidence: Butchering 1.14.3 (latest on ModDB, tagged 1.22.7, SHA256 8332A390C42677AB4376E8817EF93E8835B3F074E9CD3FE534FF32A8D5508862), decompiled to work\dec_butchering (read by explore-audit, citations below are `file:line` in that tree). Reference compat: FotSA Butchering Compat 0.4.1. LoP prior art: Butchering LoP-Dromaeo compat 1.0.1. Inventory: work\survey.csv, work\lop_inventory.csv, work\pilot_abeli.md.

## 1. How Butchering decides a creature is butcherable
- An entity is butcherable only if it has the entity behavior `butcherable` with attribute `item` (EntityBehaviorButcherable.cs:31 `item = World.GetItem(attributes["item"])`). JSON patches write `itemByType`; VS resolves `*ByType` keys recursively at entity load (vsref: vsessentialsmod/Loading/RegistryObjectType.cs:306 `solveByType`), which is how Butchering's own pig patch works.
- Interaction: dead entity only (:54 `if (entity.Alive) return;`), player with empty right hand (:59), not already knife-harvested (:64). No size or weight limit (none in the file).
- Corpse = an ITEM (class `butcherable`) given to the player; entity despawns if it has `deaddecay` (:118-128).
- Item lookup: `CodeWithVariant("texture", textureIndex+1)` (:69); if missing, retries texture "1" (:72); throws `Could not find butchering item` only if texture "1" also missing (:75). So: every item MUST have a `texture` variant with state "1". This is the real crash path. LoP adults have 1 texture alternate (index 0..1): texture "2" is absent and falls back to "1" silently.
- No `butcherable` behavior: nothing happens, vanilla harvest unchanged (HarvestablePatch.cs:31-38). No crash.
- Carcass: `AnimalCarcass` copied from `deaddecay.decayedBlock` (:92-98); table places that block, null-checked (BlockEntityButcherTable.cs:79-82). A missing carcass block does NOT crash in 1.14.3. LoP entities all have `deaddecay` with vanilla `carcass-small|medium|large` (survey.csv `decayed` column).
- Changelog crash text: no changelog in the zip. "Not determinable from the provided material" beyond the code path above.

## 2. Yield source (gate 3 is satisfied by construction)
- `AnimalDrops` = the entity's own harvestable `jsonDrops`, copied raw by reflection (EntityBehaviorButcherable.cs:84-85). So hook/table yields come from LoP's existing drops (after load-time patches, including ConfigLib multipliers), not from numbers we write.
- Table yields: ButcheringRewards + AnimalDrops minus skinning exclusives (`hide-, fat, feather, fleece-, wool-, hair-, fur-, pelt-, ivory-`) (Table:74-77, Workstation:75). Hook/skinning yields: SkinningRewards + AnimalDrops matching those prefixes (Hook:254-255).
- Food items are scaled by `animalWeight` (Workstation:334-339; harvestable weight, 1.0 for a healthy animal) and `butcheringTableLootMultiplier` (default 1).
- Knife harvest on a butcherable entity is reduced: `dropQuantityMultiplier *= 0.5` (0.8 in FieldHarvestingLightMode) (HarvestablePatch.cs:31-37).
- The only numbers a compat writes are the extras (`butcheringRewards` primemeat/offal/sinew, `skinningRewards`), blood amount, mass, workload. These are copied from a cited Butchering anchor creature per size class (section 5), not invented.

## 3. Size handling in Butchering
- `mass` (item attribute, default 0.01, ItemButcherable.cs:18) drives carry slowdown: walkspeed modifier `+= mass * AnimalMassMultiplier(1.0) * animalCarryingEfficiencyMul(-2)` => -2 x mass, clamped at -0.8 (ButcheringSystem.cs:141-162). Pickup needs a free hand; one corpse per hand (maxstacksize 1).
- `size` only offsets table mesh placement (Table:35-38). `butcheringWorkLoad` small|medium|large sets hang time before bleed-out 1h|2h|4h (Hook:62-70) and cleaver time 2.6|4.6|6.6 s (Workstation:134-148).
- No size, mass, or hitbox gate exists on hook, table, or pickup. Butchering's own giants (elephantidae, rhinocerotidae) are one whole corpse with mass 0.16, blood 400, workload large, generic `generichuge` shapes. No piece-splitting exists in the code.
- Bleed: hook finds a bucket 1..6 blocks below, adds `bloodAmount` portions, capped 1000 (Hook:160-200). Max precedent 400 (600 in FotSA compat).

## 4. Prior art
- WIP "(WIP) Butchering Compatibility Patch: Legacy of the Phanerozoic" (alias butcheringcompatlotp): ModDB page and API return 404 on 2026-11-02 and it is not found by ModDB search ("Phanerozoic", "Carnivorous Bull", "butchering"). Could not be downloaded or read. Its pieces approach is known only from the task brief.
- Butchering LoP-Dromaeo compat 1.0.1 (alias butdrocom, tagged 1.21.x only, depends on butchering 1.10.11): 4 JSON. Ships its own itemtype `deaddro-{large,medium,small,tiny}` (mass 0.04..0.01, blood 300/200/50/0, poultry rewards) and patches `dromaeosauridae:entities/land/dromaeosauridae.json` with itemByType by species glob. Right: native carcass, dependsOn gating, generic shapes. Leaves: no texture variant group (works only via the texture-less path), glob order risk (`dromaeosauridae-*` listed before `*-baby-*`, so babies resolve to "small" since first match wins), no skinning rewards, client side not checked, 1.21 only.
- FotSA Butchering Compat 0.4.1: same native pattern. modinfo deps only `game` + `butchering`; each family gated per patch with `dependsOn`; own itemtypes `enabled:false` switched on by `replace /enabled` with dependsOn; no shapes/textures (reuses Butchering generic shapes). This is the target shape.

## 5. Designs considered
| Design | How | Verdict |
|---|---|---|
| A. Native carcass per species | `butcherable` behavior appended to server+client behaviors; one compat itemtype per family with a variant per species x age | Works for every size; yields flow from LoP drops automatically; append-only patch keeps ConfigLib indices. |
| B. Butcherable pieces on death | Without code, needs LoP harvestable drops rewritten to emit quarter items. Quarter items get no AnimalDrops (only set by the behavior), so all meat/hide numbers would have to be hand-written into butcheringRewards | Rejected: rewrites `server/behaviors/13/drops`, which ConfigLib pointers address (164 float pointers in Abeli alone); duplicates and freezes yield numbers (gate 3 risk); needs a DLL to do it cleanly. |
| C. Hybrid by size class | A for small..giant, B for sauropods | Rejected for the same reasons as B; Butchering already supports a whole huge corpse (elephantidae) and clamps slowdown. |

**Pick: A, native carcass, with per-size-class parameters.** Giants are handled by mass (slowdown up to the -0.8 clamp), workload large (4 h hang, slowest cleaver), and `generichuge` shapes, which is how Butchering itself treats elephants and rhinos.

## 6. Size classes (judgment; anchors cited)
Class = max(class by adult-equivalent meat avg from LoP drops, class by hitbox height). Meat: <8 small, 8-30 medium, 30-120 large, 120-250 giant, >250 colossal. Hitbox y: <0.8 small, <1.6 medium, <4.5 large, <8 giant, >=8 colossal.

| Class | mass | blood | workload | shapes | rewards anchor (Butchering itemtypes/butchercreatures/...) |
|---|---|---|---|---|---|
| small | 0.01 | 50 | small | genericsmall | carnivore: fox.json (sinew 1.6, offal 1.6); herbivore: hare.json (offal 1.6) |
| medium | 0.03 | 100 | medium | genericmedium | carnivore: wolf.json (sinew 3, offal 1.6); herbivore: pig.json (primemeat 3, offal 4) |
| large | 0.1 / 0.06 | 400 | large | genericlarge | carnivore: bear.json brown (mass 0.1, sinew 3, offal 4); herbivore: moose.json (mass 0.06, primemeat 2, offal 3) |
| giant | 0.16 | 400 | large | generichuge | elephantidae.json male (primemeat 6, offal 3) |
| colossal | 0.4 | 400 | large | generichuge | elephantidae.json rewards; mass 0.4 is a design choice: -2 x 0.4 = -0.8 hits Butchering's clamp (dragging a sauropod is as slow as the mod allows) |

Babies use the same thresholds on their own drops (most land small or medium).

Per size class (gate 4):
- Pick-up weight/slowdown: walkspeed -0.02 / -0.06 / -0.2 (-0.12 herbivore) / -0.32 / -0.8 (clamp).
- Hook/table size: no gate in code; generic hanging/dead shape per class; workload small/medium/large/large/large.
- Yield volume: LoP's own drops (e.g. Abeli adults 50-100 bushmeat, macronaria up to 400), unchanged; Butchering adds only the anchor extras. Knife harvest becomes x0.5 for these species (Butchering rule), so the table is the full-yield path.

## 7. Mosasaurs and other aquatics
Pickup is an interaction with the dead entity (any position the player can reach); nothing in the code requires land. A drowned corpse at depth is reachable only by swimming. Treated as native with their class; noted in TEST.md.

## 8. Per-family work estimate
One generator script (scripts/gen_family.py) driven by the resolved LoP entity JSON: ~1 itemtype + 1 patch + lang keys per family, 4-60 species-age rows each, minutes per family. Verification script per family: JSON parse, patch targets resolve, item codes cover every species x age, zip integrity.

## Not determinable from the provided material
- The WIP LoP patch contents (page 404).
- Butchering changelog text for the carcass crash (no changelog file; code path in section 1 is what 1.14.3 does).
- Vanilla `EntityBehaviorHarvestable.AnimalWeight` source and base `dropQuantityMultiplier` (outside the Butchering DLL).
