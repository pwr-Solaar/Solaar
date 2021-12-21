#!/bin/bash

repo=pwr-Solaar/Solaar

usage() {
    basename="$(basename $0)"
    cat <<HELP
Usage: $basename [options]
Options:
  --dry-run           Does everything except tagging
  --help              Display this help and exit successfully
HELP
}

while [ $# != 0 ]
do
    case $1 in
    --dry-run)
        DRY_RUN=yes
        ;;
    --*)
        echo ""
        echo "Error: unknown option: $1"
        echo ""
        usage
        exit 1
        ;;
    -*)
        echo ""
        echo "Error: unknown option: $1"
        echo ""
        usage
        exit 1
        ;;
    esac

    shift
done

version=$(sed '/^__version__/!d' setup.py | cut -d\' -f2)

prerelease=false
echo $version | grep '.*rc.*' >/dev/null
[ $? -eq 0 ] && prerelease=true

ref=$(git symbolic-ref HEAD)
[ $? -ne 0 ] && echo 'Error: Failed current branch' && exit 1
branch=${ref##*/}

commit=$(git rev-list --max-count=1 HEAD)
[ $? -ne 0 ] && echo 'Error: Failed to get HEAD' && exit 1

remote=$(git config --get branch.$branch.remote)
[ $? -ne 0 ] && echo 'Error: Failed to get remote' && exit 1

remote_ref=$(git config --get branch.$branch.merge)
[ $? -ne 0 ] && echo 'Error: Failed to get remote HEAD' && exit 1
remote_branch=${remote_ref##*/}

github_token=$(cat ~/.github-token)
[ $? -ne 0 ] && echo 'Error: Failed to get github token (check ~/.github_token)' && exit 1

jq -V >/dev/null
[ $? -ne 0 ] && echo 'Error: jq is not installed' && exit 1

echo -e "\n\t** You are tagging a release for version $version **\n"
echo "Version: $version"
echo "Commit: $commit"
echo "Pre-release: $prerelease"
echo "Remote: $remote"
if [ "$branch" == "$remote_branch" ]; then
    echo "Branch: $branch"
else
    echo "Local branch: $branch"
    echo "Remote branch: $remote_branch"
fi

echo -e '\nPlease read RELEASE.md before continuing.\n'

read -p 'Are you sure you want to proceed? (y/n) ' -n 1 -r < /dev/tty
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && echo 'Release aborted.' && exit 1

read -p 'Are you *really* sure you want to proceed? (y/n) ' -n 1 -r < /dev/tty
echo
[[ ! $REPLY =~ ^[Yy]$ ]] && echo 'Release aborted.' && exit 1

# Check if version is in the changelog
grep '^# '"$version" ChangeLog.md >/dev/null
[ $? -ne 0 ] && echo 'Error: Version is not present in the changelog' && exit 1

# Check for uncomitted changes
git diff --quiet HEAD >/dev/null
[ $? -ne 0 ] && echo -e '\nError: Uncomitted changes found' && exit 1

# Check if commit is a version bump
git show -s --format=%B HEAD | grep "^release $version">/dev/null
#[ $? -ne 0 ] && echo -e '\nError: Commit does not look like a version bump' && exit 1

# Check if commit has been pushed to remote
remote_commit=$(git rev-list --max-count=1 $remote/$branch)
[ $? -ne 0 ] && echo -e '\nError: Failed to get remote HEAD' && exit 1
[ "$commit" != "$remote_commit" ] && echo -e '\nError: Commit has not been pushed to the remote' && exit 1

# Check if tag already exists
git rev-list --max-count=1 $version >/dev/null 2>/dev/null
[ $? -eq 0 ] && echo -e '\nError: Tag already exists' && exit 1

# Check if tag already exists on remote
git ls-remote $remote | grep "refs/tags/$version$" >/dev/null
[ $? -eq 0 ] && echo -e '\nError: Tag already exists on remote' && exit 1

echo

# Create tag
echo 'Creating tag...'
{
    echo "release $version"
    echo
    found=no
    while read -r line; do
        if [[ "$line" == *: ]]; then
            [ "$line" == "$version:" ] && found=yes || found=no
        fi
        [ "$found" == 'yes' ] && [ "${line:0:1}" == '*' ] && echo "$line"
    done < ChangeLog.md
} > /tmp/solaar-changelog
[ -z "$DRY_RUN" ] && git tag -s $version -F /tmp/solaar-changelog >/dev/null || true
[ $? -ne 0 ] && echo -e '\nError: Failed to create tag' && exit 1

# Push tag
echo 'Pushing tag...'
[ -z "$DRY_RUN" ] && git push $remote $version >/dev/null || true
[ $? -ne 0 ] && echo -e '\nError: Failed to push tag' && exit 1

# Create github release
body() {
    cat <<EOF
{
  "tag_name": "$version",
  "name": "$version",
  "body": "$(awk '{printf "%s\\n", $0}' /tmp/solaar-changelog)",
  "prerelease": $prerelease,
  "draft": false
}
EOF
}
echo 'Creating github release...'
##[ -z "$DRY_RUN" ] && url=$(curl -X POST --data "$(body)" "https://api.github.com/repos/$repo/releases?access_token=$github_token" 2>/dev/null | jq -r .html_url)
[ -z "$DRY_RUN" ] && url=$(curl -H 'Authorization: $github_token' -X POST --data "$(body)" "https://api.github.com/repos/$repo/releases" 2>/dev/null | jq -r .html_url)

[ -z "$DRY_RUN" ] && [ -z "$url" ] && echo -e '\nError: Failed to create a github release' && exit 1

[ -z "$DRY_RUN" ] && echo -e "\nRelease created: $url"

rm /tmp/solaar-changelog
