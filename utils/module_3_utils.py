import io
import os
import re
import numpy as np
import openpyxl
from utils.common import CM_TO_EV, RY_TO_EV, build_zip_from_dict, extract_zip_to_dict, find_excel_file
from utils.qe_parser import parse_qe_atomic_positions, parse_qe_total_energy

_RY = 13.6056980659
_BOHR = 0.529177210903
_HBAR = 1.054571817e-34
_E = 1.602176634e-19
_AMU = 1.66053906660e-27
_S_FACTOR = _HBAR * 1e10 / np.sqrt(_E * _AMU)

def extract_card(content: str, card_names: list) -> str:
    """Extracts a specific QE card and its data block from input content."""
    names_pattern = "|".join(card_names)
    known_cards = r'(?:ATOMIC_SPECIES|ATOMIC_POSITIONS|K_POINTS|KPOINTS|CELL_PARAMETERS|CONSTRAINTS|OCCUPATIONS|ATOMIC_VELOCITIES|ATOMIC_FORCES|HUBBARD|\&[A-Za-z]+)'
    pattern = rf'(?m)^\s*({names_pattern})\b[^\n]*(?:\n|$)(?:(?!^\s*{known_cards}\b).*(?:\n|$))*'
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return ""

def adjust_control_namelist(content: str) -> str:
    """
    Robustly updates &CONTROL block so that:
      calculation = 'scf'
      tprnfor = .true.
      nstep = 1
    are reliably enforced regardless of original spacing or quotes,
    without corrupted namelist slashes.
    """
    lines = content.splitlines()
    start_idx = -1
    end_idx = -1

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if start_idx == -1:
            if stripped.upper().startswith('&CONTROL'):
                start_idx = idx
        else:
            if stripped == '/' or stripped.startswith('/') or stripped.upper() in ['&END', '/']:
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

def _read_forces_from_log(file_content: str, atom_idx: int) -> np.ndarray:
    """Parses forces (Ry/Bohr) acting on a 1-based atom index from a QE output file."""
    forces = np.zeros(3)
    lines = file_content.splitlines()
    it = iter(lines)
    for line in it:
        if 'Forces acting' in line:
            while 'type' not in line:
                try:
                    line = next(it)
                except StopIteration:
                    return forces
            while True:
                try:
                    line = next(it)
                except StopIteration:
                    break
                parts = line.split()
                if len(parts) >= 9 and parts[0] == 'atom':
                    if int(parts[1]) == atom_idx:
                        forces = np.array([
                            float(parts[6]) * _RY / _BOHR,
                            float(parts[7]) * _RY / _BOHR,
                            float(parts[8]) * _RY / _BOHR,
                        ])
                        return forces
                else:
                    break
    return forces

