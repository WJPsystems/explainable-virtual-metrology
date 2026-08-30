# Changelog

Tracks what changed in each delivered version of this repo. Individual files
inside the repo are not renamed/suffixed per version -- Git's own commit
history is the source of truth for file-level changes. This changelog and
each notebook's "Notebook version" marker (in its first cell) exist so you
can tell, at a glance, whether the copy you're looking at in Colab/GitHub is
current, without needing to diff files by hand.

## v33 -- 2026-08-30

- **Diagnosed a real environment failure from actual user-reported stderr**:
  `00_run_all.ipynb` reported all six notebooks failing at kernel startup,
  before any of their own cells ran. Root cause, confirmed from the
  traceback: a Colab base image shipping Python 3.13 (every prior
  successful run in this project's history shows Python 3.12) has
  `google.colab`'s own `_shell_customizations.py` crash on import
  (`AttributeError: type object 'TermColors' has no attribute 'Green'`)
  due to an internal mismatch between the pre-installed `google-colab`
  package and whatever IPython version ships in that same image -- a
  genuine Colab-platform bug, external to this repo, its notebooks, or any
  of this project's own code.
- **Ruled out, not just assumed, that this project's own v31 change
  contributed**: v31 added an explicit `ipython>=8.0` line to
  `requirements.txt`. Reasoned through whether this could have forced an
  upgrade past whatever version Colab's image already had pre-installed --
  concluded unlikely, since `>=8.0` is a loose lower bound almost any
  current Colab environment already satisfies without triggering a
  version change. Removed the explicit pin anyway as a zero-cost
  precaution, since `ipython` remains available transitively via the
  existing `jupyter>=1.0` dependency regardless.
- **Added a best-effort mitigation, not a guaranteed fix, to
  `00_run_all.ipynb`'s setup cell**: attempts `pip install --upgrade
  google-colab` in the main, already-running Colab kernel before it
  spawns the subprocess kernels that actually crash for `01`-`06` --
  correctly scoped to the only place this could plausibly help, since the
  actual failure happens at subprocess-kernel startup, before even that
  notebook's own first cell (including its own Colab setup cell) would
  run. If Google has already patched `google-colab` to match a newer
  IPython, this picks the fix up automatically; if not, this is a no-op
  and the original failure will look the same as before. Explicitly
  disclosed as a mitigation for an external platform issue, not something
  this repo can guarantee resolves it.
- Also added a plain `print(f"Python: {sys.version}")` to the same setup
  cell, so a Python-version mismatch like this one is visible immediately
  in the setup output on any future run, rather than requiring a full
  traceback dig to notice.
- **Fixed a real bug in my own first attempt at this fix**: initially
  wrote the `google-colab` upgrade using a `try: !pip install ...` block,
  which is invalid pure Python syntax once IPython's `!`-magic line is the
  only statement inside the `try` body -- caught by this project's own
  syntax-validation step before shipping, not discovered later. Replaced
  with `subprocess.run()`, matching the pattern already used elsewhere in
  this same cell for the `git log` commit-hash check, which also gives an
  actual return code to test rather than relying on magic-command error
  suppression.

## v32 -- 2026-08-30

- **Resolved the RQ4 run-to-run reproducibility gap identified from v30's
  real-data run**: `shap.sample()`'s background selection was already
  seeded (`random_state=42`), but `KernelExplainer.shap_values()`'s own
  Monte Carlo coalition sampling was not -- it draws from numpy's global
  random state, which is why RQ4's exact numbers drifted across four
  separate real runs even though the qualitative conclusion held every
  time. Fixed by calling `np.random.seed(42)` immediately before each of
  the two `shap_values()` calls in `05_attention_comparison_rq4.ipynb`
  (TabNet's and the MLP's), re-seeding before the second call specifically
  since the first call's own random draws would otherwise have already
  consumed and advanced the seeded state.
- **Verified the fix genuinely produces bit-identical results**, not just
  assumed to: first isolated the mechanism on a minimal synthetic case
  (confirmed unseeded calls differ, seeded calls match exactly), then ran
  a full integration test mimicking the real notebook cell's exact
  structure end-to-end twice (background sampling, explainer construction,
  seeded `shap_values()` call) -- confirmed max absolute difference of
  0.0 between the two runs.
- This closes the gap between this project's stated reproducibility claims
  (Materials and Method: "version-controlled and publicly reproducible via
  GitHub") and RQ4's actual behavior, which previously contradicted that
  claim in practice.
- Not yet run against real SECOM data -- the next real run should now
  produce RQ4 numbers that exactly match any subsequent re-run, which
  itself is a testable claim worth confirming once real output is back.

## v31 -- 2026-08-30

- **Real bug found from the v30 run's real output, not caught before
  shipping**: all 10 charts saved correctly to `data/artifacts/figures/`
  (confirmed -- the real PNGs were reviewed and are correct), but none of
  them appeared inline in any notebook's own output cells or HTML export.
  Root cause: `save_figure()` called `plt.close(fig)` immediately after
  saving, which destroyed the figure before Jupyter's normal end-of-cell
  auto-display mechanism ever got a chance to render it. The save
  succeeded; the display never had a chance to happen.
- **Fixed** by calling `IPython.display.display(fig)` explicitly right
  before closing, in `src/plotting.py`'s `save_figure()` -- deliberately
  using `display(fig)` rather than `plt.show()`, since `plt.show()` renders
  matplotlib's globally-tracked "current figure," which is fragile in
  cells that create more than one figure (as `02` and `04` both do);
  `display(fig)` renders the specific figure object passed in, regardless
  of what else has been created in the same cell.
- Verified the fix with a synthetic multi-figure-per-cell test (mimicking
  `02`/`04`'s actual pattern of 2-3 charts in one cell) before shipping:
  confirmed each figure displays and closes correctly and independently,
  with no cross-contamination between figures created in sequence.
- Added `ipython` as an explicit direct dependency in `requirements.txt`
  (previously only available transitively via `jupyter`), matching this
  project's standing practice of declaring direct dependencies explicitly
  rather than relying on transitive installs.
- **Still open from v30's real-data findings, not yet resolved**: RQ4's
  exact reported numbers drift between runs (`shap.sample()`'s background
  selection is seeded, but the actual `explainer.shap_values(...)`
  Monte Carlo coalition sampling is not) -- confirmed across four separate
  real runs, with the qualitative conclusion stable each time but the
  precise figures shifting. Awaiting a decision on whether to seed this
  step for genuine reproducibility (recommended) before finalizing which
  run's numbers go into the Final Report.

## v30 -- 2026-08-30

- **Added the "Visual Evidence" charts for the Final Report** (10 total,
  the item that had been explicitly deferred/pinned in prior planning):
  - `01`: class distribution bar chart (pass vs. fail)
  - `02`: ROC curves and Precision-Recall curves, all 4 RQ1 models overlaid
  - `03`: SHAP top-10 bar chart; a rank-based SHAP-vs-permutation-importance
    comparison chart (redesigned after an initial binary-flag version
    tested visually flat -- rank-based bar length conveys both membership
    and relative importance)
  - `04`: confusion matrices (reduced model, default vs. tuned threshold);
    predicted-probability histogram with both thresholds marked; full-vs-
    reduced grouped bar chart across 5 metrics
  - `05`: RQ4 raw-vs-magnitude-only grouped bar chart; RQ4 per-instance
    paired scatter (TabNet vs. MLP correlation with SHAP, 40 wafers)
- **New `src/plotting.py`**: a fixed model-to-color mapping (Random Forest,
  XGBoost, Logistic Regression, TabNet, MLP) applied identically across
  every chart that compares these models, plus a shared `save_figure()`
  helper writing consistently to the new `data/artifacts/figures/` folder.
  Optimized for the Word/PDF report specifically; a presentation-specific
  (PPT) restyling pass is explicitly deferred, not assumed compatible.
- **All 10 charts verified against synthetic data before touching any real
  notebook**, including deliberate edge cases drawn from this project's
  own real findings: a fully degenerate zero-recall confusion matrix (the
  exact RF-at-0.5 pattern from RQ1/RQ3) renders correctly with legible
  zero-cells; a negative-value bar (RQ4's raw TabNet correlation) renders
  correctly below the zero line; a degenerate all-identical-score PR curve
  does not crash.
- **Fixed a real gap in `00_run_all.ipynb`'s existing data/artifacts
  download cell**: it used `os.listdir()` (single-level) on each `data/`
  subfolder, which would have silently skipped every new figure in the
  nested `data/artifacts/figures/` folder without any error. Changed to
  `os.walk()` (recursive), verified against a synthetic nested-folder test
  before shipping -- confirmed the fixed version correctly includes nested
  files while still excluding `PLACEHOLDER.md`.
- Not yet run against real SECOM data -- all 10 charts are implemented and
  synthetic-verified, but the real chart images still need a fresh run to
  generate before they can be embedded in the Final Report.

## v29 -- 2026-08-30

- **Real methodological question found via critical re-examination of v28's
  confirmed RQ4 result, not a bug**: TabNet's `.explain()` output is a
  sparsemax-derived attention mask, typically non-negative (magnitude of
  feature use only, no direction), while SHAP and Integrated Gradients are
  SIGNED (direction and magnitude of contribution). Correlating a
  non-negative array against a signed array partly tests a representational
  mismatch, not purely whether the importance ranking agrees -- confirmed
  on synthetic data that this mismatch alone can make a genuinely-agreeing
  pair of signals look like they disagree (raw correlation of -0.06 when
  the true magnitude-only agreement was 0.82).
- **Added a diagnostic check** (Step 2) printing TabNet's and the MLP's
  explanation value ranges, to confirm directly (not assume) whether
  TabNet's output is genuinely non-negative in this specific pipeline.
- **Added a new Step 5 supplementary analysis**: re-runs the RQ4 agreement
  comparison using absolute values on both sides (magnitude-only,
  sign-agnostic), with its own paired significance test, to determine
  whether Step 4's conclusion is robust to this representational concern
  or was substantially an artifact of it. The notebook now prints an
  explicit interpretation of which case applies, rather than requiring
  manual comparison of the two results.
- Verified the underlying logic on synthetic data before shipping,
  including a realistic scenario mimicking the actual RQ4 setup (TabNet
  genuinely disagreeing with SHAP, MLP genuinely agreeing) to confirm the
  new Step 5 cell correctly computes and reports the magnitude-only
  comparison.
- Not yet run against real SECOM data -- whether v28's RQ4 conclusion
  survives this check, or needs qualifying, is still an open, real
  question pending this run.

## v28 -- 2026-08-29

- **Implemented RQ4's formal significance test**, a real analytical gap
  identified while planning the Final Report: RQ4's own stated hypotheses
  (H0/Ha) require testing whether TabNet's attention-vs-SHAP agreement
  differs significantly from the MLP control's Integrated-Gradients-vs-SHAP
  agreement -- previously only the two mean correlations (-0.1681 vs.
  0.8479) were reported side by side, with no formal test backing the
  "TabNet's attention isn't trustworthy" conclusion.
- **New `paired_agreement_significance_test()`** in `src/explainability.py`:
  a paired t-test (primary) plus a Wilcoxon signed-rank test (robustness
  check, since per-instance correlations are bounded to [-1, 1] and often
  skewed, which can violate the t-test's normality assumption) -- matching
  this project's established pattern of pairing a parametric primary test
  with a non-parametric cross-check (as in RQ3's bootstrap AUC + McNemar's).
  Uses a PAIRED test specifically, not independent-samples, since both
  correlation arrays are computed on the same wafers.
- **Real edge case found and fixed during testing, not after shipping**:
  scipy's `ttest_rel` returns `NaN` when two input arrays are identical
  (zero-variance differences cause 0/0 internally) -- caught by explicitly
  testing this function against identical-array inputs before wiring it
  into the notebook, not assumed safe. Fixed by explicitly guarding the
  zero-variance case for both tests, returning a semantically correct
  p=1.0 ("no difference") instead of `NaN`.
- Verified with 4 tests before shipping (large real-magnitude gap ->
  significant on both tests; identical arrays -> p=1.0, no NaN; tiny
  noise-level difference -> not significant at alpha=.05; shape mismatch
  -> raises clearly) plus a full integration test simulating the actual
  `05_attention_comparison_rq4.ipynb` data flow end-to-end.
- **`05_attention_comparison_rq4.ipynb` updated**: Step 4's RQ4-answer cell
  now runs the formal test and states an explicit "reject/fail to reject
  H0(4) at alpha=0.05" conclusion, rather than an eyeballed mean comparison.
  Not yet run against real SECOM data -- that confirmation is still
  outstanding.

## v27 -- 2026-08-23

- **Added an APA-style Table of Contents to both `docs/synopsis.docx` and
  `QM640_Interim_Report.docx`** (the latter delivered as a standalone file,
  not added to the repo). Built as a manually-typed TOC with dot leaders,
  not a native docx-js/Word TOC field -- verified directly that a native
  field renders BLANK under LibreOffice headless conversion (only
  populates after a manual "update fields" action in an interactive Word
  session), which was judged too fragile for a graded submission a student
  might not remember to refresh before printing/submitting.
- **Every TOC entry's page number was independently verified against the
  actual rendered PDF** (not assumed from source order) -- extracted real
  page numbers via `pdftotext`, cross-checked all 33 (Interim Report) and
  23 (Synopsis) entries programmatically against the final build, 0
  mismatches in both documents.
- Real bug caught and fixed during this work: a content paragraph
  intended for the Literature Survey landed structurally *after* its
  array's closing bracket during a text-insertion edit -- it loaded
  without a JavaScript error (since a bare expression statement is valid
  syntax) but never actually rendered, since it was never part of the
  exported array. Caught by explicitly checking array membership after
  each edit, not just that the module still loaded -- now standard
  practice for any future docx-js content edits in this project.
- Interim Report's body content was expanded across several turns to
  approach the target page range (Literature Survey, Analysis, Modelling,
  and Preliminary Results sections each received additional real
  analytical paragraphs, not filler) before settling at ~14-15 pages of
  counted body text against a 15-20 page target, at the user's explicit
  decision to accept this as sufficient rather than continue expanding
  toward the upper end of the range.

## v26 -- 2026-08-23

- **Synopsis updated to address evaluator feedback on the graded submission**,
  no notebook/src code changes this version:
  - Added null and alternate hypotheses (H0/Ha) under each of the four RQs
    in Scope and Objectives.
  - Sample Size Calculation section rewritten to explain *why* each
    parameter value was chosen (EPV=10, power=.80, alpha=.05, effect
    sizes) rather than stating them as a bare formulaic application.
  - Added a direct paragraph addressing whether the real missingness/
    variance screening results (32 dropped for missingness, 126 for
    near-zero variance, 432 remaining) threaten sample-size adequacy --
    clarifies the binding EPV constraint depends on event count and final
    predictor count (k), not raw feature count before screening.
  - Analytic Approach section now opens with a tabulated summary (RQ |
    Technique | Reasoning | Hypothesis Tested) before the existing
    per-RQ prose, addressing feedback to tabulate solutions with reasoning.
  - Evaluation Metrics section converted from a bullet list of formulae
    into a full table with a business-language interpretation column,
    addressing feedback that metrics should be legible to a non-technical
    engineering audience.
- **New deliverable: `QM640_Interim_Report.docx`**, built from scratch
  following the QM640 Interim Report template exactly (not derived by
  editing the synopsis) -- title page, GitHub link, Introduction, Interim
  Project Status, Scope/Objectives with hypotheses, Literature Survey (13
  sources, relevance matrix), Data Description, Analysis (data cleaning
  log, EDA with real insights, sample-size justification), Modelling
  (model justification, real feature table, business-language metrics),
  Preliminary Results (all 4 RQs + robustness check, real numbers
  throughout, cross-RQ synthesis), Limitations, Next Steps, Bibliography
  (22 references), Appendix A (code). Kept as a standalone document, not
  added to the repo's `docs/` folder automatically -- delivered separately
  pending the user's own placement decision.
- **Real bug caught and fixed during construction**: the Appendix A code
  block initially rendered as one unreadable line -- embedded `\n`
  characters inside a single docx-js `TextRun` are silently ignored, not
  rendered as line breaks (a documented docx-js gotcha this build violated
  on the first pass). Fixed using `TextRun`'s `break` property between
  lines instead, verified by re-rendering to PDF and visually confirming
  proper indentation and line breaks.

## v25 -- 2026-08-02

- **v24's SMOTE robustness check confirmed run against real SECOM data.**
  Verified directly from GitHub's hosted HTML exports (not just a chat
  upload) after an initial mismatch turned out to be a stale local file,
  not a repo problem -- see resolution below. Real result: SMOTE barely
  moves the needle over class weighting (recall 0.0 -> 0.0096, BER 0.500 ->
  0.496, AUC-ROC 0.7123 -> 0.7208) -- a genuine null result, not a bug,
  suggesting the threshold-collapse problem is not specific to class
  weighting and that SMOTE's nearest-neighbor interpolation likely suffers
  from the curse of dimensionality at 432 features.
- **Resolved an apparent version mismatch**: a chat-uploaded HTML export
  showed a stale v20 marker with no SMOTE code, while the user had
  confirmed v24 on GitHub. Cloned the actual repo directly (including the
  new `docs/all_notebook_exports/` folder) and confirmed all six notebooks
  there are genuinely v24 with the real SMOTE implementation present and
  executed -- the uploaded file was stale (a local, unsynced copy), not a
  repo issue. Correcting this in the record since I initially and
  incorrectly told the user their run was stale when it was the chat
  upload that was.
- **Fixed a real gap in `01_data_screening.ipynb`**: the synopsis's
  screenshot placeholder specifically asked for `X.info()`/`X.head()`
  output, but the notebook never actually called either -- only
  `X.shape`/`y.value_counts()`. Added two new cells (`X.info()`, `X.head()`)
  immediately after the data-load cell so the promised screenshot content
  genuinely exists.
- **Synopsis updated**: SMOTE robustness check results added to the RQ1
  Results section (Table 3b); Figure 1's folder tree refreshed to show the
  actual real files now present in `data/raw/`, `data/model_ready/`,
  `data/artifacts/`, and the new `docs/all_notebook_exports/` folder; Open
  Access paragraph updated to confirm real data/artifacts are now present
  (fulfilling the v18 note that promised this update once true); screenshot
  placeholder text updated to point at the exact new cells.

## v24 -- 2026-08-02

- **Real bug from v23's first run: `NameError: name 'best_tree' is not
  defined`** in the new SMOTE cell. Root cause: `best_tree` is actually
  defined inside the later "Save results for downstream notebooks" cell,
  but the SMOTE cell (which needs it) was placed *before* that cell in
  notebook order -- an ordering mistake introduced when the SMOTE cell was
  added, not caught before shipping because it was only tested with
  `best_tree` pre-defined in the test scaffolding rather than mimicking the
  real notebook's cell order exactly.
- **Fixed by computing `best_tree` locally within the SMOTE cell** from
  `results_df` (which genuinely is available at that point), rather than
  reordering cells or depending on a later cell's definition -- makes the
  SMOTE check self-contained regardless of what runs around it. Verified by
  re-running the exact failure scenario (`results_df` defined, `best_tree`
  deliberately NOT pre-defined) and confirming no `NameError` this time.

## v23 -- 2026-08-02

- **Real gap found via audit, not a new-run failure**: `imbalanced-learn`
  sat in `requirements.txt` completely unused -- traced back to the
  synopsis's own RQ1 methodology and `02`'s own markdown both claiming a
  SMOTE robustness check "runs below," when no such code ever existed.
  Full cross-check of every third-party import across all notebooks and
  `src/*.py` against `requirements.txt` confirmed this was the only real
  gap; everything else validated correctly.
- **Implemented a scoped SMOTE robustness check** in `02_modeling_rq1.ipynb`,
  applied to the single best-performing tree model only (not all four
  models, to avoid doubling an already-long CV pass), resampling only each
  fold's training split (never the held-out fold, to avoid leakage).
  Verified the full flow end-to-end on synthetic SECOM-shaped data,
  including confirming `best_tree` resolves dynamically to whichever model
  actually wins (tested with a case where that's XGBoost, not just the
  real run's RandomForest) before wiring it into the real notebook.
- **Synopsis's RQ1 methodology text corrected** to accurately describe the
  scoped (single-model) SMOTE check, rather than implying it ran across
  all four models -- the previous wording was the actual source of the gap.
- Not yet run against real SECOM data -- the actual numeric result (does
  SMOTE fix the threshold-collapse problem class-weighting alone left
  unresolved?) is still outstanding.

## v22 -- 2026-08-02

- **Synopsis updated with the Isolation Forest robustness check's real
  results**: flagged 17/314 (5.4%) held-out wafers as anomalous; caught 0
  of the 7 real failures the supervised model missed at its tuned
  threshold. Reported as an honest null result (with the caveat that 7
  missed cases gives very little statistical power either way), not
  omitted or spun. Preliminary Results section now covers RQ1-RQ4 plus this
  robustness check -- everything with real code has real results reported.
- **README documents two workflow realities that were previously only
  explained in chat**: (1) `PLACEHOLDER.md` files should be deleted once
  real data is uploaded to a folder, rather than left alongside it; (2)
  nothing in this pipeline (Colab, or the tools used to edit this repo)
  has write access to push to GitHub -- HTML exports and synopsis updates
  require manual download/upload, same as code changes. Documented
  `00_run_all.ipynb`'s existing "download all HTML as zip" cell as the
  path to getting run exports out of Colab if they're wanted in the repo.

## v21 -- 2026-08-02

- **First fully clean, real-data run across all six notebooks confirmed**
  (v20's two fixes -- `data/model_ready/` population and the MLP scaling
  fix -- both verified working on actual SECOM data, not just synthetic
  tests). No notebook code changed in this version; only `docs/synopsis.docx`.
- **Synopsis updated with real RQ4 results**: TabNet's own attention
  explanation is negatively correlated with SHAP (mean Spearman -0.1681,
  top-3 agreement 10%), while the MLP control's Integrated Gradients
  agrees strongly with SHAP (0.8479, top-3 agreement 35%) -- a clear,
  reportable answer to "Is TabNet's Attention Actually Trustworthy?" (no).
  Documented that an earlier run's MLP results were discarded (diverged/
  non-learning network, fixed in v19-v20) rather than folded into this
  number.
- Preliminary Results section now covers RQ1-RQ4 with real data; the
  Isolation Forest robustness check's results (from `06_anomaly_safety_net.ipynb`)
  still to be added -- it's an exploratory check per the synopsis's
  "Robustness Consideration" section, not a numbered RQ.

## v20 -- 2026-08-02

- **Real bug found: `data/model_ready/` was never populated by a v18 run**
  (only `raw/` and `artifacts/` appeared in the downloaded zip). Root
  cause: `run_screening_pipeline()` -- the only code that writes to
  `data/model_ready/` -- was only reachable via
  `if __name__ == "__main__":`, i.e. running `python src/preprocessing.py`
  directly, which nothing in this notebook-based pipeline ever does. This
  was architecturally orphaned from the start, not a "hasn't run yet" gap.
- **Fixed by calling `run_screening_pipeline()` explicitly in
  `01_data_screening.ipynb`.** Confirmed this doesn't introduce a second,
  inconsistent train/test split: `stratified_split()` uses the identical
  parameters (`test_size=0.2, random_state=42, stratify=y`) as RQ1's
  index-based holdout split used everywhere else in the pipeline -- this
  materializes that same split as CSV files for direct inspection, it
  doesn't compete with it.
- Verified the underlying screen/split/write logic directly (synthetic
  data, temp directory) before wiring it in.
- `00_run_all.ipynb`'s existing data-download cell already iterates over
  all three `data/` subfolders, so no changes needed there -- it will pick
  up the newly-populated `model_ready/` files automatically on the next run.

## v19 -- 2026-07-29

- **Real bug found from `05`'s first run against actual SECOM data**: the
  MLP control's training loss exploded from 2.22 to 174.23 and then stayed
  *exactly* flat for 100+ epochs -- a saturated/dead network, not a trained
  model. This silently produced garbage explanations: MLP's SHAP-vs-
  Integrated-Gradients agreement came back as exactly 0.0000, and a
  `ConstantInputWarning` confirmed the model's output barely varied with
  input at all. This invalidated the RQ4 conclusion drawn from that run,
  since the "control" the comparison depends on was broken.
- **Root cause, confirmed by direct reproduction**: the MLP was trained on
  raw, unscaled SECOM features (which span wildly different numeric
  ranges -- the same issue that broke LASSO earlier in this project).
  TabNet handles this internally; a hand-built PyTorch MLP does not.
  Reproduced the exact failure pattern (loss explodes and flatlines
  immediately) with synthetic SECOM-scale features, then confirmed the fix
  resolves it on the same adversarial data (MLP reaches 95.6% train
  accuracy with smoothly decreasing loss instead).
- **Fix, three parts**: (1) `StandardScaler` fit on the training split,
  applied to both train and test -- not fit separately on test, which
  would leak test statistics into the transform; (2) switched from
  `Sigmoid()` + `BCELoss` to raw logits + `BCEWithLogitsLoss` (more
  numerically stable) and lowered the learning rate from 0.01 to 0.001;
  (3) added gradient clipping as a safety net against future divergence,
  plus an explicit train-accuracy diagnostic with a printed warning if it's
  at or below chance, so this exact failure mode is caught immediately in
  future runs instead of requiring someone to notice a suspiciously flat
  loss log.
- **Downstream cells updated for consistency**: Integrated Gradients and
  the MLP's SHAP explainer now both operate on the same scaled inputs the
  MLP was actually trained on (using the same fitted scaler, not a fresh
  one per set), and both are wrapped with an explicit `torch.sigmoid()`
  now that the model outputs raw logits -- keeping IG and SHAP on the same
  probability scale for a fair comparison.

## v18 -- 2026-07-29

- **Synopsis updated with the real repo link**
  (https://github.com/WJPsystems/secom-explainable-vm/tree/main), replacing
  the "link to be added" placeholder in the Open Access paragraph.
- **Figure 1's folder tree was stale** (still showed `.gitkeep` instead of
  `PLACEHOLDER.md`, missing `data/artifacts/`, `00_run_all.ipynb`,
  `artifacts.py`, `CHANGELOG.md`) -- refreshed to match the actual current
  repository structure.
- **Open Access paragraph rewritten to be honest about current state**:
  previously claimed "the cleaned dataset... are published," which wasn't
  accurate -- `data/raw/`, `data/model_ready/`, and `data/artifacts/`
  contain placeholder files, not the actual generated data, since Colab
  sessions are ephemeral and nothing syncs back to GitHub automatically.
  Now states this explicitly rather than overclaiming reproducibility that
  doesn't exist yet.
- **Added a real fix, not just a disclosure**: `00_run_all.ipynb` now has a
  final step that zips up everything actually generated in `data/raw/`,
  `data/model_ready/`, and `data/artifacts/` (excluding the placeholder
  files themselves) and triggers a download, so the real data/artifacts can
  be uploaded to GitHub after a run -- tested the filtering logic directly
  (real files included, placeholders correctly excluded) before shipping.

## v17 -- 2026-07-29

- **`04` now persists its own results** (`rq3_summary.json`: `final_features`,
  `watch_list`, `tuned_threshold`, LASSO Jaccard overlap) -- a real gap found
  while building `05`/`06`: `04` previously saved nothing at all, so neither
  downstream notebook could have loaded RQ3's actual reduced feature set or
  tuned threshold even if their own code were otherwise correct.
- **`05_attention_comparison_rq4.ipynb` built out with real code**: trains
  TabNet and a class-weighted PyTorch MLP control on RQ3's actual reduced
  feature set, extracts TabNet's native `.explain()` attention output and
  the MLP's Integrated Gradients attributions (captum), computes SHAP via
  `KernelExplainer` for both (neither is a tree model, so `TreeExplainer`
  doesn't apply), and reports per-instance Spearman agreement + top-3
  feature-set agreement between each model's SHAP values and its own
  intrinsic explanation -- RQ4's actual question, answered with real
  computed numbers instead of a stub.
- **`06_anomaly_safety_net.ipynb` built out with real code**: fits an
  Isolation Forest on the full 432-feature set (train portion of the
  holdout split), scores the held-out test portion, and compares against
  RQ3's actual reduced model at its actual tuned threshold -- reporting
  concretely how many real failures the supervised model missed and how
  many of those the unsupervised safety net still caught.
- **New `per_instance_agreement()`** in `src/explainability.py`, verified
  against known-answer cases (identical rankings -> correlation ~1.0 and
  100% top-k agreement; independent random rankings -> correlation ~0)
  before use.
- Verified the full artifact chain end-to-end twice: `02`-save ->
  `04`-load/save -> `06`-load (Isolation Forest comparison), and
  `02`-save -> `04`-load/save -> `05`-load (TabNet/MLP/SHAP/IG comparison)
  -- both using the actual `src/` modules with synthetic data, not mocks.
  **Neither `05` nor `06` has been run against the real SECOM dataset yet**
  -- that confirmation is still outstanding (see README Status).
- **Synopsis (`docs/synopsis.docx`) updated with a new "Preliminary
  Results" section**, reporting real RQ1/RQ2/RQ3 findings (model comparison
  table, SHAP vs. permutation importance top-10 with real values and their
  2/10 overlap, feature stability table, and the full-vs-reduced comparison
  at both the default and tuned thresholds) in place of the
  planned-methodology framing alone.
- README status checklist updated to reflect what's actually confirmed on
  real data (`01`-`04`) versus what's code-complete but synthetic-tested
  only (`05`/`06`) -- deliberately not marked complete until run for real,
  per the same "verify before claiming done" discipline used throughout
  this project.

## v16 -- 2026-07-29

- **Threshold calibration implemented** (Step 5 in `04_feature_reduction_rq3.ipynb`),
  addressing the confirmed finding that both full and reduced models predict
  "pass" for every held-out wafer at the default 0.5 threshold (identical
  accuracy, Cohen's h = 0, McNemar's degenerate) despite real discriminative
  power (AUC-ROC 0.77/0.80).
- **Fixed a real gap in an externally-proposed implementation plan before
  building on it**: the plan assumed `02`'s in-memory `oof_probs` variable
  would be accessible from `04` ("assuming they're saved as an artifact...
  let's assume it's saved") -- verified this was false. Each notebook runs
  as a fully separate kernel process (even within a single `00_run_all`
  run via `nbconvert --execute`), so nothing in `02`'s memory is visible to
  `04` regardless of execution mode. Fixed by having `02` explicitly persist
  the best tree model's out-of-fold probabilities as a new artifact
  (`rq1_oof_probs.json`), which `04` now loads.
- **Added `find_f1_optimal_threshold()`** to `src/metrics.py`, sweeping
  `precision_recall_curve`'s output for the F1-maximizing threshold. Guards
  a real (confirmed, not hypothetical) sklearn edge case: the last
  precision/recall pair has no corresponding threshold, and naively
  indexing `thresholds[argmax(f1_scores)]` over the full-length arrays can
  raise `IndexError` if that threshold-less point happens to be the F1
  maximum -- verified this is a real risk, not just theoretical, before
  adding the guard (slicing to the threshold-having range before argmax).
- The SAME tuned threshold is applied to both the full and reduced models
  in `04`, deliberately, so the full-vs-reduced comparison isn't confounded
  with separately tuning a threshold per model.
- Verified with: a targeted test on SECOM-like synthetic imbalance data
  (recall jumping from 17% to 48% at the tuned vs. default threshold, AUC-
  ROC unchanged), and a full `02`-save -> `04`-load integration test that
  reproduces the exact real-world pattern (precision/recall/F1=0, BER=0.5
  at 0.5 threshold; sensible numbers at the tuned threshold).
- Documented the cost-sensitive threshold (`cost_FP / (cost_FP + cost_FN)`)
  as the more defensible alternative if the fab can state a real cost
  ratio, in the new step's markdown explanation -- not computed here since
  no cost ratio has been specified, but flagged as the better answer if one
  becomes available.

## v15 -- 2026-07-29

- **Real bug found from a fully clean v14 run (all 6 notebooks completed):
  `04`'s full-vs-reduced accuracy comparison came back exactly 0.0000 for
  both models**, with McNemar's test showing "degenerate, no discordant
  pairs." The impossible-looking exact zero (not ~93%, the majority-class
  baseline one would expect) was the tell.
- **Root cause: `load_raw()` returned SECOM's raw `{-1, 1}` label encoding.**
  Only `02_modeling_rq1.ipynb` remapped this locally to `{0, 1}` before
  training; `03` and `04` called `load_raw()` directly and never remapped,
  so their `y` stayed in `{-1, 1}` while the saved models (trained in `02`
  on 0/1 labels) predict in `{0, 1}`. Any direct equality comparison
  between the two (accuracy, McNemar's) silently breaks -- confirmed by
  reproducing the exact 0.0000 result with synthetic data using the same
  mismatched encoding.
- **AUC-ROC-based results are confirmed NOT affected** -- verified directly
  that `sklearn.metrics.roc_auc_score` treats the larger label value as
  positive regardless of whether it's `{-1,1}` or `{0,1}` encoded, so RQ1's
  model comparison, `03`'s permutation importance, and `04`'s AUC-ROC
  comparison (0.7670 full / 0.8003 reduced) all remain valid as reported.
- **Fixed centrally in `load_raw()`** (`src/preprocessing.py`) rather than
  patching each notebook separately -- that per-notebook inconsistency
  (`02` remembered to remap, `03`/`04` didn't) is what caused the bug, so
  centralizing it prevents the same class of bug from recurring in `05`/
  `06` once those are built out. `02`'s existing local remap line is now
  redundant but confirmed harmless (idempotent on already-0/1 labels).
- Verified end-to-end with a realistic reproduction: fit/predict/compare
  using the corrected encoding produces a sensible ~95% accuracy on
  synthetic data, versus the broken 0.0000 with mismatched encoding.

## v14 -- 2026-07-29

- **v13's fix resolved the NaN crash but exposed a second, distinct
  numerical bug: `ValueError: Linkage 'Z' contains negative distances`**,
  raised by `fcluster()` on a real v13 run. Investigated rather than
  assumed: stress-tested whether `pandas.corr()` itself can exceed 1.0
  (2,000 trials with perfectly-correlated synthetic columns -- never
  observed), so the likely source is average-linkage's own recursive
  merge-height computation producing a tiny negative value from floating-
  point rounding, not necessarily the input distances. Confirmed this by
  deliberately constructing a `Z` matrix with a `-1e-15` merge height and
  reproducing scipy's exact error message, then confirming a fix resolves it.
- **Fixed with two additional defense layers** (five total now):
  `distance = np.clip(distance, 0, None)` before `linkage()` (guards the
  input side, addresses the originally-proposed fix), and
  `Z[:, 2] = np.clip(Z[:, 2], 0, None)` after `linkage()`, before
  `fcluster()` (guards linkage's own output -- this is the layer that
  actually matters for this specific failure, confirmed by the
  deliberately-constructed reproduction above).
- Re-ran the full test suite from v12/v13 (constant-column dropping,
  normal clustering correctness, multiple constant columns, no column/
  cluster-id misalignment) plus a new large-scale test (200 features, 25
  underlying correlated factor groups, near-duplicate columns) confirming
  25 clusters form correctly -- and re-ran the full
  `nested_cv_shap_selection()` reproduction. All pass.

## v13 -- 2026-07-29

- **v12's fix for the `cluster_correlated_features()` NaN crash was
  insufficient -- confirmed on a genuine v12 run, not a stale-session
  issue.** Replaced with a three-layer fix: (1) drop fold-locally-constant
  columns entirely before computing correlations (more principled than
  patching their correlation value, since such a column has no correlated
  signal to cluster in that fold), (2) keep `fillna(0)` + forced diagonal
  as a safety net for near-constant edge cases, (3) a defensive
  `np.isfinite` check immediately before `linkage()` as a last-resort net.
- **Found and fixed a second, silent bug while combining these fixes**:
  the return statement zipped cluster IDs with the original `X.columns`
  instead of `X_varying.columns` (the list actually clustered, after
  dropping constants) -- with a constant column anywhere but the end of
  the list, this would have silently misaligned column names to the wrong
  cluster IDs with no crash and no warning. Caught by a dedicated test
  (dropping a column mid-list, then asserting two genuinely-correlated
  features still land in the same cluster) rather than by inspection.
- Verified with 4 tests before shipping: original crash reproduction (now
  correctly drops rather than patches), normal clustering unaffected,
  multiple simultaneous constant columns, and the column-misalignment
  check specifically. Also re-ran the full `nested_cv_shap_selection()`
  reproduction from v12 to confirm no regression.

## v12 -- 2026-07-29

- **Real bug from a clean v11 run: `04` crashed with `ValueError: The
  condensed distance matrix must contain only finite values`** inside
  `cluster_correlated_features()`. Root cause: a column can pass the
  GLOBAL variance screening (over all 1,567 rows) but still be exactly
  constant within one CV fold's ~80% training subset -- correlation is
  undefined (0/0) for a constant column, producing `NaN` that crashed
  `scipy.cluster.hierarchy.linkage()`. Reproduced directly with a synthetic
  fold-locally-constant column before fixing, and re-tested after.
  Fixed by treating undefined (NaN) correlations as 0 (maximally distant --
  a locally-constant column carries no correlated signal to anything in
  that fold, which is the correct interpretation, not a workaround), with
  the diagonal explicitly forced back to 1.0 so the resulting distance
  matrix still has proper zero self-distance.
- **A second bug surfaced while testing the first fix**: naively doing
  `np.fill_diagonal(corr.values, 1.0)` failed with "underlying array is
  read-only" -- pandas can return a read-only view from `.values` in some
  cases. Fixed by explicitly copying before in-place mutation.
- Verified with: (1) a direct reproduction of the original crash on an
  isolated synthetic constant column, confirmed fixed; (2) confirmation
  that normal, non-degenerate correlation clustering still correctly groups
  genuinely correlated features and separates unrelated ones; (3) a full
  `nested_cv_shap_selection()` run with a near-constant column; (4) the
  complete RQ1 -> RQ2 -> RQ3 synthetic integration test re-run end-to-end
  with this fix in place.

## v11 -- 2026-07-29

- **Real bug found from a clean v9 run: permutation importance in
  `03_shap_analysis_rq2.ipynb` came back ~1e-17 (floating-point noise) for
  every single feature.** Root cause: it evaluated `rq1_best_tree` -- which
  RQ1 refits on 100% of the data -- on that SAME data. An unregularized
  RandomForest (no `max_depth` cap) can essentially memorize 1,567 training
  rows, so permuting any one feature barely hurts performance on data the
  model has already seen. This wasn't a code bug, but genuinely wrong
  methodology.
- **Fix: `02_modeling_rq1.ipynb` now saves a second, genuinely-held-out
  model** (`rq1_best_tree_holdout`, trained only on a fixed stratified 80/20
  split saved as `rq1_holdout_split.json`) alongside the existing full-data
  `rq1_best_tree` (kept as-is for SHAP's global-explanation use, which is
  standard practice and doesn't need held-out data the way permutation
  importance does). `03` now evaluates permutation importance with the
  holdout model on the held-out 20% only.
- **Implemented `04`'s previously-stubbed full-vs-reduced comparison**,
  reusing the same shared holdout split: trains full-feature and reduced-
  feature models on the train portion, evaluates both on the held-out test
  portion, and reports three real statistical comparisons via new
  functions in `src/metrics.py`:
  - `bootstrap_auc_comparison()` -- a paired bootstrap substitute for
    DeLong's test (documented reasoning for the substitution in the
    docstring: simpler to verify correctly than re-deriving DeLong's
    structural-component formula from scratch).
  - `mcnemar_test()` -- continuity-corrected chi-square, with an exact
    binomial fallback for small discordant-pair counts (<25).
  - `cohens_h_two_proportion_test()` -- Cohen's h effect size + a
    two-proportion z-test for accuracy comparison.
  All three verified against hand-constructed known-answer cases (clearly-
  different models detected as significant, identical/near-identical
  models detected as not significant) before shipping, not just read
  through.
- Verified the full RQ1 -> RQ2 -> RQ3 artifact chain end-to-end with a
  synthetic-data integration test (save holdout model/split in a RQ1-like
  step, load and use them in RQ2-like and RQ3-like steps) -- confirmed
  permutation importance is non-degenerate and matches SHAP's top features
  on synthetic data where the true signal is known.

## v10 -- 2026-07-29

- **Real failure found: a notebook ran with pre-v9 code even after v9 was
  correctly uploaded** (confirmed by cloning the live GitHub repo directly --
  it was genuinely on v9). Root cause: Colab's **Runtime -> Restart session**
  resets the Python kernel but does not wipe `/content` on disk -- unlike
  **Disconnect and delete runtime**, which does. If `/content/secom-
  explainable-vm` and the `.secom_setup_done` marker from an earlier,
  pre-v9 session both survived a "Restart session," the v9 session-marker
  logic would (correctly, by its prior design) skip `git pull` entirely,
  leaving stale code in place.
- **Fixed by un-bundling the two steps the marker was skipping together:**
  `git pull` now always runs unconditionally (cheap, a few seconds) --
  code can no longer go stale regardless of what state `/content` was left
  in. Only `pip install` (the actually slow step) is still skipped when the
  session marker is present. Verified with a simulation of the exact
  failure scenario (marker present from a prior session) confirming
  `git pull` now runs anyway.
- Practical note for using Colab going forward: prefer **Runtime ->
  Disconnect and delete runtime** over "Restart session" when starting a
  genuinely new attempt, since it guarantees a fully clean VM -- this fix
  makes stale code impossible either way, but a full disconnect avoids
  relying on that fix at all.

## v9 -- 2026-07-29

Three real bugs found from the first full end-to-end run (RQ1 result:
RandomForest won overall, TabNet ranked last of 4 by AUC-ROC -- but `03` and
`04` crashed partway through, so this needs a clean re-run to confirm).

- **SHAP shape bug (real `ValueError`, not cosmetic):** `shap.TreeExplainer`
  returns a single 3D array `(samples, features, classes)` for
  `RandomForestClassifier` in the shap version actually installed in Colab --
  the old code only checked for the older list-of-per-class-arrays
  convention, so `np.abs(sv).mean(axis=0)` produced a 2D result and crashed
  building a pandas Series from it. Fixed with a new shared
  `extract_positive_class_shap()` helper in `src/feature_selection.py`
  handling all 3 known shap output conventions (list, 3D array, already-2D),
  used by both `nested_cv_shap_selection()` and `03_shap_analysis_rq2.ipynb`'s
  inline SHAP cell. Verified against a real `RandomForestClassifier` +
  `TreeExplainer` reproduction of the exact bug, not just unit-style mocks.
- **LASSO selecting zero features:** `LogisticRegressionCV`'s default
  internal scoring is plain accuracy; on this ~93.4%-majority-class dataset,
  an all-zero-coefficient (majority-class-only) model already scores ~93%
  trivially, so C-selection kept picking maximum regularization every time.
  Fixed by setting `scoring="roc_auc"`. Verified on synthetic imbalanced
  data (6.67% positive, matching SECOM's real rate) -- selected the actually-
  predictive features instead of zero.
- **`00_run_all.ipynb`'s `--allow-errors` flag was masking real failures.**
  It was only meant to tolerate each notebook's own trailing live-export
  cell failing in batch mode, but it suppressed *any* cell error, which is
  why `03` and `04` were reported `[OK]` despite the SHAP crash above
  happening inside them. Fixed properly: each notebook's export cell now
  checks whether `_message.blocking_request` returned `None` (the actual
  batch-mode signal) and skips gracefully instead of raising, so
  `--allow-errors` is no longer needed at all and has been removed --
  `00_run_all` now fails loudly and correctly on genuine errors.

## v8 -- 2026-07-29

- **Session-marker optimization**, requested a few turns back and delayed
  until `04`'s timeout bug was fixed: the Colab setup cell now writes
  `/content/.secom_setup_done` after the first successful `git pull` +
  `pip install` in a session, and subsequent notebooks (e.g. `01`-`06`
  opened right after `00_run_all` already set things up) check for it and
  skip both steps if present. A brand new session (or a fresh clone) always
  runs the full setup regardless, since the marker lives only in `/content`,
  never in the repo -- verified with a standalone simulation of the control
  flow across 4 scenarios (first run, 2nd/3rd run same session, new session
  after restart) before shipping, not just a read-through.
- Still prints the commit hash every time either way, so version
  verification isn't affected by the skip.

## v7 -- 2026-07-29

- **Real bug fix: `04_feature_reduction_rq3.ipynb` timed out after 1,800s**
  inside its LASSO cross-check step. Root cause: `lasso_cross_check()` in
  `src/feature_selection.py` fit L1-penalized logistic regression
  (`liblinear` solver) directly on raw, unscaled sensor features -- with
  432 features on wildly different numeric scales, this converges
  extremely slowly (50 fits: `Cs=10 x cv=5`, each fighting to converge).
  Fixed by standardizing features first via an sklearn `Pipeline`
  (`StandardScaler` -> `LogisticRegressionCV`); also lowered `max_iter`
  from 5000 to 1000 so a future regression fails fast and loud instead of
  hanging silently for 30 minutes.
- Same latent issue existed in `02_modeling_rq1.ipynb`'s baseline
  `LogisticRegression` (didn't time out there, but same root cause) --
  fixed identically, wrapped in a `StandardScaler` Pipeline in both
  `make_models()` and `refit_full()`. `predict_proba`/`.fit()` interfaces
  are unchanged, so no other code needed to change.
- `05` and `06` were correctly never exported to HTML after `04`'s failure
  -- `00_run_all.ipynb` intentionally stops the whole run on first failure
  and only exports notebooks that actually completed; this was expected
  behavior, not a separate bug.

## v6 -- 2026-07-29

- **Free speedups, no effect on results:** added `n_jobs=-1` to every
  RandomForest and XGBoost instantiation (`02`, `04`) and to `03`'s
  `permutation_importance` call, so these use all available CPU cores
  instead of a single one by default. Same computation, same numbers,
  faster wall-clock time.
- All 7 notebook version markers bumped to v6 and independently re-verified
  by re-reading file content after the edit (not just trusting the script's
  print output, per the v5 lesson).

## v5 -- 2026-07-29

- **Bug fix in the version-marker system itself.** The v3 "bump to v3"
  script used `line.startswith("**Notebook version:**")`, which never
  matched because the marker line actually started with a leading newline
  character from how it was first inserted -- so 6 of 7 notebooks silently
  kept showing "v1" in their intro cell even though their actual code was
  correctly updated to v3. The script also printed a success message
  unconditionally, regardless of whether a match was found, which is why
  this went unnoticed until directly verified against the live GitHub repo.
  Fixed with a substring check instead, and verified this time by
  independently re-reading the file content after the edit, not just
  trusting the script's own print statement.
- No functional/code changes in this version -- only the version-marker
  text itself was wrong; the underlying pipeline logic was already correct
  as of v3.

## v4 -- 2026-07-29

- Replaced the hidden `.gitkeep` placeholder files in `data/raw/`,
  `data/model_ready/`, and `data/artifacts/` with visible `PLACEHOLDER.md`
  files. `.gitkeep` starts with a dot, so most file pickers/browsers hide it
  by default when selecting a folder to drag-and-drop -- this is why the
  `data/` folder was silently dropped from a prior upload. The new files are
  visible and also explain what populates each folder and when.

## v3 -- 2026-07-28

- **Correctness fix:** `02_modeling_rq1.ipynb` now saves its actual winning
  model(s) (`data/artifacts/`, via new `src/artifacts.py`) instead of every
  downstream notebook silently re-deriving its own assumption. Two artifacts
  are saved -- the best tree ensemble specifically (for RQ2/RQ3's
  TreeExplainer-based SHAP work) and the true overall winner (for RQ1's own
  "does TabNet beat trees" question) -- since these can legitimately differ.
- `03_shap_analysis_rq2.ipynb` no longer retrains its own fresh XGBoost; it
  loads RQ1's actual saved best-tree model.
- `04_feature_reduction_rq3.ipynb`'s nested-CV feature selection now uses
  RQ1's actual winning tree architecture (RF or XGBoost) instead of a
  hardcoded XGBoost assumption.
- Colab setup cell (all 7 notebooks) now runs `git pull` if the repo is
  already cloned (was previously skipped, risking a stale local copy), and
  prints the current commit hash + timestamp so you can verify against
  GitHub at a glance.

## v2 -- 2026-07-28

- Added `00_run_all.ipynb`: executes `01`-`06` in sequence, one command,
  with a pass/fail run summary. Handles the fact that each notebook's own
  live-Colab-frontend HTML export cell doesn't work in unattended/batch
  execution, by exporting HTML separately via plain `nbconvert` against the
  already-executed files instead.
- README updated with a "Running everything at once" usage section.

## v1 -- 2026-07-28

- `02_modeling_rq1.ipynb` built out with real analysis: 4 models (LogReg, RF,
  XGBoost, TabNet), stratified 5-fold CV with out-of-fold predictions,
  imbalance correction per model, results table (AUC-ROC, AUC-PR, BER, MCC),
  comparison plot.
- Added "Notebook version" marker to every notebook's intro cell.
- Established this changelog and the versioned-delivery naming convention.

## Pre-v1 (unversioned)

Everything prior to this point: repo scaffold, `01_data_screening.ipynb`
(real SECOM fetch + screening), `src/` modules (`preprocessing.py`,
`feature_selection.py`, `explainability.py`, `anomaly_detection.py`,
`metrics.py`, `fetch_data.py`), Colab setup cells, HTML export cells, and the
synopsis document itself. Not individually versioned since the naming
convention didn't exist yet.
