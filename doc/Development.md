# Development

This document is primarily for developers.

If you plan to contribute to RotorHazard by opening a [pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests) for a bugfix or feature, please read the following text before you start. This will help you in submitting your contribution in a form that has a good chance of being accepted.

## Using git and GitHub

Ensure you understand the GitHub workflow: [https://docs.github.com/en/get-started/quickstart/github-flow](https://docs.github.com/en/get-started/quickstart/github-flow)

Keep pull requests focused on one thing only, since this makes it easier to merge and test in a timely manner. A pull request should only make changes to the files that are needed for the modification.

If you need help with pull requests there are guides on GitHub here: [GitHub - Creating a pull request](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request)

The main flow for a contributing is as follows:

1. Login to GitHub, go to the [RotorHazard repository](https://github.com/RotorHazard/RotorHazard) and press `fork`
2. Then using the command line/terminal on your computer: `git clone <url to YOUR fork>`
3. `cd RotorHazard`
4. `git checkout main`
5. `git checkout -b my-new-code`
6. Make changes
7. `git add <files that have changed>`
8. `git commit`
9. `git push origin my-new-code`
10. Create a pull request using the GitHub web UI to merge your changes from your new branch into `RotorHazard/main`
11. Repeat from step 4 for new other changes

The primary thing to remember is that separate pull requests should be created for separate branches.  Never create a pull request from your `main` branch.

Once you have created the PR, every new commit/push in your branch will propagate from your fork into the PR in the main GitHub/RotorHazard repo. Checkout another branch first if you want something else.

Later, you can get the changes from the RotorHazard repository into your `main` branch by adding the RotorHazard repository as a [git remote](https://help.github.com/en/github/collaborating-with-issues-and-pull-requests/configuring-a-remote-for-a-fork) ("upstream") and merging from it as follows:

1. `git remote add upstream https://github.com/RotorHazard/RotorHazard.git`
2. `git checkout main`
3. `git pull upstream main`
4. `git push origin main` (this is an optional step that will update your repository on GitHub)

<br>

If using Windows, [TortoiseGit](https://tortoisegit.org) is highly recommended.

## Coding Style

When code is added to an existing file, the new code should follow what's already there in terms of indentation (spaces vs tabs), braces, naming conventions, etc.

If a PR is modifying functionality, try to avoid unnecessary whitespace changes (i.e., adding/removing trailing spaces or newlines), as this makes it harder to see the functional changes. Improvements to whitespace and code style should be implemented with PRs that do only those things.

## Eclipse PyDev Project

The [Eclipse IDE](https://www.eclipse.org/eclipseide/) (with the [PyDev](https://www.pydev.org) extension) may be used to edit the Python source code -- the ".project" and ".pydevproject" files define the project, which may be loaded via "File | Open Projects from File System..." in Eclipse.

The [PyLint](https://github.com/pylint-dev/pylint#pylint) code analyzer is used to improve and reduce bugs in the code. All Python code in the project should be able to pass PyLint analysis with minimal errors and warnings. On Windows the package may be installed via the command:  `python -m pip install pylint`

See [here](https://www.pydev.org/manual_adv_pylint.html) for enabling PyLint code analysis on Eclipse with PyDev. With its default settings PyLint will flag more warnings than we want to deal with, so we disable some of them by navigating (in Eclipse) to "Preferences | PyDev | Editor | Code Analysis | PyLint" and entering the following into the box under "Arguments to pass to the pylint command":  `--disable=broad-except,bare-except,logging-not-lazy,logging-format-interpolation,global-statement,try-except-raise,unused-argument`

The batch/script files in the 'tools' directory may be used to run the PyLint analysis from the command line: 'pylintchk' checks for errors only, 'pylintchkw' checks for errors and warnings.