def process_tab1_energies(zip_bytes: bytes, delta: float = 0.015, include_in_ext: bool = False) -> tuple[bytes | None, dict | None, str | None]:
    """
    Parses total energies for H2, H2O, and adsorbed H slab, writes to Excel,
    and generates finite-displacement inputs:
      - calculation = 'scf'
      - tprnfor = .true.
      - nstep = 1
      - Filenames named PWINPUT_atm{N}_{axis}{suffix} (without .in)
      - Guaranteed zero-duplication coordinate replacement
    """
    files = extract_zip_to_dict(zip_bytes)

    h_ads_out_key = next((k for k in files if k.endswith("3-adsorption/H/PW.out")), None)
    h2_out_key = next((k for k in files if k.endswith("2-isolated-gas/H2/PW.out")), None)
    h2o_out_key = next((k for k in files if k.endswith("2-isolated-gas/H2O/PW.out")), None)

    if not h_ads_out_key:
        return None, None, "Missing `3-adsorption/H/PW.out` in the uploaded zip."

    e_ads_ry, e_ads_ev = parse_qe_total_energy(files[h_ads_out_key].decode("utf-8", errors="ignore"))
    e_h2_ry, e_h2_ev = (None, None)
    if h2_out_key:
        e_h2_ry, e_h2_ev = parse_qe_total_energy(files[h2_out_key].decode("utf-8", errors="ignore"))
    e_h2o_ry, e_h2o_ev = (None, None)
    if h2o_out_key:
        e_h2o_ry, e_h2o_ev = parse_qe_total_energy(files[h2o_out_key].decode("utf-8", errors="ignore"))

    # Update Excel
    excel_info = find_excel_file(files)
    if excel_info:
        excel_path, excel_bytes = excel_info
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        if "1-adsorbate" in wb.sheetnames and e_ads_ry is not None:
            ws1 = wb["1-adsorbate"]
            ws1.cell(row=2, column=4, value=e_ads_ry)
            ws1.cell(row=2, column=5, value="='1-adsorbate'!D2*13.605698066")

        if "2-isolated-mol" in wb.sheetnames:
            ws2 = wb["2-isolated-mol"]
            if e_h2_ev is not None:
                ws2.cell(row=2, column=1, value="H2")
                ws2.cell(row=2, column=2, value=e_h2_ev)
                ws2.cell(row=2, column=3, value=0.2720)
                ws2.cell(row=2, column=4, value=0.4040)
            if e_h2o_ev is not None:
                ws2.cell(row=3, column=1, value="H2O")
                ws2.cell(row=3, column=2, value=e_h2o_ev)
                ws2.cell(row=3, column=3, value=0.5600)
                ws2.cell(row=3, column=4, value=0.6700)

        if "3-ads-energy" in wb.sheetnames:
            ws3 = wb["3-ads-energy"]
            ws3.cell(row=2, column=2, value="='1-adsorbate'!E2-'1-adsorbate'!C2-0.5*'2-isolated-mol'!B2")

        out_buf = io.BytesIO()
        wb.save(out_buf)
        files[excel_path] = out_buf.getvalue()

    # Generate vibration finite-displacement files
    h_in_key = next((k for k in files if k.endswith("3-adsorption/H/PW.in")), None)
    if h_in_key:
        h_in_text = files[h_in_key].decode("utf-8", errors="ignore")
        unit, atoms = parse_qe_atomic_positions(h_in_text)
        if atoms:
            root_match = re.match(r"^([^/]+)/", h_in_key)
            root = f"{root_match.group(1)}/" if root_match else ""
            h_idx = len(atoms) - 1

            template_adjusted = adjust_control_namelist(h_in_text)
            template_clean = re.split(r'ATOMIC_POSITIONS', template_adjusted, flags=re.IGNORECASE)[0].strip()

            kpoints_card = extract_card(h_in_text, ['K_POINTS', 'KPOINTS'])
            cell_card = extract_card(h_in_text, ['CELL_PARAMETERS'])
            extra_cards = ""
            if kpoints_card:
                extra_cards += f"\n\n{kpoints_card}"
            if cell_card:
                extra_cards += f"\n\n{cell_card}"

            axes = [('x', 0), ('y', 1), ('z', 2)]
            for axis_name, axis_idx in axes:
                for sign, label in [(-1.0, 'm'), (1.0, 'p')]:
                    disp_atoms = [dict(a) for a in atoms]
                    disp_atoms[h_idx][axis_name] += sign * delta

                    pos_lines = ["ATOMIC_POSITIONS (angstrom)"]
                    for a in disp_atoms:
                        pos_lines.append(f"{a['element']:<4} {a['x']:20.10f} {a['y']:20.10f} {a['z']:20.10f}")
                    pos_block = "\n".join(pos_lines)

                    full_pwinput = f"{template_clean}\n\n{pos_block}{extra_cards}\n"
                    
                    ext = ".in" if include_in_ext else ""
                    filename = f"PWINPUT_atm{h_idx + 1}_{axis_name}{label}{ext}"
                    files[f"{root}4-vibration/H/{filename}"] = full_pwinput

    summary = {
        "e_ads_ev": e_ads_ev,
        "e_h2_ev": e_h2_ev,
        "e_h2o_ev": e_h2o_ev
    }
    return build_zip_from_dict(files), summary, None

