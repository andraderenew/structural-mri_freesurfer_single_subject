# FreeSurfer single-subject QC validation

## Subject

- Dataset: OpenNeuro `ds000114`
- Participant: `sub-01`
- Session: `ses-test`
- FreeSurfer subject: `sub-01_ses-test`
- FreeSurfer version: 7.4.1

## Reconstruction completion

The canonical reconstruction log records two earlier failed attempts followed by a successful completed run.

Final status:

```text
recon-all -s sub-01_ses-test finished without error
```

The successful completion occurred on 23 July 2026.

## Canonical outputs

The completed FreeSurfer subject was verified to contain:

- `mri/T1.mgz`
- `mri/brainmask.mgz`
- `mri/aseg.mgz`
- `mri/aparc+aseg.mgz`
- `surf/lh.white`
- `surf/rh.white`
- `surf/lh.pial`
- `surf/rh.pial`
- `surf/lh.inflated`
- `surf/rh.inflated`
- `surf/lh.thickness`
- `surf/rh.thickness`
- `label/lh.aparc.annot`
- `label/rh.aparc.annot`
- `stats/aseg.stats`
- `stats/lh.aparc.stats`
- `stats/rh.aparc.stats`

The pial surface paths resolve to valid FreeSurfer surface files.

## Topology validation

Euler topology was checked using `mris_euler_number`.

### Before topology correction

```text
lh.orig.nofix: 14 holes
rh.orig.nofix: 11 holes
```

These values agree with the FreeSurfer `aseg.stats` measures:

```text
lhSurfaceHoles = 14
rhSurfaceHoles = 11
SurfaceHoles   = 25
```

FreeSurfer defines these measures as surface defects before topology fixing.

### Final corrected surfaces

```text
lh.orig: Euler number 2 -> 0 holes
rh.orig: Euler number 2 -> 0 holes
```

Both final hemispheric surfaces therefore passed the topology check.

## Table provenance validation

All seven repository morphometry tables were regenerated from the canonical FreeSurfer statistics using:

- `asegstats2table`
- `aparcstats2table`

Results:

```text
table1_aseg_volumes.tsv              EXACT_MATCH=YES
table2_lh_cortical_thickness.tsv     EXACT_MATCH=YES
table3_rh_cortical_thickness.tsv     EXACT_MATCH=YES
table4_lh_cortical_area.tsv          EXACT_MATCH=YES
table5_rh_cortical_area.tsv          EXACT_MATCH=YES
table6_lh_cortical_volume.tsv        EXACT_MATCH=YES
table7_rh_cortical_volume.tsv        EXACT_MATCH=YES
```

This establishes direct provenance between the public quantitative tables and the completed canonical FreeSurfer reconstruction.

## Selected morphometry

From the canonical FreeSurfer statistics:

```text
BrainSegVol                     865479.000000 mm^3
BrainSegVolNotVent              844231.000000 mm^3
CortexVol                       345971.666327 mm^3
CerebralWhiteMatterVol          358714.000000 mm^3
SubCortGrayVol                   43083.000000 mm^3
EstimatedTotalIntraCranialVol  1148761.753772 mm^3

LH MeanThickness                     2.2032 mm
RH MeanThickness                    2.15459 mm

LH WhiteSurfArea                     69577.6 mm^2
RH WhiteSurfArea                    69765.9 mm^2
```

## Visual QC set

The redesigned QC package contains six figures:

1. `freesurfer_aseg_multiplanar_qc_final.png`
2. `freesurfer_brainmask_qc_final.png`
3. `freesurfer_white_pial_multiplanar_qc_final.png`
4. `freesurfer_aparc_surface_final.png`
5. `freesurfer_thickness_surface_final.png`
6. `freesurfer_morphometry_topology_dashboard_final.png`

The figures cover:

- multiplanar anatomical segmentation QC
- brain-extraction QC
- white/pial cortical-boundary QC
- Desikan-Killiany cortical parcellation
- vertex-wise cortical thickness on inflated surfaces
- global morphometry, bilateral subcortical measures, regional cortical symmetry, and topology

The final figures were visually reviewed after iterative layout correction.

## Scope

This is a single-subject processing and QC project.

The morphometric measurements are descriptive. No normative reference comparison, diagnostic classification, or group-level statistical inference is claimed.
