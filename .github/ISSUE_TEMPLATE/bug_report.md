---
name: Bug report
about: Create a report to help us improve
title: ''
labels: bug
assignees: ''

---

**Information**
<!-- Make sure that your issue is not one of the known issues in the
     Solaar documentation at https://pwr-solaar.github.io/Solaar/ -->
<!-- Make sure that Solaar's udev rule is running by executing
     `ls -l /dev/hidraw*` and looking for + as the last character of the permissions. -->
<!-- Do not bother opening an issue for a version older than 1.1.14.
     Upgrade to the current version and see if your issue persists. -->
<!-- If you are not running the current version of Solaar,
     strongly consider upgrading to the current version. -->
<!-- Note that some distributions have very old versions of Solaar
     as their default version.  -->

- Solaar version (`solaar --version` or `git describe --tags` if cloned from this repository):
- Distribution:
- Kernel version (ex. `uname -srmo`):
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
<!-- Under normal operation Solaar keeps a log of warning and error messages
in ~/.tmp while it is running, as a file starting with 'Solaar'.
If this file is not available or does not have useful information you can
run Solaar as `solaar -ddd`, after killing any running Solaar processes to
have Solaar log debug, informational, warning, and error messages to stdout. -->


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
