# Structural MRI cortical reconstruction with FreeSurfer

Single-subject cortical reconstruction and morphometry portfolio project.

## Dataset
- OpenNeuro ds000114
- Participant: sub-01
- Session: ses-test

## Software
- FreeSurfer 7.4.1
- Ubuntu 22.04.5 LTS
- Core processing: `recon-all -all`
- Reported runtime on the original workstation: approximately 1.356 hours
- Exact thread count was not documented; no OpenMP setting is claimed

## Outputs
- Subcortical and global volumes
- Cortical thickness by Desikan-Killiany region
- Cortical area and volume by region
- Coronal, sagittal and axial Freeview quality-control figures

## Author
Rene Andrade Rey — ORCID 0000-0001-5627-579X