def process_tab2_vibrations(zip_bytes: bytes, delta: float = 0.015) -> tuple[bytes | None, list[float], float | None, str | None, bool]:
    """
    Parses vibrational logs or frequency calculations:
      - If valid LOG/output force files are detected: computes harmonic modes and ZPE.
      - If LOG files are NOT available: leaves the energy_ev cells in sheet 4-vibrasi EMPTY
        so the user can fill them manually.
    """
    files = extract_zip_to_dict(zip_bytes)

    excel_info = find_excel_file(files)
    if not excel_info:
        return None, [], None, "No Excel tracking sheet found in the uploaded zip.", False

    excel_path, excel_bytes = excel_info
    wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    surface_name = wb["1-adsorbate"].cell(row=2, column=1).value or "Surface"

    h_in_key = next((k for k in files if k.endswith("3-adsorption/H/PW.in")), None)
    h_idx = 1
    if h_in_key:
        _, atoms = parse_qe_atomic_positions(files[h_in_key].decode("utf-8", errors="ignore"))
        if atoms:
            h_idx = len(atoms)

    log_candidates = [
        k for k in files
        if '4-vibration/' in k and not k.endswith('/') and not os.path.basename(k).startswith('.')
    ]

    found_freqs = []
    for k in log_candidates:
        if k.endswith('.out') or 'LOG_' in k or 'vibr' in k.lower():
            content = files[k].decode("utf-8", errors="ignore")
            matches = re.findall(r'omega.*?=\s*(\d+\.\d+)\s*\[cm-1\]', content)
            if matches:
                found_freqs.extend([float(m) for m in matches])

    if not found_freqs:
        folder_candidates = [k for k in log_candidates if f"atm{h_idx}_" in k or f"atm{h_idx}" in k]
        if folder_candidates:
            H = np.zeros((3, 3))
            row_idx = 0
            has_all_forces = True

            for axis in 'xyz':
                fm_keys = [k for k in log_candidates if f"atm{h_idx}_{axis}m" in k]
                fp_keys = [k for k in log_candidates if f"atm{h_idx}_{axis}p" in k]

                if fm_keys and fp_keys:
                    content_m = files[fm_keys[0]].decode("utf-8", errors="ignore")
                    content_p = files[fp_keys[0]].decode("utf-8", errors="ignore")
                    fm_forces = _read_forces_from_log(content_m, h_idx)
                    fp_forces = _read_forces_from_log(content_p, h_idx)
                    
                    if np.any(fm_forces) or np.any(fp_forces):
                        H[row_idx] = 0.5 * (fm_forces - fp_forces) / (2.0 * delta)
                        row_idx += 1
                    else:
                        has_all_forces = False
                else:
                    has_all_forces = False

            if has_all_forces and row_idx == 3:
                H = 0.5 * (H + H.T)
                mass_h = 1.00794
                inv_m = mass_h ** -0.5
                omega2, _ = np.linalg.eigh(inv_m * H * inv_m)
                hnu = _S_FACTOR * omega2.astype(complex) ** 0.5
                found_freqs = [float(freq * 8065.544) for freq in hnu.real if freq > 0]

    if "4-vibrasi" not in wb.sheetnames:
        return None, [], None, "Sheet `4-vibrasi` not found in workbook.", False

    ws = wb["4-vibrasi"]

    if found_freqs:
        energies_ev = [0.5 * f * CM_TO_EV for f in found_freqs[:3]]
        total_zpe = sum(energies_ev)

        while ws.max_row > 1:
            ws.delete_rows(2)

        for i, e_val in enumerate(energies_ev):
            ws.append([surface_name, "H", round(e_val, 4), f"mode_{i+1}"])

        out_buf = io.BytesIO()
        wb.save(out_buf)
        files[excel_path] = out_buf.getvalue()

        return build_zip_from_dict(files), found_freqs[:3], total_zpe, None, True

    else:
        existing_has_values = False
        if ws.max_row > 1:
            for r in range(2, ws.max_row + 1):
                val = ws.cell(row=r, column=3).value
                if val is not None and isinstance(val, (int, float)):
                    existing_has_values = True
                    break

        if not existing_has_values:
            while ws.max_row > 1:
                ws.delete_rows(2)
            for i in range(3):
                ws.append([surface_name, "H", None, f"mode_{i+1}"])

        out_buf = io.BytesIO()
        wb.save(out_buf)
        files[excel_path] = out_buf.getvalue()

        return build_zip_from_dict(files), [], None, None, False
