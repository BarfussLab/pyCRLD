# CONTRIBUTING

We welcome contributions!

## Building the project

Make sure to have a dedicated environment set-up. For that you can use conda, mamba, pyenv, etc. Once you have your environment, make sure to activate it and run:

```bash
pip install -e .
```

## Running tests

Make sure you are in the root directory of pyCRLD.

```bash
nbdev_test --path nbs --ignore=nbs/.ipynb_checkpoints
```

Use the `--do-print` option if you want to check the testing progress.

## Contributing

This project uses [nbdev](https://nbdev.fast.ai/getting_started.html). `nbdev` generates the library code based on Jupyter Notebooks. That means that every time you're adding a new part of the library you should make sure to run the command `nbdev_export --path <path to notebooks>` it will export your notebooks in `path` to Python modules and make it possible to import them later on.

### Opening a pull request

- Fork this repository
- Create a new branch locally `git -b branch_name`
- Enter into the branch `git checkout branch_name`
- Create a new remote locally for example `git remote add upstream git@github.com:wbarfuss/pyCRLD.git`
- Commit the changes to your local branch `git add your_changes` and `git commit -m "commit_msg"`
- Before pushing changes make sure the code runs locally in your machine. See how to run the tests above
- Push the changes to your local remote. If your local remote is named "origin" (it is named origin by default) then you can push to it `git push origin branch_name`
- Go to the GitHub interface and click "Create Pull Request". Make sure your contributing from your `<origin>:<branch_name>` to `<upstream>:<main>`
