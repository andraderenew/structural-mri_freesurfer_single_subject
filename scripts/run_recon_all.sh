#!/usr/bin/env bash

export FREESURFER_HOME="$HOME/Downloads/freesurfer"
export FS_LICENSE="$FREESURFER_HOME/license.txt"
export FS_FREESURFERENV_NO_OUTPUT=1

source "$FREESURFER_HOME/SetUpFreeSurfer.sh"

set -eo pipefail

PROJECT="/media/andraderenew/Elements/neuroimaging/structural-mri_freesurfer_single_subject"
export SUBJECTS_DIR="$PROJECT/derivatives/freesurfer"

SUBJECT="sub-01_ses-test"
T1="$PROJECT/data/raw/sub-01/ses-test/anat/sub-01_ses-test_T1w.nii.gz"
THREADS=8

export OMP_NUM_THREADS="$THREADS"

if [[ ! -f "$T1" ]]; then
    echo "ERROR: falta la imagen T1:"
    echo "$T1"
    exit 1
fi

if [[ ! -f "$FS_LICENSE" ]]; then
    echo "ERROR: falta la licencia:"
    echo "$FS_LICENSE"
    exit 1
fi

mkdir -p "$SUBJECTS_DIR"

echo "FreeSurfer: $(recon-all -version)"
echo "Sujeto: $SUBJECT"
echo "T1: $T1"
echo "SUBJECTS_DIR: $SUBJECTS_DIR"
echo "Procesamiento paralelo: dos hemisferios"
echo "OpenMP por proceso: $THREADS"
echo "Inicio: $(date)"

exec recon-all \
    -s "$SUBJECT" \
    -i "$T1" \
    -all \
    -parallel \
    -openmp "$THREADS" \
    -noappend
