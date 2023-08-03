---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Information**
<!-- Make sure that your issue is not one of the known issues in the Solaar documentation at https://pwr-solaar.github.io/Solaar/ -->
<!-- Do not bother opening an issue for a version older than 1.1.8.  Upgrade to the latest version and see if your issue persists. -->
<!-- If you are not running the current version of Solaar, strongly consider upgrading to the newest version. -->
- Solaar version (`solaar --version` or `git describe --tags` if cloned from this repository):
- Distribution:
- Kernel version (ex. `uname -srmo`): `KERNEL VERSION HERE`
- Output of `solaar show`:

<details>

```
SOLAAR SHOW OUTPUT HERE
```
</details>

- Contents of `~/.config/solaar/config.yaml` (or `~/.config/solaar/config.json` if `~/.config/solaar/config.yaml` not present):

<details>

```
CONTENTS HERE
```
</details>


- Errors or warrnings from Solaar:
<!-- Under normal operation Solaar keeps a log of warning and error messages in ~/.tmp
while it is running as a file starting with 'Solaar'.
If this file is not available or does not have useful information you can
run Solaar as `solaar -dd`, after killing any running Solaar processes to
have Solaar log informational, warning, and error messages to stdout. -->


**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Go to '...'
2. Click on '....'
3. Scroll down to '....'
4. See error

**Screenshots**
If applicable, add screenshots to help explain your problem.

**Additional context**
Add any other context about the problem here.
