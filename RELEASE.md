# Solaar releases

###### Please read before making a release.

We support two type of releases: normal releases (ex. `1.0.0`) and release
candidates (ex. `1.0.0-rc1`). Release candidates must have a `-rcX` prefix.

Release routine:
  - Update the ChangeLog and setup.py to the new version and create a commit
    - Release commits must start with `release VERSION`
  - Invoke `./release.sh`
    - Git tags are signed so you must have GPG set up
    - You are required to have a have a github token with `public_repo` access
      in `~/.github-token`
