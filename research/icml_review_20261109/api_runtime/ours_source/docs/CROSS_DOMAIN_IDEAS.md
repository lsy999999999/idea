# Cross-disciplinary idea generation

The current objective is to propose research ideas. Immediate implementation, available data,
experiments, and complete solutions are not prerequisites. Final checking follows the two
judgments in [IDEA_CHECK.md](IDEA_CHECK.md): similar prior directions and obvious mathematical
or logical errors.

`cross_domain_ideas.py` adds separate disciplinary inputs before the existing idea builder and
final checker. Four domain inputs, one synthesis role, and one final check role form this
pilot's six logical roles. They run sequentially through the reusable Luna runtime. Separate
contexts and different source material encourage diverse inputs; they do not establish
independent expertise or guarantee creativity.

Each domain input extracts structures and open tensions from actual sources. The synthesizer
then proposes ideas with explicit correspondences: which concept is transferred, what it
corresponds to in the other field, how it changes the research question, and where the analogy
might break. The complete batch is saved before final checking. Crossing fields is a generation
instruction; the final checker has no third acceptance gate.

The first pilot uses statistical physics, evolutionary ecology, immunology, and mechanism
design. These are configurable inputs, not fixed domain boundaries for the system. No scientific
experiment runs in this mode. A citation search or arithmetic sanity check is not validation of
the proposed research direction.

Completed pilot: [proposals and judgments](../CROSS_DOMAIN_RESULTS.md). Its final checker
received one bounded follow-up to apply the user's broad similarity threshold. For this
run, use `check_report_calibrated.json`; `check_report.json` retains the initial screen.
The reusable prompt now asks for short established search terms and explicitly rejects
requiring an exact conjunction of all proposed details before recognizing prior work.

```bash
cd /Applications/ideas/1103_boundary_discovery
.venv/bin/python -u src/cross_domain_ideas.py \
  --brief bootstrap/CROSS_DOMAIN_IDEA_BRIEF.md \
  --domains bootstrap/CROSS_DOMAIN_FIELDS.json \
  --run-dir runs/cross_domain_ideas_001 \
  --count 3 --model gpt-6-luna --effort high \
  --timeout 600 --check-timeout 900
```

Repeat the same command to resume. A completed run does not repeat model calls. Each failed
runtime stage has at most one automatic retry, retained under a distinct stage ID.

Read `ideas.json` for every proposal, `check_report.json` for both final judgments, and
`idea_state.json` for progress. Raw source notes and model outputs are in `stages/`.
Schema checks verify completeness and handoff; semantic originality and coherence remain
the final check agent's judgments supported by its recorded sources.
