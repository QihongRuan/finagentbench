# FinAgentBench

Can LLM agents do quantitative finance research? A two-track benchmark run on
13 frontier models through one identical harness:

- **Track A — Execution**: replicate quantitative results (momentum, event
  studies, an option-overlay backtest) from a written method spec + raw private
  data, graded programmatically against ground truth.
- **Track B — Judgment**: predict forward returns from financial text (news
  headlines, full analyst articles published after model training cutoffs, and
  SEC filing MD&A sections), with withheld-text controls to bound memorization.

Live results: https://qihongruan.github.io/finagentbench/

All tables are generated programmatically from run logs. Underlying market and
text datasets are licensed; this repo publishes aggregates only.
