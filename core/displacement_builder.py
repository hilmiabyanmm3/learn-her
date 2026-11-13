import re
import os
import numpy as np
from core.cell_builder import extract_card
from core.qe_parser import parse_qe_atomic_positions

_RY = 13.6056980659
_BOHR = 0.529177210903
_HBAR = 1.054571817e-34
_E = 1.602176634e-19
_AMU = 1.66053906660e-27
_S_FACTOR = _HBAR * 1e10 / np.sqrt(_E * _AMU)
CM_TO_EV = 1.0 / 8065.544

ATOMIC_MASSES = {
    'H': 1.00794,
    'O': 15.9994,
    'C': 12.011,
    'N': 14.0067,
    'S': 32.065,
    'P': 30.9738,
    'FE': 55.845,
    'CO': 58.9332,
    'NI': 58.6934,
    'CU': 63.546,
    'PT': 195.084
}

INTERMEDIATE_ATOM_COUNT = {
    "H": 1,
    "O": 1,
    "OH": 2,
    "OOH": 3,
    "H2O": 3,
    "O2": 2
}

def adjust_control_namelist(content: str) -> str:
    """Robustly updates &CONTROL block: calculation = 'scf', tprnfor = .true., nstep = 1."""
    lines = content.splitlines()
    start_idx, end_idx = -1, -1

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if start_idx == -1:
            if stripped.upper().startswith('&CONTROL'):
                start_idx = idx
        else:
            if stripped in ['/', '&END'] or stripped.startswith('/'):
                end_idx = idx
                break

    if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
        fallback_block = [
            "&CONTROL",
            " calculation = 'scf'",
            "  tprnfor = .true.",
            "  nstep = 1",
            "/"
        ]
        return "\n".join(fallback_block) + "\n" + content

    body_lines = lines[start_idx + 1:end_idx]
    new_body_lines = []
    has_nstep = False

    for raw_line in body_lines:
        line = raw_line
        if re.search(r'(?i)\bcalculations?\s*=', line):
            continue
        if re.search(r'(?i)\btprnfor\s*=', line):
            continue
        if re.search(r'(?i)\bnstep\s*=', line):
            line = re.sub(r'(?i)(\bnstep\s*=\s*)\d+', r'\g<1>1', line)
            has_nstep = True
        if line.strip():
            new_body_lines.append(line)

    updated_control = [
        lines[start_idx],
        " calculation = 'scf'",
        "  tprnfor = .true."
    ]
    updated_control.extend(new_body_lines)
    if not has_nstep:
        updated_control.append("  nstep = 1")
    updated_control.append(lines[end_idx])

    return "\n".join(lines[:start_idx] + updated_control + lines[end_idx + 1:])

def get_adsorbate_indices(files: dict, target_key: str, atoms: list, inter_clean: str) -> list[int]:
    """Identifies the 0-based indices of all atoms that belong to the adsorbate."""
    surf_key = next((k for k in files if k.endswith("1-surface/PW.out") or k.endswith("1-surface/PW.in")), None)
    if surf_key:
        surf_text = files[surf_key].decode("utf-8", errors="ignore") if isinstance(files[surf_key], bytes) else files[surf_key]
        _, surf_atoms = parse_qe_atomic_positions(surf_text)
        if surf_atoms and len(atoms) > len(surf_atoms):
            return list(range(len(surf_atoms), len(atoms)))

    num_ads = INTERMEDIATE_ATOM_COUNT.get(inter_clean.upper(), 1)
    return list(range(max(0, len(atoms) - num_ads), len(atoms)))

def generate_finite_displacements(
    files: dict, 
    intermediate: str = "H", 
    delta: float = 0.015
) -> dict:
    """Generates 6 Cartesian displacement inputs for EACH atom of the specified adsorbate in 4-vibration/<adsorbate>/."""
    inter_clean = intermediate.replace("*", "").strip()
    target_key = next((k for k in files if k.endswith(f"3-adsorption/{inter_clean}/PW.in")), None)
    if not target_key:
        return files

    pw_text = files[target_key].decode("utf-8", errors="ignore") if isinstance(files[target_key], bytes) else files[target_key]
    unit, atoms = parse_qe_atomic_positions(pw_text)
    if not atoms:
        return files

    root_match = re.match(r"^([^/]+)/", target_key)
    root = f"{root_match.group(1)}/" if root_match else ""

    displace_indices = get_adsorbate_indices(files, target_key, atoms, inter_clean)

    template_adjusted = adjust_control_namelist(pw_text)
    template_clean = re.split(r'ATOMIC_POSITIONS', template_adjusted, flags=re.IGNORECASE)[0].strip()

    kpoints_card = extract_card(pw_text, ['K_POINTS', 'KPOINTS'])
    cell_card = extract_card(pw_text, ['CELL_PARAMETERS'])
    extra_cards = ""
    if kpoints_card:
        extra_cards += f"\n\n{kpoints_card}"
    if cell_card:
        extra_cards += f"\n\n{cell_card}"

    axes = [('x', 0), ('y', 1), ('z', 2)]
    for target_atom_idx in displace_indices:
        qe_idx = target_atom_idx + 1
        for axis_name, axis_idx in axes:
            for sign, label in [(-1.0, 'm'), (1.0, 'p')]:
                disp_atoms = [dict(a) for a in atoms]
                disp_atoms[target_atom_idx][axis_name] += sign * delta

                pos_lines = ["ATOMIC_POSITIONS (angstrom)"]
                for a in disp_atoms:
                    pos_lines.append(f"{a['element']:<4} {a['x']:20.10f} {a['y']:20.10f} {a['z']:20.10f}")
                pos_block = "\n".join(pos_lines)

                full_pwinput = f"{template_clean}\n\n{pos_block}{extra_cards}\n"
                filename = f"PWINPUT_atm{qe_idx}_{axis_name}{label}"
                files[f"{root}4-vibration/{inter_clean}/{filename}"] = full_pwinput

    return files

