# Plain-Language Stats

Status: draft
Primary sources: docs/model-spec.md; public/data/model_card.json; public/research-data/regional/model_card.json; tickbiterisk/modeling/risk_score.py; tickbiterisk/modeling/regional_forecast_typicality.py
Reviewer focus: methods/statistics
Last checked against commit: 3456791

This chapter will turn the statistical contract into reviewable public language so forecast labels, chart bands, and tooltips explain reported incidence per 100k, annual forecasts, predicted scores, percentiles, and intervals without implying clinical certainty.

## Reported Incidence Per 100k

The phrase reported incidence per 100k refers to reported Lyme disease cases normalized by population. It is not true Lyme burden and should not be described as an observed infection rate for every exposed person.

## Annual Forecast

## Weekly Seasonal Risk

Weekly seasonal risk is an allocation of annual pressure across the season. It is not observed county-week truth.

## Predicted Score

Predicted score is a relative scale derived from the model output for communication and comparison. It is not a probability.

## Forecast Percentile

Forecast percentile compares a forecast against a relevant historical or modeled reference distribution.

## Forecast Interval

Forecast interval communicates model uncertainty around the annual forecast. It is not a medical confidence interval.

## Average, Worse Than Average, And Much Higher Than Typical

## Chart Marks And Bands

## Language To Avoid
