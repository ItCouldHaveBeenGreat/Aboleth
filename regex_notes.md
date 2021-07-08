# Damage Regex

```
(takes|or|plus|\{\@h\}) ?([0-9]+) ?(?:\(\{@damage ([d0-9\+\- ]+)\}(?: plus \{@damage ([d0-9\+\- ]+)\})?\))? ([A-z]+)? ?damage
```

## Groups
1. Clause. Defines the damage entry's relationship (if any) to the other damage entries.
2. Stated Damage. Only used when damage dice strings are unavailable.
3. Damage Dice String.
4. Secondary Damage Dice String. Only used for special monsters (with multiple types of dice in play)
5. Damage Type.

## Examples
{@atk mw} {@hit 5} to hit, reach 5 ft., one target. {@h}7 ({@damage 1d8 + 3}) slashing damage, or 8 ({@damage 1d10 + 3}) slashing damage if used with two hands.

{@atk mw} {@hit 6} to hit, reach 15 ft., one target. {@h}11 ({@damage 2d6 + 4}) bludgeoning damage. If the target is a creature, it is {@condition grappled} (escape {@dc 14}). Until this grapple ends, the target is {@condition restrained}. The chaos quadrapod can grapple no more than two targets at a time.

{@atk mw} {@hit 9} to hit, reach 10 ft., one target. {@h}16 ({@damage 2d10 + 5}) piercing damage, and the target is {@condition grappled} (escape {@dc 17}). Until this grapple ends, the target is {@condition restrained}, and the deep crow can't use its mandibles on another target.

{@atk mw} {@hit 4} to hit, reach 5 ft., one target. {@h}7 ({@damage 1d10 + 2}) piercing damage.

{@atk mw} {@hit 16} to hit, reach 10 ft., one target. {@h}17 ({@damage 2d8 + 8}) piercing damage plus 36 ({@damage 8d8}) fire damage.

{@atk mw} {@hit 11} to hit, reach 5/20 ft., one target. {@h}14 ({@damage 2d6 + 7}) slashing damage, or 17 ({@damage 2d6 + 10}) slashing damage while raging, plus 3 ({@damage 1d6}) fire damage from the gauntlets of flaming fury.

{@atk mw} {@hit 0} to hit ({@hit 4} to hit with shillelagh), reach 5 ft., one target. {@h}1 ({@damage 1d4 - 1}) bludgeoning damage, or 6 ({@damage 1d8 + 2}) bludgeoning damage with shillelagh.

{@atk mw} {@hit 4} to hit, reach 5 ft., one target. {@h}1 piercing damage in raven form, or 4 ({@damage 1d4 + 2}) piercing damage in hybrid form. If the target is humanoid, it must succeed on a {@dc 10} Constitution saving throw or be cursed with wereraven lycanthropy.

 {@atk mw,rw} {@hit 6} to hit, reach 5 ft. or range 20/60 ft., one target. {@h}12 ({@damage 1d6 + 4} plus {@damage 1d8}) piercing damage, or 13 ({@damage 2d8 + 4}) piercing damage if used with two hands to make a melee attack.

The giant moves up to 30 feet in a straight line and can move through the space of any creature smaller than Huge. The first time it enters a creature's space during this move, it makes a fireshield attack against that creature. If the attack hits, the target must also succeed on a {@dc 21} Strength saving throw or be pushed ahead of the giant for the rest of this move. If a creature fails the save by 5 or more, it is also knocked {@condition prone} and takes 18 ({@damage 3d6 + 8}) bludgeoning damage, or 29 ({@damage 6d6 + 8}) bludgeoning damage if it was already {@condition prone}.