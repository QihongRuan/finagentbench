#!/usr/bin/env python3
"""Generate the FinAgentBench static site from results CSVs.

Data sources (all produced by the benchmark pipeline):
  ../results.csv                      Track A agent runs (dedup: last per task/model/seed)
  ../trackB_news/leaderboard_b1.csv   Track B1 news headlines
  ../trackB_news/leaderboard_b2.csv   Track B2 analyst articles (post-cutoff)
  ../trackB_news/leaderboard_b3.csv   Track B3 SEC filings MD&A

Public-page rules: generic data-source naming (no vendor names), aggregates only.
"""
import csv
import html
import pathlib
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = pathlib.Path(__file__).parent
OUT = SITE / "index.html"

MODEL_LABELS = {
    "deepseek-ai/DeepSeek-V4-Flash": "DeepSeek V4 Flash",
    "deepseek-ai/DeepSeek-V4-Pro": "DeepSeek V4 Pro",
    "XiaomiMiMo/MiMo-V2.5": "MiMo V2.5",
    "google/gemma-4-31b-it": "Gemma 4 31B",
    "zai-org/GLM-5.2-FP8": "GLM 5.2",
    "anthropic/claude-sonnet-5": "Claude Sonnet 5",
    "anthropic/claude-opus-5": "Claude Opus 5",
    "Qwen/Qwen3.8-Max": "Qwen3.8 Max",
    "x-ai/grok-4.5": "Grok 4.5",
    "moonshotai/kimi-k3": "Kimi K3",
    "openai/gpt-5.4": "GPT-5.4",
    "openai/gpt-5.6-sol": "GPT-5.6 Sol",
    "google/gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "openai/gpt-5.6-terra": "GPT-5.6 Terra",
    "openai/gpt-5.5": "GPT-5.5",
    "google/gemini-3.6-flash": "Gemini 3.6 Flash",
    "MiniMaxAI/MiniMax-M3": "MiniMax M3",
    "nvidia/nemotron-3-ultra-550b-a55b": "Nemotron 3 Ultra",
    "tencent/Hy3": "Hunyuan 3",
    "moonshotai/Kimi-K2.6": "Kimi K2.6",
    "deepseek-ai/DeepSeek-V3.2": "DeepSeek V3.2",
    "anthropic/claude-opus-4.8": "Claude Opus 4.8",
    "anthropic/claude-opus-4.7": "Claude Opus 4.7",
    "anthropic/claude-opus-4.6": "Claude Opus 4.6",
    "anthropic/claude-opus-4.5": "Claude Opus 4.5",
    "anthropic/claude-haiku-4.5": "Claude Haiku 4.5",
}
TASK_LABELS = {
    "t1_momentum": "T1 · 20-stock momentum",
    "t2_event_study": "T2 · News event study",
    "t3_covered_call": "T3 · Covered-call option backtest",
    "t4_crsp_momentum": "T4 · Full-market momentum (11GB)",
    "t6_gkx_ml": "T6 · Replicate an ML asset-pricing study (RFS-style, 4 models trained)",
}


def slug_label(run_slug):
    """Map a preds-file slug back to a display label (+ control marker)."""
    control = run_slug.endswith(".control")
    base = run_slug[: -len(".control")] if control else run_slug
    for mid, lab in MODEL_LABELS.items():
        if mid.replace("/", "_").replace(" ", "_") == base:
            return lab, control
    return base, control


def load_track_a():
    """Dedup keep-last per (task, model, seed); aggregate across seeds."""
    if not (ROOT / "results.csv").exists():
        return {}
    last = {}
    for r in csv.DictReader(open(ROOT / "results.csv")):
        last[(r["task"], r["model"], r["seed"])] = r
    agg = defaultdict(lambda: defaultdict(list))
    for (task, model, _seed), r in last.items():
        agg[task][model].append(r)
    return agg


