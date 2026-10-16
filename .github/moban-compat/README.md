This directory restores Moban template generation on Python 3.15 for pyexcel maintainers.

Create a Python 3.15 virtual environment, activate it and run:

```sh
bash .github/moban-compat/prepare.sh
python .github/moban-compat/test_compat.py
python .github/moban-compat/test_workflow.py
```

Before running `moban -f`, check out these template trees at the revisions used by the workflow:

| Directory | Repository | Revision |
| --- | --- | --- |
| `.moban.d/upstream/pyexcel` | `pyexcel/pyexcel-mobans` | `b95b0893e70834d9aefe7fab846f3967d1628186` |
| `.moban.d/upstream/pypi` | `moremoban/pypi-mobans` | `862f395a444d5123a75349c464efdb56ee5721f7` |

Initialise the pypi tree's `templates/gitignore` submodule at its recorded revision. Keep these checkouts out of commits. The local `mobanfile.yaml` preserves the shared configuration's targets and directory order; `.moban.d/moban-update.yml` shadows its workflow template.

Run `python .github/moban-compat/test_generation.py` in a disposable checkout. It writes every generated output and uses a fabricated contributor response to check repeated generation without network access.

The two patches repair the latest published fs 2.4.16 and jinja2-fsloader 0.3.0 wheels. They use standard library namespace, entrypoint and resource APIs, and permit the tested Jinja 3.1.6. Upstream distribution names, versions and MIT licence files are retained. These are downstream build 1 wheels, labelled for Python 3.15 or later. They are not upstream releases.

Requirements and wheel hashes target Linux x86-64 Python 3.15. `prepare.sh` rebuilds with fixed ZIP timestamps, verifies the resulting hashes and checks the installed dependency graph. Update the original hashes, reviewed patches, repaired hashes and runtime closure together when upgrading, then rerun the checks.

Generation runs without write credentials. A fresh job accepts only regular, non-executable generated files at an explicit source revision. Workflow changes remain in the `moban-changes` artifact for maintainer review. The write token is scoped to the commit job, including its pinned actions. Its shell receives `GH_TOKEN` only in the push step; dependencies and generated scripts never run in that job. Branch protection may require a maintainer to apply the artifact instead.
