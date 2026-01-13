#!/usr/bin/env bash
# remove-readme_pi5.sh
# Usage:
#   ./remove-readme_pi5.sh                      # default: owner=larduino repo=hawkesbay-can2mqtt (will perform actions)
#   ./remove-readme_pi5.sh --dry-run            # show actions without changing anything
#   ./remove-readme_pi5.sh --owner O --repo R   # override owner/repo
#
# Requirements:
# - git installed
# - gh CLI (optional but recommended for checking branch protection). If gh is missing, script will attempt pushes and fallback to creating removal branches on push-failure.
# - network access and push permission for branches (or ability to create branches)
#
# Important:
# - This will create commits that remove README_pi5.md from branch tips (history still contains the file).
# - If a branch is protected and you do not have permission to push to it, the script will create a new branch remove-readme_pi5/<branch> and push that instead.
# - Always run with --dry-run first.

set -euo pipefail

OWNER="larduino"
REPO="hawkesbay-can2mqtt"
REMOTE="origin"
DRY_RUN=0
WORKDIR="$(pwd)/tmp_remove_readme_$(date +%s)"
FILE_TO_REMOVE="README_pi5.md"
COMMIT_MSG="Remove README_pi5.md (old Pi5 README)"
GH_AVAILABLE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --owner) OWNER="$2"; shift 2 ;;
    --repo) REPO="$2"; shift 2 ;;
    --remote) REMOTE="$2"; shift 2 ;;
    --workdir) WORKDIR="$2"; shift 2 ;;
    -h|--help) sed -n '1,160p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

if command -v gh >/dev/null 2>&1; then
  GH_AVAILABLE=1
fi

echo "Owner: $OWNER"
echo "Repo:  $REPO"
echo "Remote: $REMOTE"
echo "File to remove: $FILE_TO_REMOVE"
echo "Dry run: $DRY_RUN"
echo
echo "Working directory: $WORKDIR"

mkdir -p "$WORKDIR"
cd "$WORKDIR"

REPO_URL="https://github.com/${OWNER}/${REPO}.git"

echo "Cloning ${REPO_URL} (this may take a moment)..."
if [[ $DRY_RUN -eq 1 ]]; then
  echo "[DRY RUN] git clone --no-tags --bare ${REPO_URL} ${REPO}.git"
else
  git clone --no-tags "${REPO_URL}" "${REPO}.git"
fi

cd "${REPO}.git"

echo "Fetching all remote refs..."
if [[ $DRY_RUN -eq 1 ]]; then
  echo "[DRY RUN] git fetch --all --prune"
else
  git fetch --all --prune
fi

# Get list of remote branches
mapfile -t BRANCHES < <(git for-each-ref --format='%(refname:short)' refs/remotes/"${REMOTE}" | sed "s#^${REMOTE}/##" | grep -v '^HEAD$' || true)

