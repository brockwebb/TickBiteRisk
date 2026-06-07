# Regional bundle TEVV materiality report

🚨 **REVIEW_RECOMMENDED: YES**
- structural change(s): 6 (see Structural changes)

- Built-from commit: `8b427d804bbcf86928a4605d393a88c1fddd69ca`
- Deployed commit: `none`
- Forecast year(s): 2024, 2025, 2026
- Total counties (new): 283

## Counts

- Counties flagged: 0 of 283 (0.0%)
- By rule — (a) relative-incidence: 0; (b) category-change: 0; (c) score-bin: 0

**No material change.** No county tripped rule (a), (b), or (c).

## Structural changes

⚠️ Structural change detected (schema / field population / caveats / size / record counts):
- B1 schema_version: county-week-risk-static-v1 -> county-week-risk-static-v2
- B2 field 'risk_score_high' non-null rate 0.0% -> 100.0%
- B2 field 'risk_score_low' non-null rate 0.0% -> 100.0%
- B3 caveat added: Prediction intervals apply forecast residuals pooled across the region's counties to each county's point forecast, so a low-incidence county's interval can extend well beyond its own historical range.
- B4 model_card.json size 8621 -> 9065 (+5.2%, +0.0 MB)
- B4 static_export_manifest.json size 1635 -> 1871 (+14.4%, +0.0 MB)

## Distribution shifts

- Score-floor (score==1) population: 357 → 357
- Category histogram (deployed): {'very_low': 393, 'very_high': 243, 'low': 60, 'moderate': 105, 'high': 48}
- Category histogram (new): {'very_low': 393, 'very_high': 243, 'low': 60, 'moderate': 105, 'high': 48}

## Provenance / integrity

- record_counts unchanged between bundles

