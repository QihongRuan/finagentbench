# FinAgentBench

**Live results: https://qihongruan.github.io/finagentbench/**

Can LLM agents do quantitative finance research? FinAgentBench measures two
distinct capabilities, separately, across 20+ frontier models (Claude, GPT,
Gemini, Grok, DeepSeek, Qwen, Kimi, GLM, and more) running through one
identical agent harness on a single inference platform:

- **Track A — Execution.** The agent receives a written method specification
  (results withheld), read-only raw data, and a bash sandbox, and must
  reproduce the study's numbers. Five tasks of increasing difficulty, from a
  20-stock momentum portfolio up to end-to-end replication of a canonical
  machine-learning asset-pricing study (four model classes trained, annual
  refits, out-of-sample portfolio evaluation).
- **Track B — Judgment.** The model reads financial text — news headlines,
  full analyst articles, SEC filing MD&A sections, earnings press releases,
  13F disclosures — and predicts forward returns. Every track pairs each model
  with a withheld-text control run; the flagship track uses only articles
  published *after* model training cutoffs (verified per model).

## Headline results

1. **Execution is commoditized.** Nearly every model — including ones costing
   a fraction of a cent per run — perfectly replicates standard quant studies
   from spec. The capability frontier only appears at full-paper scale, where
   the field splits roughly in half.
2. **Reading long financial text yields real judgment.** On post-cutoff
   analyst articles, flagship models reach Spearman ICs ≈ 0.4–0.5 vs ≈ 0.2 for
   small models; withheld-text controls collapse to ≈ 0 for everyone.
3. **On historical data, apparent skill is often memorization.** Some models
   predict historical event outcomes *better with the news withheld* — a
   methodological warning for the "LLMs predict stocks" literature. The honest
   metric is ΔIC = IC(text) − IC(withheld).
4. **Reliability, quantified.** Across repeated identical runs, ~2–3% silently
   produce wrong answers and ~6% die on provider infrastructure.
5. **Published ML alpha decays.** Re-running a canonical ML asset-pricing
   design on 2015–2021: decile long-short Sharpe falls from 2+ to ≈ 0.2–0.3,
   while the nonlinear-beats-linear ranking survives.

Full tables, controls, per-model training-cutoff audit, cost-optimal routing,
and honest caveats are on the [live site](https://qihongruan.github.io/finagentbench/).

## Methodology at a glance

- One two-tool agent loop (`run_bash` + `submit_answer`), step-capped, identical
  for every model; provider API quirks normalized at the gateway and documented.
- Grading is scripted: submitted statistics vs reference implementations run on
  private data extracts (loose ±5% / strict ±1% tolerance bands). No LLM judges,
  no hand-entered numbers — the site is generated programmatically from run logs.
- Underlying market and text datasets are licensed; this repository publishes
  aggregate results only.

## Provenance

Built and operated by Agentic Sciences (Qihong Ruan). Total inference budget
for the entire benchmark: under $750.