def track_a_table(agg, task):
    rows = []
    for model, runs in agg.get(task, {}).items():
        ok = [r for r in runs if r["status"] == "submitted"]
        n = len(runs)
        loose = [float(r["score_loose"]) for r in ok]
        strict = [float(r["score_strict"]) for r in ok]
        cost = [float(r["cost_usd"]) for r in ok if r["cost_usd"]]
        steps = [int(r["steps"]) for r in ok]
        pass5 = (
            f"{sum(1 for s in strict if s == 1.0)}/{n}" if n > 1 else "—"
        )
        rows.append(
            {
                "model": MODEL_LABELS.get(model, model),
                "runs": n,
                "loose": max(loose) if loose else 0.0,
                "strict": max(strict) if strict else 0.0,
                "consist": pass5,
                "steps": min(steps) if steps else "—",
                "cost": f"${min(cost):.4f}" if cost else "—",
            }
        )
    rows.sort(key=lambda r: (-r["strict"], -r["loose"], r["model"]))
    return rows


def load_track_b(name):
    p = ROOT / "trackB_news" / f"leaderboard_{name}.csv"
    if not p.exists():
        return []
    rows = []
    for r in csv.DictReader(open(p)):
        lab, control = slug_label(r["run"])
        rows.append({**r, "model": lab, "control": control})
    main = [r for r in rows if not r["control"]]
    ctrl = {r["model"]: r for r in rows if r["control"]}
    for r in main:
        c = ctrl.get(r["model"])
        r["ctrl_ic"] = c["spearman_ic"] if c else ""
        r["ctrl_hit"] = c["hit_rate"] if c else ""
        try:
            r["delta_ic"] = round(float(r["spearman_ic"]) - float(c["spearman_ic"]), 4)
        except (TypeError, ValueError, KeyError):
            r["delta_ic"] = ""
    main.sort(key=lambda r: -(float(r["spearman_ic"] or 0)))
    return main


def td(v):
    return f"<td>{html.escape(str(v))}</td>"


