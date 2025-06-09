# TickBiteRisk – API Specification

> **File location:** `/api/API_SPEC.md`

---

## 1  Overview

A single REST endpoint returns the posterior probability that a tick bite acquired in a given U.S. county, with specified attachment duration(s), will result in Lyme disease infection.  Results include 95 % credible intervals and metadata flags indicating data freshness.

Base URL (Docker default)

```
http://localhost:8000
```

Production deployments SHOULD serve the API behind HTTPS.

---

## 2  Endpoint: `GET /risk`

### 2.1  Query parameters

| Name     | Type                           | Required                  | Example                   | Description                                                                                             |
| -------- | ------------------------------ | ------------------------- | ------------------------- | ------------------------------------------------------------------------------------------------------- |
| `fips`   | string (5‑digit)               | ✅                         | `24003`                   | County FIPS code. Leading zeros allowed.                                                                |
| `tau`    | number **or** array of numbers | ✅                         | `24`  or  `tau=12&tau=36` | Attachment duration(s) in hours. Each must be ≥0 & ≤168.                                                |
| `k`      | integer                        | optional, default `1`     | `2`                       | Number of attached nymphs (identical τ assumed for each).                                               |
| `date`   | `YYYY‑MM‑DD`                   | optional, default *today* | `2025‑07‑15`              | Returns risk based on priors valid for ISO week of this date. Useful for querying historical baselines. |
| `pretty` | boolean                        | optional                  | `true`                    | If `true`, JSON is indented for human reading (no effect on content).                                   |

### 2.2  Successful response (`200 OK`)

```jsonc
{
  "fips": "24003",
  "tau": [24],
  "k": 1,
  "date": "2025-07-15",
  "risk": [0.022],
  "ci95": [[0.011, 0.041]],
  "theta_source": "observed",      // 'observed' | 'forecast' | 'static'
  "lambda_source": "forecast",     // same enum
  "last_theta_update": "2024-11-20",
  "last_lambda_update": "2025-07-07",
  "version": "v1.0.0"
}
```

*Elements `risk` and `ci95` are arrays aligned with `tau` order.*

### 2.3  Error responses

| Status                    | JSON payload                               | Typical cause                   |
| ------------------------- | ------------------------------------------ | ------------------------------- |
| `400 Bad Request`         | `{ "detail": "tau must be 0–168 hours" }`  | Validation failed               |
| `404 Not Found`           | `{ "detail": "Unknown FIPS code" }`        | Non‑existent county             |
| `503 Service Unavailable` | `{ "detail": "Model priors unavailable" }` | Postgres down or priors missing |

All errors follow FastAPI’s Problem Details format (`detail`, optional `type`).

---

## 3  OpenAPI schema (excerpt)

```yaml
openapi: 3.1.0
info:
  title: TickBiteRisk API
  version: 1.0.0
paths:
  /risk:
    get:
      summary: Per‑bite Lyme probability
      parameters:
        - in: query
          name: fips
          schema: {type: string, pattern: "^\d{5}$"}
          required: true
        - in: query
          name: tau
          schema: {type: array, items: {type: number}}
          style: form
          explode: true
          required: true
        - in: query
          name: k
          schema: {type: integer, minimum: 1}
          required: false
        - in: query
          name: date
          schema: {type: string, format: date}
          required: false
      responses:
        '200':
          description: OK
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/RiskResponse'
        '400': { $ref: '#/components/responses/BadRequest' }
        '404': { $ref: '#/components/responses/NotFound' }
components:
  schemas:
    RiskResponse:
      type: object
      properties:
        fips: {type: string}
        tau: {type: array, items: {type: number}}
        k: {type: integer}
        date: {type: string, format: date}
        risk: {type: array, items: {type: number}}
        ci95:
          type: array
          items:
            type: array
            items: {type: number}
            minItems: 2
            maxItems: 2
        theta_source: {type: string}
        lambda_source: {type: string}
        last_theta_update: {type: string, format: date}
        last_lambda_update: {type: string, format: date}
        version: {type: string}
  responses:
    BadRequest:
      description: Bad Request
      content:
        application/json:
          schema: {type: object, properties: {detail: {type: string}}}
    NotFound:
      description: Not Found
      content:
        application/json:
          schema: {type: object, properties: {detail: {type: string}}}
```

Full YAML lives at `/api/openapi.yaml`; FastAPI auto‑serves interactive docs at `/docs`.

---

*Last updated: 2025‑06‑08 (draft v0.1)*

