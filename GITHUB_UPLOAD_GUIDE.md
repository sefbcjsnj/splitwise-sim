# GitHub Upload Guide

## Recommended Path

Use a fork of the original SplitwiseSim repository.

1. Open the original repository on GitHub:

   ```text
   https://github.com/Mutinifni/splitwise-sim
   ```

2. Click `Fork` and create a fork under your GitHub account.

3. In this local repository, change `origin` to your fork:

   ```powershell
   cd C:\Users\Administrator\Desktop\splitwise\splitwise-sim
   $git = "C:\Users\Administrator\Desktop\splitwise\portable-git\cmd\git.exe"
   & $git remote set-url origin https://github.com/YOUR_USERNAME/splitwise-sim.git
   & $git remote -v
   ```

4. Commit the experiment files:

   ```powershell
   & $git add configs/orchestrator_repo/schedulers/mixed_pool_a100_bw*.yml
   & $git add scripts/*.py
   & $git add experiment_status.md report_draft.md GITHUB_UPLOAD_GUIDE.md
   & $git add pd_disaggregation_deliverables
   & $git commit -m "Add prefill-decode disaggregation parametric study"
   ```

5. Push to GitHub:

   ```powershell
   & $git push -u origin main
   ```

## VSCode Setup

VSCode can connect to GitHub through the Accounts icon in the lower-left corner.

If VSCode does not detect Git automatically, set the Git path to the portable Git executable:

```json
{
  "git.path": "C:\\Users\\Administrator\\Desktop\\splitwise\\portable-git\\cmd\\git.exe"
}
```

Then reload VSCode and use the Source Control panel to commit and push.

## What Is Included

The repository includes the original simulator plus:

- A100-only PD scheduler configs.
- Trace generation, sweep, aggregation, and plotting scripts.
- `report_draft.md`.
- `experiment_status.md`.
- `pd_disaggregation_deliverables/` with report-ready tables, figures, raw CSV summaries, and docs.

Large raw simulator output remains ignored by `.gitignore` through `results/` and `traces/`.
