# CONTRIBUTING

We welcome contributions!

## Building the project

Make sure to have a dedicated environment set-up. For that you can use conda, mamba, pyenv, etc. Once you have your environment, make sure to activate it and run:

```bash
pip install -e .
```

## Running tests

Install test pre-requisits:

```bash
pip install .[dev]
```

Run all tests:

```bash
pytest --nbval-lax --pyargs nbs --ignore=nbs/.ipynb_checkpoints
```

Or individual ones:

```bash
pytest nbs/notebook_name.ipynb --nbval-lax
```

An important note about the tests ran with `nbval` is that we're skipping all cells marked as `#| export`. This is due to the fact that `nbval` doesn't accept cells not having outputs even when we use the `--nbval-lax` parameter. This is likely a bug that should be fixed upstream. For our purpose is important to keep the cells running with no outputs as we depend on this to generate readable docs.


## Opening a pull request

- Fork this repository
- Create a new branch locally `git -b branch_name`
- Enter into the branch `git checkout branch_name`
- Create a new remote locally for example `git remote add upstream git@github.com:wbarfuss/pyCRLD.git`
- Commit the changes to your local branch `git add your_changes` and `git commit -m "commit_msg"`
- Before pushing changes make sure the code runs locally in your machine. See how to run the tests above
- Push the changes to your local remote. If your local remote is named "origin" (it is named origin by default) then you can push to it `git push origin branch_name`
- Go to the GitHub interface and click "Create Pull Request". Make sure your contributing from your `<origin>:<branch_name>` to `<upstream>:<main>`
