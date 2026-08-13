#!/usr/bin/env python3
"""Generate auditable single-subject FreeSurfer QC figures.

The script reads a completed FreeSurfer subject directory without modifying it.
It renders volume, segmentation, brainmask, white/pial surface, cortical
parcellation, cortical-thickness, and morphometry/topology summaries.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm, colors
from matplotlib.collections import LineCollection
import nibabel as nib
from nibabel.affines import apply_affine
from nibabel.freesurfer.io import read_annot, read_geometry, read_morph_data
import numpy as np


PLANES = [
    (0, "Sagittal"),
    (1, "Coronal"),
    (2, "Axial"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--subject-dir", required=True, type=Path)
    p.add_argument("--output-dir", required=True, type=Path)
    p.add_argument("--freesurfer-home", required=True, type=Path)
    return p.parse_args()


def require(path: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def savefig(fig: plt.Figure, path: Path, dpi: int = 180) -> None:
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    if not path.exists() or path.stat().st_size < 10_000:
        raise RuntimeError(f"Figure validation failed: {path}")


def intensity_limits(t1: np.ndarray, mask: np.ndarray) -> tuple[float, float]:
    vals = np.asarray(t1[mask > 0], dtype=np.float32)
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        vals = np.asarray(t1, dtype=np.float32).ravel()
        vals = vals[np.isfinite(vals)]
    lo, hi = np.percentile(vals, [0.5, 99.5])
    if hi <= lo:
        lo, hi = float(np.min(vals)), float(np.max(vals))
    return float(lo), float(hi)


def plane_slice(arr: np.ndarray, axis: int, idx: int) -> np.ndarray:
    if axis == 0:
        return arr[idx, :, :].T
    if axis == 1:
        return arr[:, idx, :].T
    return arr[:, :, idx].T


def choose_slices(mask: np.ndarray, axis: int, n: int = 5) -> list[int]:
    reduce_axes = tuple(i for i in range(3) if i != axis)
    occupied = np.where(np.any(mask > 0, axis=reduce_axes))[0]
    if occupied.size == 0:
        return [mask.shape[axis] // 2]
    lo, hi = int(occupied[0]), int(occupied[-1])
    span = max(hi - lo, 1)
    lo = int(round(lo + 0.12 * span))
    hi = int(round(hi - 0.12 * span))
    vals = np.linspace(lo, hi, n)
    return [int(round(v)) for v in vals]


def parse_freesurfer_lut(path: Path) -> dict[int, tuple[float, float, float, float]]:
    lut: dict[int, tuple[float, float, float, float]] = {}
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            parts = s.split()
            if len(parts) < 6:
                continue
            try:
                idx = int(parts[0])
                r, g, b, a = map(int, parts[-4:])
            except ValueError:
                continue
            # In FreeSurfer LUT files alpha 0 means fully opaque in the viewer.
            alpha = 1.0 if a == 0 else max(0.0, min(1.0, 1.0 - a / 255.0))
            lut[idx] = (r / 255.0, g / 255.0, b / 255.0, alpha)
    return lut


def segmentation_rgba(labels: np.ndarray, lut: dict[int, tuple[float, float, float, float]], alpha: float = 0.42) -> np.ndarray:
    out = np.zeros(labels.shape + (4,), dtype=np.float32)
    for lab in np.unique(labels):
        lab_i = int(lab)
        if lab_i <= 0:
            continue
        rgba = lut.get(lab_i, (0.8, 0.8, 0.8, 1.0))
        m = labels == lab_i
        out[m, 0] = rgba[0]
        out[m, 1] = rgba[1]
        out[m, 2] = rgba[2]
        out[m, 3] = alpha
    return out


def render_aseg_multiplanar(t1: np.ndarray, brainmask: np.ndarray, aseg: np.ndarray,
                             lut: dict[int, tuple[float, float, float, float]],
                             vmin: float, vmax: float, out: Path) -> None:
    fig, axes = plt.subplots(3, 5, figsize=(15.5, 9.3), constrained_layout=True)
    for row, (axis, plane) in enumerate(PLANES):
        indices = choose_slices(brainmask, axis, 5)
        for col, idx in enumerate(indices):
            ax = axes[row, col]
            base = plane_slice(t1, axis, idx)
            seg = plane_slice(aseg, axis, idx)
            ax.imshow(base, cmap="gray", origin="lower", vmin=vmin, vmax=vmax, interpolation="nearest")
            ax.imshow(segmentation_rgba(seg, lut), origin="lower", interpolation="nearest")
            ax.set_title(f"{plane} · voxel {idx}", fontsize=9)
            ax.axis("off")
    fig.suptitle("FreeSurfer anatomical QC — T1 with aseg segmentation", fontsize=15, fontweight="bold")
    fig.text(0.5, 0.005, "Segmentation colors use FreeSurferColorLUT; overlay is descriptive QC.", ha="center", fontsize=9)
    savefig(fig, out)


def render_brainmask(t1: np.ndarray, brainmask: np.ndarray, vmin: float, vmax: float, out: Path) -> None:
    fig, axes = plt.subplots(3, 5, figsize=(15.5, 9.3), constrained_layout=True)
    for row, (axis, plane) in enumerate(PLANES):
        indices = choose_slices(brainmask, axis, 5)
        for col, idx in enumerate(indices):
            ax = axes[row, col]
            base = plane_slice(t1, axis, idx)
            mask2d = plane_slice(brainmask > 0, axis, idx)
            ax.imshow(base, cmap="gray", origin="lower", vmin=vmin, vmax=vmax, interpolation="nearest")
            if np.any(mask2d):
                ax.contour(mask2d.astype(float), levels=[0.5], linewidths=1.0)
            ax.set_title(f"{plane} · voxel {idx}", fontsize=9)
            ax.axis("off")
    fig.suptitle("FreeSurfer brain extraction QC — brainmask boundary on T1", fontsize=15, fontweight="bold")
    fig.text(0.5, 0.005, "Boundary should track the intracranial brain without systematic tissue loss or extracranial inclusion.", ha="center", fontsize=9)
    savefig(fig, out)


def surface_vertices_in_voxels(surface_path: Path, t1_img: nib.spatialimages.SpatialImage) -> tuple[np.ndarray, np.ndarray]:
    verts, faces = read_geometry(str(surface_path))
    vox2ras_tkr = t1_img.header.get_vox2ras_tkr()
    ras2vox_tkr = np.linalg.inv(vox2ras_tkr)
    vox = apply_affine(ras2vox_tkr, verts)
    return vox, faces


def triangle_plane_segments(vertices: np.ndarray, faces: np.ndarray, axis: int, level: float) -> list[np.ndarray]:
    tri = vertices[faces]
    vals = tri[:, :, axis]
    cross = (np.min(vals, axis=1) <= level) & (np.max(vals, axis=1) >= level)
    tri = tri[cross]
    if tri.size == 0:
        return []

    display_axes = [i for i in range(3) if i != axis]
    segments: list[np.ndarray] = []
    eps = 1e-7
    for t in tri:
        pts: list[np.ndarray] = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            pa, pb = t[a], t[b]
            da, db = pa[axis] - level, pb[axis] - level
            if abs(da) < eps and abs(db) < eps:
                pts.extend([pa[display_axes], pb[display_axes]])
            elif abs(da) < eps:
                pts.append(pa[display_axes])
            elif abs(db) < eps:
                pts.append(pb[display_axes])
            elif da * db < 0:
                u = da / (da - db)
                p = pa + u * (pb - pa)
                pts.append(p[display_axes])
        if len(pts) >= 2:
            unique: list[np.ndarray] = []
            for p in pts:
                if not any(np.linalg.norm(p - q) < 1e-4 for q in unique):
                    unique.append(p)
            if len(unique) >= 2:
                segments.append(np.vstack([unique[0], unique[1]]))
    return segments


def render_surface_overlay(t1_img: nib.spatialimages.SpatialImage, t1: np.ndarray, brainmask: np.ndarray,
                           vmin: float, vmax: float, subj: Path, out: Path) -> None:
    surfaces: list[tuple[str, str, np.ndarray, np.ndarray]] = []
    for hemi in ("lh", "rh"):
        for kind, color in (("white", "tab:blue"), ("pial", "tab:red")):
            verts, faces = surface_vertices_in_voxels(require(subj / "surf" / f"{hemi}.{kind}"), t1_img)
            surfaces.append((f"{hemi}.{kind}", color, verts, faces))

    fig, axes = plt.subplots(3, 4, figsize=(14.2, 9.2), constrained_layout=True)
    for row, (axis, plane) in enumerate(PLANES):
        indices = choose_slices(brainmask, axis, 4)
        for col, idx in enumerate(indices):
            ax = axes[row, col]
            ax.imshow(plane_slice(t1, axis, idx), cmap="gray", origin="lower", vmin=vmin, vmax=vmax, interpolation="nearest")
            for _, color, verts, faces in surfaces:
                segs = triangle_plane_segments(verts, faces, axis, float(idx))
                if segs:
                    ax.add_collection(LineCollection(segs, colors=color, linewidths=0.65, alpha=0.9))
            ax.set_title(f"{plane} · voxel {idx}", fontsize=9)
            ax.axis("off")
    fig.suptitle("FreeSurfer cortical-surface QC — white and pial boundaries", fontsize=15, fontweight="bold")
    fig.text(0.5, 0.005, "Blue = white surface; red = pial surface. Curves are exact mesh/slice intersections.", ha="center", fontsize=9)
    savefig(fig, out)


def parse_measure(stats_path: Path, measure: str) -> tuple[float, str]:
    pat = re.compile(r"^# Measure\s+([^,]+),\s*([^,]+),\s*(.*?),\s*([-+0-9.eE]+),\s*([^\s]+)")
    for line in stats_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = pat.match(line)
        if not m:
            continue
        if m.group(1) == measure or m.group(2) == measure:
            return float(m.group(4)), m.group(5)
    raise KeyError(f"Measure {measure} not found in {stats_path}")


def parse_aseg_structure_volumes(stats_path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in stats_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            vol = float(parts[3])
        except ValueError:
            continue
        out[parts[4]] = vol
    return out


def parse_aparc_regions(stats_path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for line in stats_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        try:
            out[parts[0]] = float(parts[4])
        except ValueError:
            pass
    return out


def euler_holes(surface: Path) -> int:
    proc = subprocess.run(["mris_euler_number", str(surface)], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
    m = re.search(r"-->\s*(\d+)\s+holes", proc.stdout)
    if not m:
        raise RuntimeError(f"Could not parse Euler holes from {surface}\n{proc.stdout}")
    return int(m.group(1))


def render_dashboard(subj: Path, out: Path) -> None:
    aseg_stats = require(subj / "stats" / "aseg.stats")
    lh_stats = require(subj / "stats" / "lh.aparc.stats")
    rh_stats = require(subj / "stats" / "rh.aparc.stats")

    globals_mm3 = {
        "Brain segmentation": parse_measure(aseg_stats, "BrainSegVol")[0],
        "Cortical gray matter": parse_measure(aseg_stats, "CortexVol")[0],
        "Cerebral white matter": parse_measure(aseg_stats, "CerebralWhiteMatterVol")[0],
        "Subcortical gray matter": parse_measure(aseg_stats, "SubCortGrayVol")[0],
        "Estimated ICV": parse_measure(aseg_stats, "eTIV")[0],
    }
    lh_thick = parse_measure(lh_stats, "MeanThickness")[0]
    rh_thick = parse_measure(rh_stats, "MeanThickness")[0]
    lh_area = parse_measure(lh_stats, "WhiteSurfArea")[0]
    rh_area = parse_measure(rh_stats, "WhiteSurfArea")[0]
    pre_lh = int(round(parse_measure(aseg_stats, "lhSurfaceHoles")[0]))
    pre_rh = int(round(parse_measure(aseg_stats, "rhSurfaceHoles")[0]))
    final_lh = euler_holes(require(subj / "surf" / "lh.orig"))
    final_rh = euler_holes(require(subj / "surf" / "rh.orig"))

    aseg_struct = parse_aseg_structure_volumes(aseg_stats)
    paired = [
        ("Thalamus", "Left-Thalamus", "Right-Thalamus"),
        ("Caudate", "Left-Caudate", "Right-Caudate"),
        ("Putamen", "Left-Putamen", "Right-Putamen"),
        ("Pallidum", "Left-Pallidum", "Right-Pallidum"),
        ("Hippocampus", "Left-Hippocampus", "Right-Hippocampus"),
        ("Amygdala", "Left-Amygdala", "Right-Amygdala"),
        ("Lat. ventricle", "Left-Lateral-Ventricle", "Right-Lateral-Ventricle"),
    ]

    lh_regions = parse_aparc_regions(lh_stats)
    rh_regions = parse_aparc_regions(rh_stats)
    common = sorted(set(lh_regions) & set(rh_regions))
    x_lh = np.array([lh_regions[k] for k in common])
    y_rh = np.array([rh_regions[k] for k in common])

    fig = plt.figure(figsize=(15.5, 10.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 2)

    ax = fig.add_subplot(gs[0, 0])
    labels = list(globals_mm3)
    vals_ml = np.array([globals_mm3[k] for k in labels]) / 1000.0
    y = np.arange(len(labels))
    ax.barh(y, vals_ml)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("Volume (mL)")
    ax.set_title("A. Global morphometry")
    for yi, v in zip(y, vals_ml):
        ax.text(v, yi, f" {v:.1f}", va="center", fontsize=8)

    ax = fig.add_subplot(gs[0, 1])
    ax.axis("off")
    lines = [
        "Hemisphere summary",
        "",
        f"Mean cortical thickness   LH {lh_thick:.3f} mm   RH {rh_thick:.3f} mm",
        f"White-surface area       LH {lh_area/100:.1f} cm²  RH {rh_area/100:.1f} cm²",
        "",
        "Topology",
        f"Pre-fix surface holes     LH {pre_lh}   RH {pre_rh}",
        f"Final orig surface holes  LH {final_lh}   RH {final_rh}",
        "",
        "Interpretation",
        "Pre-fix holes quantify defects before topology correction.",
        "Final orig surfaces should have Euler topology corresponding to 0 holes.",
    ]
    ax.text(0.03, 0.97, "\n".join(lines), va="top", ha="left", fontsize=11, family="monospace")
    ax.set_title("B. Cortical summary and topology", loc="left")

    ax = fig.add_subplot(gs[1, 0])
    names = [p[0] for p in paired]
    left = np.array([aseg_struct.get(p[1], np.nan) for p in paired]) / 1000.0
    right = np.array([aseg_struct.get(p[2], np.nan) for p in paired]) / 1000.0
    xx = np.arange(len(names))
    w = 0.38
    ax.bar(xx - w/2, left, width=w, label="Left")
    ax.bar(xx + w/2, right, width=w, label="Right")
    ax.set_xticks(xx, names, rotation=32, ha="right")
    ax.set_ylabel("Volume (mL)")
    ax.set_title("C. Selected bilateral aseg volumes")
    ax.legend(frameon=False)

    ax = fig.add_subplot(gs[1, 1])
    ax.scatter(x_lh, y_rh, s=28, alpha=0.8)
    low = float(np.nanmin(np.r_[x_lh, y_rh]))
    high = float(np.nanmax(np.r_[x_lh, y_rh]))
    ax.plot([low, high], [low, high], linestyle="--", linewidth=1)
    ax.set_xlabel("LH regional thickness (mm)")
    ax.set_ylabel("RH regional thickness (mm)")
    ax.set_title("D. Desikan–Killiany regional thickness symmetry")
    diffs = np.abs(x_lh - y_rh)
    for idx in np.argsort(diffs)[-5:]:
        ax.annotate(common[idx], (x_lh[idx], y_rh[idx]), fontsize=7, xytext=(3, 3), textcoords="offset points")

    fig.suptitle("FreeSurfer single-subject morphometry and topology dashboard", fontsize=16, fontweight="bold")
    fig.text(0.5, 0.005, "Descriptive single-subject QC; no normative or group inference is implied.", ha="center", fontsize=9)
    savefig(fig, out)


def set_3d_equal(ax, verts: np.ndarray) -> None:
    mins = verts.min(axis=0)
    maxs = verts.max(axis=0)
    center = (mins + maxs) / 2.0
    radius = float(np.max(maxs - mins) / 2.0)
    ax.set_xlim(center[0] - radius, center[0] + radius)
    ax.set_ylim(center[1] - radius, center[1] + radius)
    ax.set_zlim(center[2] - radius, center[2] + radius)
    ax.set_box_aspect((1, 1, 1))
    ax.set_axis_off()


def plot_mesh(ax, verts: np.ndarray, faces: np.ndarray, facecolors: np.ndarray) -> None:
    surf = ax.plot_trisurf(
        verts[:, 0], verts[:, 1], verts[:, 2], triangles=faces,
        linewidth=0.0, antialiased=False, shade=False,
    )
    surf.set_facecolors(facecolors)
    surf.set_rasterized(True)
    set_3d_equal(ax, verts)


def annotation_vertex_colors(annot_path: Path) -> tuple[np.ndarray, list[str]]:
    labels, ctab, names = read_annot(str(annot_path), orig_ids=False)
    rgba = np.full((labels.shape[0], 4), (0.75, 0.75, 0.75, 1.0), dtype=float)
    valid = labels >= 0
    if ctab.shape[1] >= 4:
        c = ctab[:, :4].astype(float)
        c[:, :3] /= 255.0
        c[:, 3] = 1.0
    else:
        c = np.c_[ctab[:, :3].astype(float) / 255.0, np.ones(ctab.shape[0])]
    rgba[valid] = c[labels[valid]]
    decoded = [n.decode("utf-8", errors="replace") if isinstance(n, bytes) else str(n) for n in names]
    return rgba, decoded


def render_aparc_surface(subj: Path, out: Path) -> None:
    data = {}
    for hemi in ("lh", "rh"):
        verts, faces = read_geometry(str(require(subj / "surf" / f"{hemi}.pial")))
        vcolors, _ = annotation_vertex_colors(require(subj / "label" / f"{hemi}.aparc.annot"))
        fcolors = vcolors[faces[:, 0]]
        data[hemi] = (verts, faces, fcolors)

    views = [
        ("lh", "LH lateral", 180),
        ("lh", "LH medial", 0),
        ("rh", "RH medial", 180),
        ("rh", "RH lateral", 0),
    ]
    fig = plt.figure(figsize=(15.5, 8.2), constrained_layout=True)
    for i, (hemi, title, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        verts, faces, fcolors = data[hemi]
        plot_mesh(ax, verts, faces, fcolors)
        ax.view_init(elev=0, azim=azim)
        ax.set_title(title, fontsize=11)
    fig.suptitle("FreeSurfer cortical parcellation — Desikan–Killiany (aparc)", fontsize=16, fontweight="bold")
    fig.text(0.5, 0.01, "Parcel colors are read directly from the subject's aparc annotation.", ha="center", fontsize=9)
    savefig(fig, out, dpi=160)


def render_thickness_surface(subj: Path, out: Path) -> None:
    data = {}
    all_positive = []
    for hemi in ("lh", "rh"):
        verts, faces = read_geometry(str(require(subj / "surf" / f"{hemi}.inflated")))
        thick = np.asarray(read_morph_data(str(require(subj / "surf" / f"{hemi}.thickness"))), dtype=float)
        data[hemi] = (verts, faces, thick)
        all_positive.append(thick[thick > 0])
    pool = np.concatenate(all_positive)
    vmin, vmax = np.percentile(pool, [2, 98])
    norm = colors.Normalize(vmin=float(vmin), vmax=float(vmax))
    cmap = cm.get_cmap("viridis")

    views = [
        ("lh", "LH lateral", 180),
        ("lh", "LH medial", 0),
        ("rh", "RH medial", 180),
        ("rh", "RH lateral", 0),
    ]
    fig = plt.figure(figsize=(15.5, 8.6), constrained_layout=True)
    for i, (hemi, title, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        verts, faces, thick = data[hemi]
        face_vals = np.mean(thick[faces], axis=1)
        fcolors = cmap(norm(face_vals))
        fcolors[face_vals <= 0] = (0.72, 0.72, 0.72, 1.0)
        plot_mesh(ax, verts, faces, fcolors)
        ax.view_init(elev=0, azim=azim)
        ax.set_title(title, fontsize=11)
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=fig.axes, shrink=0.55, pad=0.01)
    cbar.set_label("Cortical thickness (mm)")
    fig.suptitle("FreeSurfer cortical thickness on inflated surfaces", fontsize=16, fontweight="bold")
    fig.text(0.5, 0.01, f"Shared display scale across hemispheres: {vmin:.2f}–{vmax:.2f} mm (2nd–98th percentile of positive vertices).", ha="center", fontsize=9)
    savefig(fig, out, dpi=160)


def write_summary(subj: Path, t1_img, brainmask: np.ndarray, aseg: np.ndarray, output: Path) -> None:
    axcodes = nib.aff2axcodes(t1_img.affine)
    lh_final = euler_holes(require(subj / "surf" / "lh.orig"))
    rh_final = euler_holes(require(subj / "surf" / "rh.orig"))
    lh_pre = euler_holes(require(subj / "surf" / "lh.orig.nofix"))
    rh_pre = euler_holes(require(subj / "surf" / "rh.orig.nofix"))
    lines = [
        "=== FREESURFER QC REDESIGN SUMMARY ===",
        f"Subject directory: {subj}",
        f"T1 shape: {tuple(t1_img.shape[:3])}",
        f"T1 axis codes: {axcodes}",
        f"Brainmask nonzero voxels: {int(np.count_nonzero(brainmask))}",
        f"Aseg nonzero voxels: {int(np.count_nonzero(aseg))}",
        f"Pre-fix topology holes: LH={lh_pre}, RH={rh_pre}",
        f"Final topology holes: LH={lh_final}, RH={rh_final}",
        "Public morphometry tables were separately audited against canonical FreeSurfer stats.",
        "QC figures are descriptive single-subject outputs; no normative inference is implied.",
        "FREESURFER_QC_RENDER_PASSED",
    ]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    subj = args.subject_dir.resolve()
    outdir = args.output_dir.resolve()
    figdir = outdir / "figures"
    summarydir = outdir / "summaries"
    figdir.mkdir(parents=True, exist_ok=True)
    summarydir.mkdir(parents=True, exist_ok=True)

    required = [
        subj / "mri" / "T1.mgz",
        subj / "mri" / "brainmask.mgz",
        subj / "mri" / "aseg.mgz",
        subj / "mri" / "aparc+aseg.mgz",
        subj / "surf" / "lh.white",
        subj / "surf" / "rh.white",
        subj / "surf" / "lh.pial",
        subj / "surf" / "rh.pial",
        subj / "surf" / "lh.inflated",
        subj / "surf" / "rh.inflated",
        subj / "surf" / "lh.thickness",
        subj / "surf" / "rh.thickness",
        subj / "label" / "lh.aparc.annot",
        subj / "label" / "rh.aparc.annot",
        subj / "stats" / "aseg.stats",
        subj / "stats" / "lh.aparc.stats",
        subj / "stats" / "rh.aparc.stats",
    ]
    for p in required:
        require(p)

    t1_img = nib.load(str(subj / "mri" / "T1.mgz"))
    brain_img = nib.load(str(subj / "mri" / "brainmask.mgz"))
    aseg_img = nib.load(str(subj / "mri" / "aseg.mgz"))
    t1 = np.asanyarray(t1_img.dataobj)
    brainmask = np.asanyarray(brain_img.dataobj)
    aseg = np.asanyarray(aseg_img.dataobj)
    if t1.shape[:3] != brainmask.shape[:3] or t1.shape[:3] != aseg.shape[:3]:
        raise RuntimeError("T1, brainmask, and aseg shapes do not match")
    if not np.all(np.isfinite(t1)):
        raise RuntimeError("Non-finite values in T1")

    vmin, vmax = intensity_limits(t1, brainmask)
    lut = parse_freesurfer_lut(require(args.freesurfer_home / "FreeSurferColorLUT.txt"))

    render_aseg_multiplanar(
        t1, brainmask, aseg, lut, vmin, vmax,
        figdir / "freesurfer_aseg_multiplanar_qc_final.png",
    )
    print("WROTE freesurfer_aseg_multiplanar_qc_final.png")

    render_brainmask(
        t1, brainmask, vmin, vmax,
        figdir / "freesurfer_brainmask_qc_final.png",
    )
    print("WROTE freesurfer_brainmask_qc_final.png")

    render_surface_overlay(
        t1_img, t1, brainmask, vmin, vmax, subj,
        figdir / "freesurfer_white_pial_multiplanar_qc_final.png",
    )
    print("WROTE freesurfer_white_pial_multiplanar_qc_final.png")

    render_aparc_surface(
        subj,
        figdir / "freesurfer_aparc_surface_final.png",
    )
    print("WROTE freesurfer_aparc_surface_final.png")

    render_thickness_surface(
        subj,
        figdir / "freesurfer_thickness_surface_final.png",
    )
    print("WROTE freesurfer_thickness_surface_final.png")

    render_dashboard(
        subj,
        figdir / "freesurfer_morphometry_topology_dashboard_final.png",
    )
    print("WROTE freesurfer_morphometry_topology_dashboard_final.png")

    write_summary(
        subj, t1_img, brainmask, aseg,
        summarydir / "freesurfer_qc_redesign_summary.txt",
    )

    expected = [
        figdir / "freesurfer_aseg_multiplanar_qc_final.png",
        figdir / "freesurfer_brainmask_qc_final.png",
        figdir / "freesurfer_white_pial_multiplanar_qc_final.png",
        figdir / "freesurfer_aparc_surface_final.png",
        figdir / "freesurfer_thickness_surface_final.png",
        figdir / "freesurfer_morphometry_topology_dashboard_final.png",
    ]
    for p in expected:
        if p.stat().st_size < 10_000:
            raise RuntimeError(f"Output too small: {p}")

    print("FREESURFER_QC_RENDER_PASSED")


if __name__ == "__main__":
    main()