def _read_forces_from_text(file_content: str, idx_move: list[int]) -> np.ndarray:
    """Parses QE forces for requested 1-based atom indices."""
    forces = np.zeros((len(idx_move), 3))
    lines = file_content.splitlines()
    it = iter(lines)
    for line in it:
        if 'Forces acting' in line:
            while 'type' not in line:
                try:
                    line = next(it)
                except StopIteration:
                    return forces
            ia = 0
            while True:
                try:
                    line = next(it)
                except StopIteration:
                    break
                parts = line.split()
                if len(parts) >= 9 and parts[0] == 'atom':
                    atom_idx = int(parts[1])
                    if atom_idx in idx_move:
                        idx_pos = idx_move.index(atom_idx)
                        forces[idx_pos] = [
                            float(parts[6]) * _RY / _BOHR,
                            float(parts[7]) * _RY / _BOHR,
                            float(parts[8]) * _RY / _BOHR
                        ]
                else:
                    break
    return forces

def parse_vibrational_frequencies(files: dict, intermediate: str = "H", delta: float = 0.015) -> tuple[list[float], float | None]:
    """Parses frequency outputs or computes Hessian. Preserves negative (imaginary) modes for auditing."""
    inter_clean = intermediate.replace("*", "").strip()
    log_candidates = [
        k for k in files
        if f'4-vibration/{inter_clean}/' in k and not k.endswith('/') and not os.path.basename(k).startswith('.')
    ]

    # 1. Direct frequency parsing from vibration / dynmat output
    found_freqs = []
    for k in log_candidates:
        if k.endswith('.out') or 'LOG_' in k or 'vibr' in k.lower():
            content = files[k].decode("utf-8", errors="ignore") if isinstance(files[k], bytes) else files[k]
            # Match both positive and negative frequencies
            matches = re.findall(r'omega.*?=\s*([-+]?\d+\.\d+)\s*\[cm-1\]', content)
            if matches:
                found_freqs.extend([float(m) for m in matches])

    if found_freqs:
        # Sum ZPE only from bound, positive physical modes
        positive_modes = [f for f in found_freqs if f > 0]
        zpe = sum(0.5 * f * CM_TO_EV for f in positive_modes) if positive_modes else 0.0
        return found_freqs, zpe

    # 2. Construct Hessian from finite-displacement force outputs
    target_key = next((k for k in files if k.endswith(f"3-adsorption/{inter_clean}/PW.in")), None)
    if target_key:
        pw_text = files[target_key].decode("utf-8", errors="ignore") if isinstance(files[target_key], bytes) else files[target_key]
        _, atoms = parse_qe_atomic_positions(pw_text)
        if atoms:
            displace_indices = get_adsorbate_indices(files, target_key, atoms, inter_clean)
            idx_move = [i + 1 for i in displace_indices]
            n_atoms = len(idx_move)
            n_dim = 3 * n_atoms
            H = np.zeros((n_dim, n_dim))
            row_idx = 0
            has_forces = False

            for a in idx_move:
                for axis in 'xyz':
                    fm_candidates = [
                        k for k in log_candidates
                        if f"atm{a}_{axis}m" in k or f"atm{a}_{axis}_minus" in k
                    ]
                    fp_candidates = [
                        k for k in log_candidates
                        if f"atm{a}_{axis}p" in k or f"atm{a}_{axis}_plus" in k
                    ]
                    if fm_candidates and fp_candidates:
                        content_m = files[fm_candidates[0]].decode("utf-8", errors="ignore") if isinstance(files[fm_candidates[0]], bytes) else files[fm_candidates[0]]
                        content_p = files[fp_candidates[0]].decode("utf-8", errors="ignore") if isinstance(files[fp_candidates[0]], bytes) else files[fp_candidates[0]]
                        fm_forces = _read_forces_from_text(content_m, idx_move)
                        fp_forces = _read_forces_from_text(content_p, idx_move)
                        if np.any(fm_forces) or np.any(fp_forces):
                            H[row_idx] = 0.5 * (fm_forces - fp_forces).ravel() / (2.0 * delta)
                            row_idx += 1
                            has_forces = True

            if has_forces and row_idx == n_dim:
                H = 0.5 * (H + H.T)
                masses = np.array([ATOMIC_MASSES.get(atoms[i]['element'].upper(), 15.9994) for i in displace_indices])
                im = np.repeat(masses**-0.5, 3)
                omega2, _ = np.linalg.eigh(im[:, None] * H * im)
                
                # Check negative eigenvalues (imaginary frequencies)
                calc_freqs = []
                for val in omega2:
                    if val >= 0:
                        f_cm = float(np.sqrt(val) * _S_FACTOR * 8065.544)
                        if f_cm > 10.0:  # Threshold for non-translational
                            calc_freqs.append(f_cm)
                    else:
                        # Imaginary mode indicated by negative sign
                        f_cm = -float(np.sqrt(abs(val)) * _S_FACTOR * 8065.544)
                        calc_freqs.append(f_cm)

                if calc_freqs:
                    positive_modes = [f for f in calc_freqs if f > 0]
                    zpe = sum(0.5 * f * CM_TO_EV for f in positive_modes) if positive_modes else 0.0
                    return calc_freqs, zpe

    return [], None
