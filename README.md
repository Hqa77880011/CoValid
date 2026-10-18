# CoValid

Implementation of **Policy-sensitive co-validity of multi-issuer evidence**.

Implements conservative finite joint-state construction, nonempty evidence checks, dual permitting/rejecting witnesses and cost-aware issuer acquisition. Historical observations never become present-value guarantees. A decision uses the effect window in its input.

## Install

Use Python 3.11 or newer. Create and activate a virtual environment, then install the package:

```bash
git clone https://github.com/Hqa77880011/CoValid.git
cd CoValid
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS or `.venv\Scripts\Activate.ps1` in PowerShell.

```bash
python -m pip install -e .
```

## Prepare data

```bash
python -m covalid prepare --count 200 --seed 17 --output data/workload.jsonl
```

The generator constructs finite workloads from the formal problem. It writes one JSON object per line. Import recorded or independently constructed cases with the same schema.

`domains` declares finite attribute domains. `evidence` gives attribute, value, lease or historical kind, guaranteed interval and revision. `constraints` contains public if/then causal relations. `issuers` specifies query cost, latency, availability and revision. `actual` is evaluator/issuer state, not evidence available to the decision procedure.

## Execute and compare

```bash
python -m covalid run --data data/workload.jsonl --output runs/main
python -m covalid suite --data data/workload.jsonl --methods covalid full_refresh --output runs/comparison
```

Omit `--methods` in `suite` to include every comparison method and ablation.

`covalid` selects an issuer by opposing-witness separation per acquisition cost; `full_refresh` queries every issuer; `round_robin` uses fixed order; `no_nonempty`, `issued_at_lease` and `no_causal_constraints` remove the named semantic checks.

These are algorithmic workloads without learned parameters. `--count` controls scenario count and `--seed` controls generation. Repeat with independent seeds for comparisons.

## Evaluate and visualize

Each method writes `records.jsonl` with per-case outputs and measurements, plus `metrics.json` with counts, means, sample standard deviations and quantiles. Rates are fractions. Conditional metrics exclude cases outside their denominator. Timers cover method execution; independent scoring is outside this timer.

False allow, oracle-conditioned benign completion/false denial, query counts and failures, acquisition cost, modeled issuer delay and measured local kernel runtime.

```bash
python -m covalid plot --inputs runs/comparison/covalid runs/comparison/full_refresh --output figures
```

Plotting creates `summary.csv` and one PNG per numeric metric. RSS includes the Python runtime and imported libraries. Output bytes measure JSON serialization size.

## Implementation conventions

Input evidence is the post-verification boundary: service integrations must verify issuer signatures, subject scope and registry authority before supplying records. The finite acquisition backend models issuer replies in memory. `issuer_latency_sum` is declared simulated delay; `latency_ms` is measured kernel time. No network timings are inferred from the simulation.


## Uncertainty and paired comparisons

```bash
python -m covalid.statistics --records runs/main/covalid/records.jsonl --output results/intervals.json
```

Supply --reference with a matched record file for paired differences. Resampling uses independent case IDs, or explicit cluster IDs when provided. Repeated observations from one source unit must share cluster. Zero-event bounds refer to an event in an independent cluster.

## Fixed reproduction setting

Finite trusted issuer/world model: member/MFA/level/color domains, lease effect window[2,3], costs/latencies and issuer availability.

The checked-in entry point fixes data seeds, methods, budgets and output paths. Inspect its commands without starting any computation:

```bash
python reproduce.py --plan
```

Remove `--plan` to execute the registered pipeline in a fresh output directory. The entry point calls the existing implementation; it does not insert paper results. Installation uses the package instructions above.
