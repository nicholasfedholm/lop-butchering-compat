# In-game test for lopbutcheringcompat 0.1.0 (for Nick)

Setup (you install; nothing was put in Mods by this run):
1. Back up Mods. Copy into Mods: `work\dl\butchering_1.14.3.zip` (Butchering, ModDB latest) and `out\lopbutcheringcompat_0.1.0.zip`.
2. Use a creative test world first (or a copy of your world). Butchering adds its own blocks/items; removing it later leaves unknown blocks/items in that world.

Pilot: Carnivorous Bull (abelisauridae). Expected values come from `work\coverage\abelisauridae.csv`.
3. Spawn an adult male Carnotaurus (creative inventory spawn item "Carnotaurus (Male)", or your usual spawn command) and kill it. Wait for the death animation.
4. With an EMPTY right hand, right-click the corpse. Expect: item "Carnotaurus carcass" in your hand/inventory, corpse gone. Walk: you should be noticeably slower (mass 0.1, about -20% walk speed).
5. Repeat with `abelisauridae-carnotaurus-baby-female`: "Carnotaurus juvenile carcass", slowdown about -6%.
6. Build Butchering's butcher hook (check the handbook for its recipe) with a bucket 1-6 blocks below. Hang the adult carcass. After about 4 in-game hours (workload large) bleed it out: the bucket gets 400 blood portions (cap 1000).
7. Skin on the hook: expect LoP's hide and fat drops (adult carnotaurus: `hide-raw-huge` avg 5, `fat` avg 15) plus nothing extra (skinningRewards empty).
8. Butcher the bled-out carcass on the butcher table: expect LoP's meat (`bushmeat-raw` avg 100) plus anchor extras from Butchering's brown bear: `sinew-wet` avg 3, `offal-bloody` avg 4. The vanilla `carcass-large` block should be placed after butchering.
9. Control: kill another adult and knife-harvest it in the field instead. Expect about half the usual LoP yield (Butchering's rule for butcherable animals: drop multiplier x0.5).
10. Giant check: spawn and kill any tyrannosaurid adult ( giant class, mass 0.16, about -32% walk speed) and one macronaria adult (colossal, mass 0.4, walk speed at Butchering's -80% clamp). Confirm you can still carry and hang them; note how the generic huge carcass looks on the hook.
11. Aquatic check: kill a mosasaur in water and try step 4 while swimming. Report if the pickup does not work.
12. Check `Logs\server-main.log` and `client-main.log` for `Could not find butchering item`, `butchering`, or `lopbutcheringcompat` errors.

Pass = steps 4-8 behave as stated and step 12 shows no compat errors. Report any family whose carcass name shows a raw lang key (`item-dead...`).
