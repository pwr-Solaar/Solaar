# Solaar releases

## Please read before making a release

We support two type of releases: normal releases (ex. `1.0.0`) and release
candidates (ex. `1.0.0rc1`). Release candidates must have a `rcX` suffix.

Release routine:

- Update version in `lib/solaar/version`
- Add release changes to `CHANGELOG.md`
- Add release information to `share/solaar/io.github.pwr_solaar.solaar.metainfo.xml`
- Create a commit that starts with `release VERSION`
- Push commit to Solaar repository
- Invoke `./release.sh`
  - Git tags are signed so you must have GPG set up
  - You are required to have a github token with `public_repo` access
    in `~/.github-token`
