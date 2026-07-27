# Structural MRI cortical reconstruction with FreeSurfer

Single-subject cortical reconstruction and morphometry portfolio project.

## Dataset
- OpenNeuro ds000114
- Participant: sub-01
- Session: ses-test

## Software
- FreeSurfer 7.4.1
- Ubuntu 22.04.5 LTS
- Initial processing command: `recon-all -s sub-01_ses-test -i <T1w.nii.gz> -all -parallel -openmp 8 -noappend`
- OpenMP configuration verified from `recon-all_complete_sub-01_ses-test.log`: 8 threads
- The workstation exposed 16 logical CPU threads; 8 OpenMP threads were used for this run
- Reported runtime on the original workstation: approximately 1.356 hours

## Outputs
- Subcortical and global volumes
- Cortical thickness by Desikan-Killiany region
- Cortical area and volume by region
- Coronal, sagittal and axial Freeview quality-control figures

## Author
Rene Andrade Rey — ORCID 0000-0001-5627-579X
