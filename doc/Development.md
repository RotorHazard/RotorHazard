# Development

This document is primarily for developers.
If you plan to contribute to RotorHazard by opening a pull request for a bugfix or feature, please read the following text before you start. This will help you in submitting your contribution in a form that has a good chance of being accepted.

## Using git and GitHub

Ensure you understand the GitHub workflow: https://guides.github.com/introduction/flow/index.html

Keep pull requests focused on one thing only, since this makes it easier to merge and test in a timely manner.

If you need help with pull requests there are guides on GitHub here:

https://help.github.com/articles/creating-a-pull-request

The main flow for a contributing is as follows:

1. Login to GitHub, go to the [RotorHazard repository](https://github.com/RotorHazard/RotorHazard) and press `fork`;
2. Then using the command line/terminal on your computer: `git clone <url to YOUR fork>`;
3. `cd RotorHazard`;
4. `git checkout master`;
5. `git checkout -b my-new-code`;
6. Make changes;
7. `git add <files that have changed>`;
8. `git commit`;
9. `git push origin my-new-code`;
10. Create pull request using GitHub UI to merge your changes from your new branch into `RotorHazard/master`;
11. Repeat from step 4 for new other changes.

The primary thing to remember is that separate pull requests should be created for separate branches.  Never create a pull request from your `master` branch.

Once you have created the PR,
every new commit/push in your branch will propagate from your fork into the PR in the main GitHub/RotorHazard repo.
Checkout another branch first if you want something else.

Push will often fail if you edit or squash commits in a branch already pushed. Never do such things after creating the PR.

Later, you can get the changes from the RotorHazard repo into your `master` branch by adding RotorHazard as a git remote and merging from it as follows:

1. `git remote add RotorHazard https://github.com/RotorHazard/RotorHazard.git`
2. `git checkout master`
3. `git fetch RotorHazard`
4. `git merge RotorHazard/master`
5. `git push origin master` is an optional step that will update your fork on GitHub
 
If using Windows, [TortoiseGit](https://tortoisegit.org) is highly recommended.

## Forking Delta5 and RotorHazard on GitHub

If you have a fork of the Delta5 repository in your GitHub account, you probably won't be able to create a fork of the RotorHazard repository in the same account. (GitHub does not seem to allow forks sourcing the same repository to be on there simultaneously.)  The solutions we have found are to either:

* Delete the copy of the Delta5 fork in you GitHub account and then create a fork of the RotorHazard repository into there, or
* Create a new account on GitHub and fork the RotorHazard repository into that account.

## Coding Style

When code is added to an existing file, the new code should follow what's already there in terms of indentation (spaces vs tabs), braces, naming conventions, etc.

If a PR is modifying functionality, try to avoid unnecessary whitespace changes (i.e., adding/removing trailing spaces or newlines), as this makes it harder to see the functional changes. Improvements to whitespace and code style should be implemented PRs that do only those things.
