#!/usr/bin/env bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PROJECT_ROOT="${FS_PROJECT_ROOT:-$REPO_ROOT}"
FREESURFER_HOME="${FREESURFER_HOME:-}"
FS_LICENSE="${FS_LICENSE:-${FREESURFER_HOME:+$FREESURFER_HOME/license.txt}}"

SUBJECT="${FS_SUBJECT:-sub-01_ses-test}"
T1="${FS_T1:-$PROJECT_ROOT/data/raw/sub-01/ses-test/anat/sub-01_ses-test_T1w.nii.gz}"
SUBJECTS_DIR="${SUBJECTS_DIR:-$PROJECT_ROOT/derivatives/freesurfer}"
THREADS="${FS_THREADS:-8}"

if [[ -z "$FREESURFER_HOME" || ! -f "$FREESURFER_HOME/SetUpFreeSurfer.sh" ]]; then
    echo "ERROR: set FREESURFER_HOME to a valid FreeSurfer installation" >&2
    exit 1
fi

if [[ ! -f "$FS_LICENSE" ]]; then
    echo "ERROR: FreeSurfer license not found: $FS_LICENSE" >&2
    exit 1
fi

if [[ ! -f "$T1" ]]; then
    echo "ERROR: T1 image not found: $T1" >&2
    exit 1
fi

mkdir -p "$SUBJECTS_DIR"

FS_TYPE="$(findmnt -T "$SUBJECTS_DIR" -n -o FSTYPE 2>/dev/null || true)"

case "$FS_TYPE" in
    exfat|vfat|fuseblk)
        echo "ERROR: SUBJECTS_DIR is on $FS_TYPE." >&2
        echo "FreeSurfer requires a filesystem supporting POSIX symbolic links, such as ext4." >&2
        exit 1
        ;;
esac

export FREESURFER_HOME
export FS_LICENSE
export SUBJECTS_DIR
export FS_FREESURFERENV_NO_OUTPUT=1
export OMP_NUM_THREADS="$THREADS"

source "$FREESURFER_HOME/SetUpFreeSurfer.sh"

echo "FreeSurfer: $(recon-all -version)"
echo "Subject: $SUBJECT"
echo "T1: $T1"
echo "SUBJECTS_DIR: $SUBJECTS_DIR"
echo "Filesystem: ${FS_TYPE:-unknown}"
echo "OpenMP threads per process: $THREADS"
echo "Start: $(date)"

exec recon-all \
    -s "$SUBJECT" \
    -i "$T1" \
    -all \
    -parallel \
    -openmp "$THREADS" \
    -noappend