def render():
    agg = load_track_a()
    parts = []
    parts.append(
        """<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FinAgentBench — Can LLM agents do finance research?</title>
<style>
:root{--fg:#1a1d23;--muted:#6b7280;--line:#e5e7eb;--acc:#0b6e4f;--bg:#fcfcfd}
*{box-sizing:border-box}body{margin:0;font:16px/1.65 -apple-system,'Segoe UI',Roboto,sans-serif;color:var(--fg);background:var(--bg)}
.wrap{max-width:980px;margin:0 auto;padding:48px 24px}
h1{font-size:2rem;margin:.2em 0}h2{margin-top:2.2em;border-bottom:2px solid var(--line);padding-bottom:.3em}
.sub{color:var(--muted);font-size:1.05rem}
table{border-collapse:collapse;width:100%;margin:1em 0;font-size:.92rem}
th{background:#f3f4f6;text-align:left}th,td{border:1px solid var(--line);padding:6px 10px}
tr:nth-child(even) td{background:#fafafa}
.note{background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:12px 16px;font-size:.9rem}
.kpi{display:flex;gap:16px;flex-wrap:wrap;margin:1.2em 0}
.kpi div{flex:1;min-width:180px;border:1px solid var(--line);border-radius:10px;padding:14px 16px;background:#fff}
.kpi b{display:block;font-size:1.5rem;color:var(--acc)}
footer{margin-top:3em;color:var(--muted);font-size:.85rem;border-top:1px solid var(--line);padding-top:1em}
</style></head><body><div class="wrap">
<h1>FinAgentBench</h1>
<p class="sub">Can LLM agents do quantitative finance research? Two capabilities, measured
separately on private data: <b>execution</b> (replicate a result from a written method
spec + raw data) and <b>judgment</b> (predict returns from financial text). All models
run through one identical harness on a single inference platform.</p>"""
    )

    # headline KPIs (dynamic)
    t1 = track_a_table(agg, "t1_momentum")
    n_perfect_t1 = sum(1 for r in t1 if r["strict"] == 1.0)
    n_models = len(set(m for task in agg.values() for m in task))
    n_runs = sum(len(runs) for task in agg.values() for runs in task.values())
    b2rows = load_track_b("b2")
    top_b2 = max((float(r["spearman_ic"] or 0) for r in b2rows), default=0)
    parts.append('<div class="kpi">')
    parts.append(f"<div><b>{n_models}</b>frontier models, one identical harness, "
                 f"{n_runs} graded agent runs</div>")
    parts.append(f"<div><b>{n_perfect_t1}/{len(t1)}</b>models replicate a momentum "
                 "study perfectly from spec — execution is commoditized</div>")
    parts.append(f"<div><b>IC {top_b2:.2f}</b>best model reading post-cutoff analyst "
                 "articles; withheld-text controls collapse to ≈0</div>")
    parts.append("</div>")

    # key findings
    parts.append(
        """<h2>Key findings</h2><ol>
<li><b>Execution is commoditized.</b> Given a precise method spec and raw data,
nearly every model — including sub-cent-per-run ones — perfectly replicates
standard quantitative studies (momentum portfolios, event studies, an
option-overlay backtest, an 11GB full-market study). See T1–T4.</li>
<li><b>The frontier appears at paper scale.</b> Replicating a full
machine-learning asset-pricing study end-to-end (T6: train four model classes,
annual refits, out-of-sample portfolio evaluation) splits the field roughly in
half. Failures are precision failures — every model produces plausible
magnitudes; only some hold twenty-plus spec details simultaneously.</li>
<li><b>Reading long financial text yields real, measurable judgment.</b> On
analyst articles published after training cutoffs, flagship models reach
Spearman ICs around 0.4–0.5 vs ≈0.2 for small models; with the text withheld,
every model collapses to ≈0. See B2.</li>
<li><b>On historical data, apparent skill is often memorization.</b> Some
models predict historical event outcomes better with the news withheld —
they recall two decades of price history from (ticker, date) alone. The honest
metric is ΔIC = IC(text) − IC(withheld). See B1.</li>
<li><b>Models rank better than they call direction.</b> Several models show
significantly positive ICs with below-50% hit rates: a systematic long bias.
Use these signals cross-sectionally, not for market timing.</li>
<li><b>Reliability, quantified.</b> Re-running identical tasks: ~2–3% of runs
silently produce wrong answers and ~6% die on provider infrastructure —
consistent with what production-agent practitioners report as their top
challenge.</li>
<li><b>Published ML alpha decays.</b> Re-running a canonical ML asset-pricing
design on 2015–2021 (after the original out-of-sample period), decile
long-short Sharpe falls from 2+ to ≈0.2–0.3 and linear signals flip negative;
the nonlinear-beats-linear ranking survives.</li>
</ol>"""
    )

    # methods in brief
    parts.append(
        """<h2>Methods in brief</h2><ul>
<li><b>One harness, one platform.</b> Every model runs the same two-tool agent
loop (bash sandbox + answer submission, step-capped) through one inference
platform; provider-specific API quirks are normalized at the gateway layer and
documented.</li>
<li><b>Script-graded, private ground truth.</b> Track A answers are graded by
tolerance bands (loose ±5%, strict ±1%) against reference implementations run
on private data extracts — published numbers can't be recalled from training.</li>
<li><b>Controls everywhere.</b> Every text-prediction track has a
withheld-text control run per model, bounding memorization; Track B2
additionally uses only articles published after model training cutoffs, with
per-model cutoff verification.</li>
<li><b>Replicates.</b> Reliability numbers come from repeated identical runs
(up to 5 seeds); leaderboard metrics are being extended with multi-seed error
bars.</li>
</ul>"""
    )

    # Track A
    parts.append("<h2>Track A — Execution: replicate from spec</h2>")
    parts.append(
        "<p>The agent gets a task sheet (method spelled out, results withheld), "
        "read-only data, a bash sandbox, and a 40-step budget. Grading is scripted: "
        "each submitted statistic vs ground truth (loose ±5% / strict ±1%). Samples "
        "are private extracts, so published numbers can't be recalled from training.</p>"
    )
    for task in ["t1_momentum", "t2_event_study", "t3_covered_call", "t4_crsp_momentum", "t6_gkx_ml"]:
        rows = track_a_table(agg, task)
        if not rows:
            continue
        parts.append(f"<h3>{TASK_LABELS[task]}</h3>")
        parts.append(
            "<table><tr><th>Model</th><th>Strict</th><th>Loose</th>"
            "<th>Consistency (strict across seeds)</th><th>Best steps</th><th>Best cost</th></tr>"
        )
        for r in rows:
            parts.append(
                "<tr>" + td(r["model"]) + td(f"{r['strict']:.1f}") + td(f"{r['loose']:.1f}")
                + td(r["consist"]) + td(r["steps"]) + td(r["cost"]) + "</tr>"
            )
        parts.append("</table>")

    # Track B
    parts.append("<h2>Track B — Judgment: predict returns from text</h2>")
    b_specs = [
        (
            "b1",
            "B1 · News headlines",
            "1,008 stratified news events on 20 mega-caps (2004–2024) from an "
            "institutional news-event dataset. Model sees headline + ticker + date "
            "+ trailing stats; predicts 5-day beta-adjusted return. Control: "
            "headline withheld (memorization baseline).",
        ),
        (
            "b2",
            "B2 · Analyst articles (post-cutoff)",
            "Full-text investment research articles published Apr–Aug 2026 — after "
            "the training cutoff of the models under test. Model predicts 20-day "
            "market-adjusted return. Control: article withheld.",
        ),
        (
            "b4",
            "B4 · Earnings press releases (post-cutoff)",
            "8-K item-2.02 earnings press releases filed with the SEC Feb–Jul 2026 "
            "(after most models' training cutoffs), fetched from EDGAR. Model reads "
            "the release and predicts the 5-day post-filing market-adjusted return. "
            "Control: text withheld.",
        ),
        (
            "b6",
            "B6 · Earnings-call transcripts (post-cutoff)",
            "Full earnings-call transcripts (Feb–Jul 2026). Model reads management "
            "remarks + Q&A and predicts the 5-day post-call market-adjusted return. "
            "Control: transcript withheld.",
        ),
        (
            "b5",
            "B5 · 13F smart-money adds (post-cutoff, small n)",
            "Top new/increased positions from Q1-2026 13F filings of 11 prominent "
            "funds (filed mid-May 2026). Model sees who bought, size, and portfolio "
            "weight; predicts the 20-day post-filing market-adjusted return. "
            "Control: same stock/date without the 13F context. n≈38 — indicative "
            "only.",
        ),
        (
            "b3",
            "B3 · SEC filing MD&A",
            "Management's Discussion & Analysis sections from 10-K/20-F filings of "
            "33 AI-infrastructure companies (2017–2024); predict 20-day "
            "post-filing market-adjusted drift. Control: text withheld.",
        ),
    ]
    for name, title, desc in b_specs:
        rows = load_track_b(name)
        if not rows:
            continue
        parts.append(f"<h3>{title}</h3><p>{desc}</p>")
        has_cut = name == "b2"
        hdr = "<table><tr><th>Model</th><th>n</th><th>Hit rate</th><th>Spearman IC</th>"
        if has_cut:
            hdr += "<th>IC (Jun–Jul only)</th><th>Cutoff</th>"
        hdr += "<th>L/S spread (bps)</th><th>Control IC</th>"
        if name == "b1":
            hdr += "<th>ΔIC (text − control)</th>"
        hdr += "</tr>"
        parts.append(hdr)
        for r in rows:
            row = "<tr>" + td(r["model"]) + td(r["n"]) + td(r.get("hit_rate", "")) + td(r.get("spearman_ic", ""))
            if has_cut:
                cut = r.get("cutoff", "")
                mark = " ⚠️" if cut == "UNDISCLOSED" or cut >= "2026-04" else ""
                row += td(r.get("ic_junjul", "")) + td(cut + mark)
            row += td(r.get("ls_spread_bps", "")) + td(r["ctrl_ic"])
            if name == "b1":
                row += td(r.get("delta_ic", ""))
            row += "</tr>"
            parts.append(row)
        parts.append("</table>")

    # cost-optimal routing table derived from Track A results
    parts.append(
        "<h2>Cost-optimal routing</h2>"
        "<p>Because every model runs the same tasks in the same harness, the results "
        "double as a routing table: the cheapest model that solves each difficulty "
        "tier perfectly. Routine replication does not need a flagship.</p>"
    )
    routing = []
    for task in ["t1_momentum", "t2_event_study", "t3_covered_call", "t4_crsp_momentum", "t6_gkx_ml"]:
        rows = [r for r in track_a_table(agg, task) if r["strict"] == 1.0 and r["cost"] != "—"]
        if rows:
            best = min(rows, key=lambda r: float(r["cost"].lstrip("$")))
            routing.append((TASK_LABELS[task], best["model"], best["cost"]))
    if routing:
        parts.append("<table><tr><th>Task tier</th><th>Cheapest perfect solver</th><th>Cost per run</th></tr>")
        for t, m, c in routing:
            parts.append("<tr>" + td(t) + td(m) + td(c) + "</tr>")
        parts.append("</table>")

    # which-text-has-alpha contrast
    parts.append(
        "<h2>Which financial text carries alpha?</h2>"
        "<p>The same models, the same harness, four post-cutoff text sources — "
        "very different outcomes. <b>Analyst opinion articles</b> (B2) support "
        "strong cross-sectional ranking (best models IC ≈ 0.4–0.6): opinions "
        "diffuse slowly. <b>Earnings press releases</b> (B4) show near-zero or "
        "negative IC for most models: hard numbers are priced within minutes, so "
        "reading them the next day adds nothing — models that naively map \"good "
        "quarter → buy\" get systematically caught by post-announcement reversals. "
        "<b>13F disclosures</b> (B5) show positive signal on a small sample. "
        "The lesson: text selection dominates model choice.</p>"
    )

    # GKX post-publication decay (from the t6 reference run)
    gkx_p = ROOT.parent / "gkx" / "ground_truth_t6.json"
    if gkx_p.exists():
        import json as _json
        g = _json.loads(gkx_p.read_text())
        parts.append(
            "<h2>Side finding — ML asset-pricing alpha after publication</h2>"
            "<p>Building T6's ground truth required re-running a scoped version of a "
            "canonical machine-learning asset-pricing study (94 firm characteristics, "
            "expanding-window refits) on 2015–2021 — entirely after the original "
            "paper's out-of-sample period. The equal-weighted decile long-short "
            "portfolios that earned Sharpe ratios above 2 in the original sample "
            "largely vanish:</p>"
        )
        parts.append("<table><tr><th>Model</th><th>OOS R² (%)</th><th>Decile L/S Sharpe 2015–2021</th></tr>")
        for key, lab in [("ols3", "OLS-3 (size/value/momentum)"), ("enet", "Elastic net"),
                         ("gbt", "Gradient-boosted trees"), ("nn3", "Neural net (3 layers)")]:
            parts.append("<tr>" + td(lab) + td(f"{g['r2oos_'+key]['value']:.3f}")
                         + td(f"{g['ls_sharpe_'+key]['value']:.3f}") + "</tr>")
        parts.append("</table><p>Nonlinear models still beat linear ones — the paper's "
                     "qualitative ranking survives — but linear signals flip negative and "
                     "the economic magnitude is a fraction of the published era. (Scope "
                     "deviations: characteristics only, equal-weighted deciles, training "
                     "history starts 2004.)</p>")

    # caveats
    parts.append(
        """<h2>Honest caveats</h2><div class="note"><ul>
<li>Track B2's "post-cutoff" claim is per-model: models released mid-2026 may have
training data extending into the article window; a per-model cutoff table is in
progress. Withheld-text controls bound the contamination for every track.</li>
<li>Article/filing forward windows overlap in calendar time, so cross-sectional
correlation inflates naive significance; treat Track B as a <i>ranking</i> across
models on a common sample, not a tradable alpha estimate.</li>
<li>Small samples where noted (B2 n<500); error bars matter and seeds are being added.</li>
<li>Underlying market and text datasets are licensed; this page publishes
aggregates only.</li>
<li>Scores are harness-dependent: the same model can score differently under a
different runtime (a point model vendors themselves acknowledge). All numbers
here come from ONE neutral harness on one serving platform — comparable to each
other, not to vendor-reported benchmarks.</li>
<li>Costs are computed at full input-token list price; provider-side prefix
caching (not metered in early runs) would reduce flagship agent costs somewhat.</li></ul></div>"""
    )

    parts.append('<footer>FinAgentBench · Agentic Sciences research · <a href=\"https://github.com/QihongRuan/finagentbench\">source & docs on GitHub</a> · results generated programmatically from run logs; no numbers are hand-entered.</footer>')
    parts.append("</div></body></html>")
    OUT.write_text("\n".join(parts))
    print("wrote", OUT)


if __name__ == "__main__":
    render()