if [[ ${#BRANCHES[@]} -eq 0 ]]; then
  echo "No branches found on ${REMOTE}. Exiting."
  exit 0
fi

echo "Found ${#BRANCHES[@]} branches."

deleted_branches=()
created_branches=()
not_found_branches=()
errors=()

sanitize_branch_name() {
  # create a safe branch name suffix from original branch (replace / with --)
  local b="$1"
  b="${b//\//--}"
  b="${b// /_}"
  echo "$b"
}

check_branch_protected() {
  local branch="$1"
  if [[ $GH_AVAILABLE -eq 1 ]]; then
    # gh api requires auth; returns JSON with "protected": true/false
    if gh auth status >/dev/null 2>&1; then
      local resp
      if resp=$(gh api repos/"${OWNER}"/"${REPO}"/branches/"${branch}" 2>/dev/null); then
        # extract protected flag without jq
        if echo "$resp" | grep -q '"protected": true'; then
          return 0  # protected -> return 0/true
        else
          return 1  # not protected
        fi
      fi
    fi
  fi
  return 2 # unknown (no gh auth)
}

report() {
  echo
  echo "==== SUMMARY ===="
  echo "Deleted directly on branches:"
  for b in "${deleted_branches[@]}"; do echo "  - $b"; done
  echo
  echo "Created removal branches (push to these branches):"
  for b in "${created_branches[@]}"; do echo "  - $b"; done
  echo
  echo "Branches where file was not found:"
  for b in "${not_found_branches[@]}"; do echo "  - $b"; done
  echo
  if [[ ${#errors[@]} -gt 0 ]]; then
    echo "Errors:"
    for e in "${errors[@]}"; do echo "  - $e"; done
  fi
  echo "==== END ===="
}

for branch in "${BRANCHES[@]}"; do
  echo
  echo "Processing branch: $branch"

  # Test if file exists in remote branch
  if git ls-tree -r --name-only "${REMOTE}/${branch}" | grep -qx "${FILE_TO_REMOVE}"; then
    echo "  -> ${FILE_TO_REMOVE} exists in ${branch}"
  else
    echo "  -> ${FILE_TO_REMOVE} not found in ${branch}"
    not_found_branches+=("$branch")
    continue
  fi

  # Determine whether we can push to the branch directly
  protected_status=2
  if [[ $GH_AVAILABLE -eq 1 ]]; then
    check_branch_protected "$branch" || protected_status=$?
  fi

  if [[ $protected_status -eq 0 ]]; then
    echo "  -> branch is protected (via gh). Will create removal branch instead of pushing to ${branch}."
    can_push_to_branch=false
  elif [[ $protected_status -eq 1 ]]; then
    echo "  -> branch is NOT protected (via gh). Will attempt direct removal & push to ${branch}."
    can_push_to_branch=true
  else
    echo "  -> branch protection unknown (gh not available or not authenticated). Will attempt push and fallback on failure."
    can_push_to_branch=true
  fi

  if [[ $can_push_to_branch == true ]]; then
    # checkout branch locally from remote
    echo "  -> checking out ${branch} from ${REMOTE}/${branch}"
    if [[ $DRY_RUN -eq 1 ]]; then
      echo "[DRY RUN] git checkout -B ${branch} ${REMOTE}/${branch}"
      echo "[DRY RUN] git rm -f ${FILE_TO_REMOVE} || true"
      echo "[DRY RUN] git commit -m \"${COMMIT_MSG}\" || true"
      echo "[DRY RUN] git push ${REMOTE} ${branch}"
      deleted_branches+=("${branch} (dry-run)")
      continue
    fi

    git checkout -B "${branch}" "${REMOTE}/${branch}"

    # remove file
    if git rm -f --ignore-unmatch "${FILE_TO_REMOVE}"; then
      git commit -m "${COMMIT_MSG}" || { echo "  -> nothing to commit after rm (unexpected)"; }
    else
      echo "  -> git rm failed for ${FILE_TO_REMOVE} on ${branch}"
    fi

    # attempt push
    if git push "${REMOTE}" "${branch}" --porcelain; then
      sha=$(git rev-parse --short HEAD)
      echo "  -> pushed removal commit ${sha} to ${branch}"
      deleted_branches+=("${branch} -> ${sha}")
      continue
    else
      echo "  -> push to ${branch} failed. Will create removal branch instead."
      # fall through to create removal branch
      # continue to creation step
    fi
  fi

  # If we get here, either branch is protected or push failed: create new branch from remote branch
  safe_suffix=$(sanitize_branch_name "${branch}")
  new_branch="remove-readme_pi5/${safe_suffix}"

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "[DRY RUN] git checkout -B ${new_branch} ${REMOTE}/${branch}"
    echo "[DRY RUN] git rm -f ${FILE_TO_REMOVE} || true"
    echo "[DRY RUN] git commit -m \"${COMMIT_MSG}\" || true"
    echo "[DRY RUN] git push ${REMOTE} ${new_branch}"
    created_branches+=("${new_branch} (dry-run, from ${branch})")
    continue
  fi

  git checkout -B "${new_branch}" "${REMOTE}/${branch}"
  git rm -f --ignore-unmatch "${FILE_TO_REMOVE}" || true
  # Only commit if there are changes
  if git status --porcelain | grep -q .; then
    git commit -m "${COMMIT_MSG}" || true
  else
    echo "  -> Nothing to commit on ${new_branch} (file may not have been present at tip)."
  fi

  if git push "${REMOTE}" "${new_branch}"; then
    sha=$(git rev-parse --short HEAD)
    echo "  -> pushed ${new_branch} (${sha})"
    created_branches+=("${new_branch} -> ${sha} (from ${branch})")
  else
    echo "  -> push failed for ${new_branch}"
    errors+=("${branch}: failed to push ${new_branch}")
    # continue to next branch
  fi
done

report

echo
echo "Working copy left at: $WORKDIR/${REPO}.git (you can examine local branches there)"
if [[ $DRY_RUN -eq 1 ]]; then
  echo "DRY RUN - no changes were pushed."
fi

exit 0
