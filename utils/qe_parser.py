import re
import numpy as np
from utils.common import RY_TO_EV

BOHR_TO_ANGSTROM = 0.529177210903

def parse_qe_total_energy(content: str) -> tuple[float | None, float | None]:
    """Extracts the final converged total energy from a QE relax or scf output file."""
    matches = re.findall(r'!\s+total energy\s*=\s*([-+]?\d+\.\d+)\s+Ry', content)
    if matches:
        e_ry = float(matches[-1])  # Takes the last step from relaxation
        return e_ry, e_ry * RY_TO_EV
    return None, None

def parse_qe_cell_parameters(content: str) -> tuple[str, np.ndarray | None]:
    """Parses the latest CELL_PARAMETERS from a QE input or relax output file."""
    blocks = re.split(r'CELL_PARAMETERS\s*[\({]?([a-zA-Z0-9_=]+)?[\)}]?', content, flags=re.IGNORECASE)
    if len(blocks) < 3:
        return "angstrom", None
    
    unit_str = blocks[-2].strip().lower() if blocks[-2] else "angstrom"
    lines = blocks[-1].strip().split('\n')
    
    cell_rows = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                cell_rows.append([float(parts[0]), float(parts[1]), float(parts[2])])
                if len(cell_rows) == 3:
                    break
            except ValueError:
                continue

    if len(cell_rows) == 3:
        cell_matrix = np.array(cell_rows, dtype=float)
        if "bohr" in unit_str or "au" in unit_str:
            cell_matrix *= BOHR_TO_ANGSTROM
        return unit_str, cell_matrix
    return unit_str, None

def parse_qe_atomic_positions(content: str) -> tuple[str, list[dict]]:
    """
    Extracts the final relaxed atomic positions from a QE 'relax' calculation.
    Handles:
    1. 'Begin final coordinates' block if present in PW.out.
    2. Takes the LAST ATOMIC_POSITIONS block if multiple steps are printed.
    3. Crystal fractional coordinate conversion to Cartesian (Angstrom).
    4. Stripping numeric indices (e.g., Sc1, Sc2 -> Sc).
    5. Preserves selective dynamics flags (e.g., 1 1 1).
    """
    target_text = content
    final_coord_match = re.search(
        r'Begin final coordinates[\s\S]*?End final coordinates',
        content,
        re.IGNORECASE
    )
    if final_coord_match:
        target_text = final_coord_match.group(0)

    blocks = re.split(r'ATOMIC_POSITIONS\s*[\({]?([a-zA-Z]+)?[\)}]?', target_text, flags=re.IGNORECASE)
    if len(blocks) < 3:
        blocks = re.split(r'ATOMIC_POSITIONS\s*[\({]?([a-zA-Z]+)?[\)}]?', content, flags=re.IGNORECASE)
        if len(blocks) < 3:
            return "angstrom", []

    unit = blocks[-2].strip().lower() if blocks[-2] else "angstrom"
    body = blocks[-1].strip().split('\n')

    raw_atoms = []
    for line in body:
        line = line.strip()
        if not line or any(keyword in line.upper() for keyword in [
            'K_POINTS', 'CELL_PARAMETERS', 'TOTAL', 'FORCES', 'END', 'JOB', '!', 'BEGIN'
        ]):
            if raw_atoms:
                break
            continue

        parts = line.split()
        if len(parts) >= 4:
            raw_elem = parts[0]
            elem_match = re.match(r'^[A-Za-z]+', raw_elem)
            clean_elem = elem_match.group(0).capitalize() if elem_match else raw_elem

            try:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                flags = parts[4:7] if len(parts) >= 7 else ['1', '1', '1']
                raw_atoms.append({
                    'element': clean_elem,
                    'raw_label': raw_elem,
                    'x': x,
                    'y': y,
                    'z': z,
                    'flags': flags
                })
            except ValueError:
                continue

    if not raw_atoms:
        return "angstrom", []

    # If positions are in crystal coordinates, convert to Cartesian Angstrom
    if "crystal" in unit:
        _, cell = parse_qe_cell_parameters(content)
        if cell is not None:
            converted_atoms = []
            for atom in raw_atoms:
                cart_pos = np.dot([atom['x'], atom['y'], atom['z']], cell)
                atom['x'], atom['y'], atom['z'] = float(cart_pos[0]), float(cart_pos[1]), float(cart_pos[2])
                converted_atoms.append(atom)
            return "angstrom", converted_atoms

    return unit, raw_atoms

def filter_topmost_active_sites(atoms: list[dict], threshold_z: float = 1.8) -> list[dict]:
    """
    Identifies candidate catalytic sites in the surface layer.
    threshold_z = 1.8 Å ensures 3d metal cations below lighter surface anions (O, S, C) are included.
    """
    if not atoms:
        return []

    max_z = max(a['z'] for a in atoms)

    active_elems = {
        # --- Complete 3d Transition Metal Series (Sc to Zn) ---
        'SC', 'TI', 'V', 'CR', 'MN', 'FE', 'CO', 'NI', 'CU', 'ZN',

        # --- 4d Transition Metals ---
        'Y', 'ZR', 'NB', 'MO', 'TC', 'RU', 'RH', 'PD', 'AG', 'CD',

        # --- 5d Transition Metals ---
        'HF', 'TA', 'W', 'RE', 'OS', 'IR', 'PT', 'AU',

        # --- Post-Transition Metals & Metalloids ---
        'AL', 'GA', 'IN', 'SN', 'PB', 'BI', 'SB',

        # --- Non-metal Active Centers / Dopants ---
        'B', 'C', 'N', 'P', 'S', 'SE', 'TE'
    }

    sites = []
    for i, a in enumerate(atoms):
        is_top = (a['z'] >= (max_z - threshold_z))
        clean_symbol = re.sub(r'[^A-Za-z]', '', a['element']).upper()
        is_active = clean_symbol in active_elems

        if is_top and is_active:
            sites.append({
                'index': i + 1,
                'element': a['element'],
                'raw_label': a.get('raw_label', a['element']),
                'x': a['x'],
                'y': a['y'],
                'z': a['z']
            })
    return sites
