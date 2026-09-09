# Contributing Knowledge Modules

## Era/site/overlay pack checklist

A new pack must:

1. identify whether it is a `historical_era`, `site_tradition`, `genre_overlay`, or `fantasy_overlay`;
2. define period and region boundaries;
3. label individual claims with a compatibility value and confidence;
4. include incompatible/anachronistic examples that are actually useful for prompt failure prevention;
5. link evidence sources;
6. state what additional narrowing strict reconstruction needs;
7. avoid treating one surviving elite object as universal dress for all people.

Run `python scripts/validate_repo.py` after editing.

## Art-method checklist

A new method is not accepted if it is only an adjective bundle. It must explain:

- material;
- fabrication process;
- visible production marks;
- edge/mark/color/surface behavior;
- composition behavior;
- structural limits;
- aging;
- compatible artifact forms;
- image-model failure modes;
- evaluation criteria.

If a new method differs only by palette from an existing method, it is probably a variant rather than a new module.

## Case checklist

A case must contain a valid `case.json`, compile without errors, and identify what it is meant to validate. An output image is optional. If an image is added, evaluation should distinguish aesthetic success from historical/material correctness.
