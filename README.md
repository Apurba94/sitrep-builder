# SitRep Builder

Turn your team's activity records into a situation report: who is doing what and where, progress on indicators, and a first draft of the summary. It runs offline.

```
python -m sitrep_builder
```

Then open http://127.0.0.1:8040. Use the browser's print command for a paper copy. It needs Python 3.10 or newer.

## What it gives you

- **A 4W matrix:** who does what, where and when
- **People reached,** counted carefully
- **Week-on-week change** by sector
- **Indicators against time:** progress compared with the share of the response period used, so "60% done" means something
- **Gaps and overlaps:** sectors and areas with nothing reported, and places where several partners do the same thing
- **A draft summary** from the numbers, for a person to edit

## Counting people honestly

The most common mistake in humanitarian reports is adding partners' numbers together. If two organisations each give hygiene kits to mostly the same families in one area, the sum counts many people twice.

So this tool never adds different partners' figures for the same activity and area. It takes the largest, and adds across different activities and areas. The result is labelled "at least". It is still not a count of unique people: one person reached by food and water counts twice, and only a shared register could fix that.

## How it is tested

Counting rules are tested by hand and on random data, where the result must stay between the largest single figure and the plain sum. Indicator states, week boundaries and gaps have their own tests, and the full report is tested from entered activities.

## Limits

It is for a single team's data on one computer, with no import from partner systems. Narrative text is a skeleton: context, causes and risks must come from people. Beneficiary figures are as good as what was reported.

## Tests

```
python -m unittest discover -s tests
```

MIT licence.
