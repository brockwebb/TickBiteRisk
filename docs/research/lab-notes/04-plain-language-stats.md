# Plain-Language Stats

Status: draft
Primary sources: docs/model-spec.md; public/data/model_card.json; public/research-data/regional/model_card.json; tickbiterisk/modeling/risk_score.py; tickbiterisk/modeling/regional_forecast_typicality.py
Reviewer focus: methods/statistics
Last checked against commit: 7a83b4e

This chapter will turn the statistical contract into reviewable public language so forecast labels, chart bands, and tooltips explain reported incidence per 100k, annual forecasts, predicted scores, percentiles, and intervals without implying clinical certainty.

## Reported Incidence Per 100k

Technical definition: reported incidence per 100k is reported Lyme disease
cases divided by the relevant population denominator and multiplied by
100,000.

Plain-language sentence: this is a way to compare reported Lyme pressure
between counties of different sizes, not a count of every infection and not a
personal chance of getting sick.

## Annual Forecast

Technical definition: annual forecast is the selected model branch's predicted
county-year reported Lyme incidence per 100k and corresponding reported-case
proxy for a future year.

Plain-language sentence: the model first estimates the year's reported Lyme
pressure for a county, then later display steps spread that annual estimate
across weeks.

## Weekly Seasonal Risk

Technical definition: weekly seasonal risk is the annual forecast multiplied
by CDC national Lyme onset seasonality shares for MMWR weeks.

Plain-language sentence: the weekly curve shows how the annual forecast is
allocated through the season; it is not observed county-week truth and not
observed county-week Lyme data.

## Predicted Score

Technical definition: Predicted score is the rounded 1-10 value created by
mapping predicted weekly reported-incidence pressure to the selected score
denominator.

Plain-language sentence: the predicted score is a relative display score for
comparing county-weeks on this product's scale; 10 is the top of the display
scale, not a medical or probability cutoff.

The predicted score is not a probability. It is a relative 1-10 display score
derived from predicted weekly reported-incidence pressure and the selected
scale denominator. In the current scoring code, that denominator is the
nearest-rank benchmark quantile of predicted weekly incidence, default `0.95`,
times the headroom multiplier, default `1.2`; raw score is rounded and clamped
to the `1..10` display range.

## Forecast Percentile

Technical definition: Forecast percentile is the position of the selected
forecast relative to the same county's prior reported annual incidence history
through the forecast origin.

Plain-language sentence: it says whether the forecast looks low, usual, or
high compared with that county's own reported history.

## Forecast Interval

Technical definition: Forecast interval is an empirical prediction range built
from historical forecast residuals around reported-incidence forecasts, when
the selected artifact includes interval rows.

Plain-language sentence: it shows how far historical forecasts have missed in the
past for this modeled quantity when interval data are available.

The forecast interval is not a medical confidence interval. It is an empirical
range from historical forecast errors around reported-incidence forecasts. The
current Maryland public model card records interval method `not_available`;
the regional research artifact records
`empirical_rolling_origin_residual_quantile`.

## Typical, Above Typical, And Much Higher Than Typical

Technical definition: "typical" refers to a forecast inside the middle band of
the county's prior reported-incidence history. This band is percentile or
IQR-like county-history context, not an arithmetic mean. "Above typical" is
above that typical band; "much higher than typical" is near the upper tail of
the same prior-history comparison.

Plain-language sentence: these labels compare the forecast with what has been
reported for the same county before, not with a clinical threshold.

Avoid "average" in public labels. If it appears casually in review drafts,
translate it to "typical" unless the sentence is explicitly talking about an
arithmetic mean.

## Chart Marks And Bands

Technical definition: chart points and bands can show the selected annual
forecast, weekly seasonal allocation, prior-history reference band, forecast
percentile, and forecast interval bounds.

Plain-language sentence: marks show the model estimate. A typical band shows
where that county's prior reported history usually sits; a forecast interval
band shows historical forecast-error uncertainty when interval rows are
available. Those bands answer different questions, so the chart should keep
historical context, seasonal allocation, and forecast-error uncertainty
visually distinct.

## Language To Avoid

Avoid calling the score a probability, infection chance, diagnosis, treatment
recommendation, or personal medical risk. Avoid saying weekly values are
observed cases, observed county-week truth, or observed county-week outcomes.
Avoid calling forecast intervals clinical confidence intervals or medical
certainty bands. Avoid public labels such as "average" or "worse than average"
when the intended meaning is county-history typicality rather than an
arithmetic mean.

Use "reported incidence", "annual forecast", "weekly seasonal allocation",
"relative predicted score", "forecast percentile", and "forecast interval"
instead. Keep the public wording tied to reported surveillance incidence and
the selected model scale.
