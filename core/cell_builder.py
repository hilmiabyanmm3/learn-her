import re
import openpyxl
import io
from core.qe_parser import parse_qe_total_energy, parse_qe_atomic_positions

def extract_card(content: str, card_names: list) -> str:
    """Extracts a specific QE card and its data block from input content."""
    names_pattern = "|".join(card_names)
    known_cards = r'(?:ATOMIC_SPECIES|ATOMIC_POSITIONS|K_POINTS|KPOINTS|CELL_PARAMETERS|CONSTRAINTS|OCCUPATIONS|ATOMIC_VELOCITIES|ATOMIC_FORCES|HUBBARD|\&[A-Za-z]+)'
    pattern = rf'(?m)^\s*({names_pattern})\b[^\n]*(?:\n|$)(?:(?!^\s*{known_cards}\b).*(?:\n|$))*'
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return ""

def get_default_adsorption_height(intermediate: str) -> float:
    inter = intermediate.replace("*", "").strip().upper()
    heights = {
        "H": 1.0,
        "O": 1.2,
        "OH": 1.4,
        "OOH": 1.4,
        "H2O": 1.5,
        "O2": 1.4
    }
    return heights.get(inter, 1.2)

def build_adsorbate_system(
    files: dict, 
    selected_site_idx: int, 
    h_height: float = 1.0, 
    intermediate: str = "H"
) -> dict:
    """Constructs 3-adsorption/{intermediate}/PW.in using clean card decomposition.
    Supports H, O, OH, OOH, H2O, and O2 with realistic surface-adsorbate coordinates.
    """
    in_key = next(k for k in files if k.endswith("1-surface/PW.in"))
    out_key = next(k for k in files if k.endswith("1-surface/PW.out"))

    in_text = files[in_key].decode("utf-8", errors="ignore") if isinstance(files[in_key], bytes) else files[in_key]
    out_text = files[out_key].decode("utf-8", errors="ignore") if isinstance(files[out_key], bytes) else files[out_key]
    e_ry, e_ev = parse_qe_total_energy(out_text)

    _, atoms = parse_qe_atomic_positions(out_text)
    site_atom = atoms[selected_site_idx - 1]
    sx, sy, sz = site_atom["x"], site_atom["y"], site_atom["z"]

    inter_clean = intermediate.replace("*", "").strip().upper()
    added_atoms = []

    if inter_clean == "H":
        added_atoms.append({'element': 'H', 'x': sx, 'y': sy, 'z': sz + h_height})
    elif inter_clean == "O":
        added_atoms.append({'element': 'O', 'x': sx, 'y': sy, 'z': sz + h_height})
    elif inter_clean == "OH":
        added_atoms.append({'element': 'O', 'x': sx, 'y': sy, 'z': sz + h_height})
        added_atoms.append({'element': 'H', 'x': sx + 0.70, 'y': sy, 'z': sz + h_height + 0.65})
    elif inter_clean == "OOH":
        added_atoms.append({'element': 'O', 'x': sx, 'y': sy, 'z': sz + h_height})
        added_atoms.append({'element': 'O', 'x': sx + 1.20, 'y': sy, 'z': sz + h_height + 0.50})
        added_atoms.append({'element': 'H', 'x': sx + 1.70, 'y': sy, 'z': sz + h_height + 1.20})
    elif inter_clean in ["H2O", "H2O*"]:
        added_atoms.append({'element': 'O', 'x': sx, 'y': sy, 'z': sz + h_height})
        added_atoms.append({'element': 'H', 'x': sx + 0.70, 'y': sy, 'z': sz + h_height + 0.65})
        added_atoms.append({'element': 'H', 'x': sx - 0.70, 'y': sy, 'z': sz + h_height + 0.65})
    elif inter_clean in ["O2", "O2*"]:
        added_atoms.append({'element': 'O', 'x': sx, 'y': sy, 'z': sz + h_height})
        added_atoms.append({'element': 'O', 'x': sx + 1.21, 'y': sy, 'z': sz + h_height + 0.35})
    else:
        added_atoms.append({'element': 'H', 'x': sx, 'y': sy, 'z': sz + h_height})

    num_added = len(added_atoms)

    # 1. Update nat in &SYSTEM
    nat_match = re.search(r"nat\s*=\s*(\d+)", in_text, re.IGNORECASE)
    if nat_match:
        old_nat = int(nat_match.group(1))
        in_text = re.sub(r"nat\s*=\s*\d+", f"nat = {old_nat + num_added}", in_text, count=1)

    # 2. Append elements to ATOMIC_SPECIES if missing
    pseudo_map = {
        'H': '1.00794 h_pbe_v1.4.uspp.F.UPF',
        'O': '15.9994 o_pbe_v1.2.uspp.F.UPF'
    }
    for a in added_atoms:
        elem = a['element']
        has_elem = re.search(rf"ATOMIC_SPECIES[\s\S]*?\b{elem}\b", in_text, re.IGNORECASE)
        if not has_elem:
            ntyp_match = re.search(r"ntyp\s*=\s*(\d+)", in_text, re.IGNORECASE)
            if ntyp_match:
                old_ntyp = int(ntyp_match.group(1))
                in_text = re.sub(r"ntyp\s*=\s*\d+", f"ntyp = {old_ntyp + 1}", in_text, count=1)

            species_pattern = re.compile(r"(ATOMIC_SPECIES[\s\S]*?)(^\s*\n|^[A-Z_]+)", re.MULTILINE)
            pseudo_line = f"{elem}   {pseudo_map.get(elem, '1.000 element.UPF')}"
            if species_pattern.search(in_text):
                in_text = species_pattern.sub(rf"\g<1>{pseudo_line}\n\g<2>", in_text, count=1)
            else:
                in_text += f"\nATOMIC_SPECIES\n{pseudo_line}\n"

    # 3. Clean Card Decomposition
    template_clean = re.split(r'ATOMIC_POSITIONS', in_text, flags=re.IGNORECASE)[0].strip()
    kpoints_card = extract_card(in_text, ['K_POINTS', 'KPOINTS'])
    cell_card = extract_card(in_text, ['CELL_PARAMETERS'])
    extra_cards = ""
    if kpoints_card:
        extra_cards += f"\n\n{kpoints_card}"
    if cell_card:
        extra_cards += f"\n\n{cell_card}"

    # 4. Construct ATOMIC_POSITIONS block
    pos_lines = ["ATOMIC_POSITIONS (angstrom)"]
    for a in atoms:
        pos_lines.append(f"{a['element']:<4} {a['x']:20.10f} {a['y']:20.10f} {a['z']:20.10f}")
    for a in added_atoms:
        pos_lines.append(f"{a['element']:<4} {a['x']:20.10f} {a['y']:20.10f} {a['z']:20.10f}")
    pos_block = "\n".join(pos_lines)

    clean_pw_in = f"{template_clean}\n\n{pos_block}{extra_cards}\n"

    target_inter_dir = "H" if inter_clean == "H" else inter_clean
    root_match = re.match(r"^([^/]+)/", in_key)
    root = f"{root_match.group(1)}/" if root_match else ""
    files[f"{root}3-adsorption/{target_inter_dir}/PW.in"] = clean_pw_in

    return files

def build_all_adsorbate_systems(files: dict, selected_site_idx: int, intermediates: list) -> dict:
    """Constructs 3-adsorption/{inter}/PW.in for all intermediates in a single batch."""
    for inter in intermediates:
        h = get_default_adsorption_height(inter)
        files = build_adsorbate_system(files, selected_site_idx, h_height=h, intermediate=inter)
    return files
