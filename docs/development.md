# Development and GitHub workflow

Git records local versions of your project. GitHub stores the remote repository and provides issues, pull requests, and automation. Publishing this command-line project on GitHub does not host a running study service.

## Install this documentation kit

Extract the ZIP into a temporary folder. Copy its contents into the existing project folder containing `study.py`. Merge the `tests` folder: retain `test_pipeline.py` and add `test_rate_limits.py`. This kit replaces the README but does not replace application modules. The new tests require the updated `curriculum_engine/llm_client.py` that supports request spacing. Do not create another nested application folder.

Keep the original priority script too. Its actual filename and location must be identified before adding it; it was not included in the lesson-generator ZIP. Do not assume a suggested filename is its existing name.

## First publication

From the project folder in CMD:

```bat
git --version
git status
git remote -v
```

If Git reports that this is not a repository, that is expected for an extracted ZIP. If a repository already exists, inspect its history/remotes before initializing or changing anything.

For a new local repository and a new EMPTY GitHub repository only:

```bat
git init -b main
git add README.md requirements.txt study.py curriculum_engine examples tests docs .gitignore .github
git diff --cached --stat
git diff --cached
py -m unittest discover -s tests -v
git commit -m "Add source-grounded lesson generation prototype"
```

Review staged files before committing. Add the original priority script separately after checking it for keys and personal data. Create an empty GitHub repository (no initial README, license, or gitignore when following this sequence). Then run `git remote add origin YOUR_REPOSITORY_URL` with the actual URL substituted, and `git push -u origin main`. Do not paste the placeholder literally. GitHub authentication may be required. If the remote already contains commits, stop and inspect it instead of force-pushing over them.

`.gitignore` excludes common local artifacts; it does not remove files already tracked by Git or identify every private file. Never stage real lecture notes, account keys, databases, or raw request dumps without reviewing them. Use the bundled synthetic demo for a public demonstration. If a real key was previously exposed, removing it from code does not revoke it.

## Everyday work

1. Create an issue with the problem, expected behavior, reproduction steps, and acceptance criteria.
2. Start a branch: `git switch -c fix/descriptive-name`.
3. Reproduce the bug. Record the useful, sanitized error, not the entire terminal transcript.
4. Make one focused change. Add a regression test when it protects meaningful behavior.
5. Run relevant checks; inspect `git diff` and `git status`.
6. Stage the specific changed files and commit with a factual message.
7. Push the branch with `git push -u origin fix/descriptive-name` and open a pull request.
8. Explain the cause, fix, verification, and remaining limitations. Merge after review and close the issue.

A solo project can use this workflow. Tiny documentation changes can be committed directly when appropriate. Do not create artificial commits to simulate earlier development: this retrospective documents the real history before Git tracking began.

## What belongs where?

| Record | Purpose |
|---|---|
| Commit | Exact code change and short reason |
| Issue | Reproducible bug or bounded feature request |
| Pull request | Reviewable explanation of a group of changes |
| README | Current project overview and quick start |
| docs/architecture.md | Current structure and reasons for boundaries |
| docs/debugging.md | Significant debugging findings and lessons |
| docs/backlog.md | Proposed next work, not claims of completion |
| Local terminal/runtime logs | Temporary operational evidence; exclude private data |

AI can help investigate errors and write patches. You remain responsible for understanding the change, checking its behavior, and explaining it. Describe AI assistance honestly; a generated explanation is not evidence that a fix works.

## References

- [Adding locally hosted code to GitHub](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github)
- [GitHub issues](https://docs.github.com/en/issues/tracking-your-work-with-issues/learning-about-issues/about-issues)
- [Ignoring files](https://docs.github.com/en/get-started/git-basics/ignoring-files)

## Documentation-kit verification

On 2026-10-11, all 29 offline tests passed in a local Python 3.12 environment against the recovered lesson package plus the patched client and the six retained tests. This was not a new live-provider test or a GitHub Actions run.
