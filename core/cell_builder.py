import re
import numpy as np
from core.qe_parser import parse_qe_atomic_positions, parse_qe_cell_parameters

ADSORBATE_GEOMETRIES = {
    "H": [
        ("H", np.array([0.0, 0.0, 0.0]))
    ],
    "O": [
        ("O", np.array([0.0, 0.0, 0.0]))
    ],
    "OH": [
        ("O", np.array([0.0, 0.0, 0.0])),
        ("H", np.array([0.78, 0.0, 0.58]))
    ],
    "OOH": [
        ("O", np.array([0.0, 0.0, 0.0])),
        ("O", np.array([1.22, 0.0, 0.72])),
        ("H", np.array([1.22, 0.78, 1.30]))
    ],
    "H2O": [
        ("O", np.array([0.0, 0.0, 0.0])),
        ("H", np.array([0.76, 0.0, 0.59])),
        ("H", np.array([-0.76, 0.0, 0.59]))
    ],
    "O2": [
        ("O", np.array([0.0, 0.0, 0.0])),
        ("O", np.array([1.21, 0.0, 0.15]))
    ]
}

DEFAULT_HEIGHTS = {
    "H": 1.0,
    "O": 1.2,
    "OH": 1.4,
    "OOH": 1.4,
    "H2O": 1.5,
    "O2": 1.4
}

PSEUDO_DEFAULTS = {
    "H": ("1.00794", "h_pbe_v1.4.uspp.F.UPF"),
    "O": ("15.9994", "o_pbe_v1.2.uspp.F.UPF"),
    "N": ("14.0067", "n_pbe_v1.2.uspp.F.UPF"),
    "C": ("12.0110", "c_pbe_v1.2.uspp.F.UPF"),
}

def extract_card(content: str, card_names: list[str]) -> str | None:
    """Extracts a complete QE card block (e.g. K_POINTS or CELL_PARAMETERS) from input text."""
    lines = content.splitlines()
    target_set = {c.upper() for c in card_names}
    all_cards = {
        "ATOMIC_SPECIES", "ATOMIC_POSITIONS", "K_POINTS", "KPOINTS",
        "CELL_PARAMETERS", "CONSTRAINTS", "OCCUPATIONS", "ATOMIC_FORCES"
    }

    start_idx = -1
    for i, line in enumerate(lines):
        first_tok = line.strip().split()[0].upper() if line.strip() else ""
        if first_tok in target_set:
            start_idx = i
            break

    if start_idx == -1:
        return None

    collected = [lines[start_idx]]
    for j in range(start_idx + 1, len(lines)):
        stripped = lines[j].strip()
        if not stripped:
            if len(collected) > 1:
                break
            continue
        first_tok = stripped.split()[0].upper()
        if first_tok in all_cards or stripped.startswith("&") or stripped == "/":
            break
        collected.append(lines[j])

    return "\n".join(collected)


def _build_single_pw_input(
    in_text: str,
    out_text: str,
    site_index_1based: int,
    adsorption_height: float,
    intermediate: str
) -> str:
    """Constructs a clean Quantum ESPRESSO PW.in for slab + adsorbate at chosen site."""
    inter_clean = intermediate.replace("*", "").strip().upper()
    rel_atoms = ADSORBATE_GEOMETRIES.get(inter_clean, [("H", np.array([0.0, 0.0, 0.0]))])

    _, slab_atoms = parse_qe_atomic_positions(out_text)
    if not slab_atoms:
        _, slab_atoms = parse_qe_atomic_positions(in_text)
    if not slab_atoms:
        return in_text

    site_idx = max(0, min(len(slab_atoms) - 1, site_index_1based - 1))
    anchor = np.array([
        slab_atoms[site_idx]["x"],
        slab_atoms[site_idx]["y"],
        slab_atoms[site_idx]["z"] + adsorption_height
    ], dtype=float)

    combined_atoms = [dict(a) for a in slab_atoms]
    for elem, offset in rel_atoms:
        pos = anchor + offset
        combined_atoms.append({
            "element": elem,
            "raw_label": elem,
            "x": float(pos[0]),
            "y": float(pos[1]),
            "z": float(pos[2]),
            "flags": ["1", "1", "1"]
        })

    # Parse existing ATOMIC_SPECIES from PW.in
    species_lines = []
    existing_species = set()
    lines = in_text.splitlines()
    in_species = False
    all_cards = {
        "ATOMIC_POSITIONS", "K_POINTS", "KPOINTS",
        "CELL_PARAMETERS", "CONSTRAINTS", "OCCUPATIONS", "ATOMIC_FORCES"
    }
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        tok = stripped.split()[0].upper()
        if tok == "ATOMIC_SPECIES":
            in_species = True
            continue
        if in_species:
            if tok in all_cards or stripped.startswith("&") or stripped == "/":
                break
            parts = stripped.split()
            if len(parts) >= 3:
                sym = re.sub(r"[^A-Za-z]", "", parts[0]).capitalize()
                existing_species.add(sym.upper())
                species_lines.append(f"{parts[0]:<5} {parts[1]:<10} {parts[2]}")

    for atom in combined_atoms:
        sym = atom["element"].upper()
        if sym not in existing_species:
            mass, pp = PSEUDO_DEFAULTS.get(sym, ("1.00794", f"{sym.lower()}_pbe_v1.4.uspp.F.UPF"))
            species_lines.append(f"{atom['element']:<5} {mass:<10} {pp}")
            existing_species.add(sym)

    new_nat = len(combined_atoms)
    new_ntyp = len(existing_species)

    header_part = re.split(r"ATOMIC_SPECIES|ATOMIC_POSITIONS", in_text, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    header_part = re.sub(r"(?i)(\bnat\s*=\s*)\d+", rf"\g<1>{new_nat}", header_part)
    header_part = re.sub(r"(?i)(\bntyp\s*=\s*)\d+", rf"\g<1>{new_ntyp}", header_part)

    species_block = "ATOMIC_SPECIES\n" + "\n".join(species_lines)

    pos_lines = ["ATOMIC_POSITIONS (angstrom)"]
    for a in combined_atoms:
        flags_str = " ".join(a.get("flags", ["1", "1", "1"])[:3])
        pos_lines.append(f"{a['element']:<4} {a['x']:18.10f} {a['y']:18.10f} {a['z']:18.10f}  {flags_str}")
    pos_block = "\n".join(pos_lines)

    kpoints_card = extract_card(in_text, ["K_POINTS", "KPOINTS"]) or "K_POINTS automatic\n  4 4 1 0 0 0"
    cell_card = extract_card(out_text, ["CELL_PARAMETERS"]) or extract_card(in_text, ["CELL_PARAMETERS"])

    sections = [header_part, species_block, pos_block, kpoints_card]
    if cell_card:
        sections.append(cell_card)

    return "\n\n".join(sections) + "\n"


def build_adsorbate_system(
    files: dict,
    site_index_1based: int,
    adsorption_height: float = 1.0,
    intermediate: str = "H"
) -> dict:
    """Generates 3-adsorption/<intermediate>/PW.in inside the project dictionary."""
    in_key = next((k for k in files if k.endswith("1-surface/PW.in")), None)
    out_key = next((k for k in files if k.endswith("1-surface/PW.out")), None)
    if not in_key or not out_key:
        return files

    in_text = files[in_key].decode("utf-8", errors="ignore") if isinstance(files[in_key], bytes) else files[in_key]
    out_text = files[out_key].decode("utf-8", errors="ignore") if isinstance(files[out_key], bytes) else files[out_key]

    root_match = re.match(r"^([^/]+)/", in_key)
    root = f"{root_match.group(1)}/" if root_match else ""
    inter_clean = intermediate.replace("*", "").strip()

    pw_in = _build_single_pw_input(in_text, out_text, site_index_1based, adsorption_height, inter_clean)
    files[f"{root}3-adsorption/{inter_clean}/PW.in"] = pw_in
    return files


def build_all_adsorbate_systems(
    files: dict,
    site_index_1based: int,
    intermediates: list[str],
    heights_map: dict[str, float] | None = None
) -> dict:
    """Batch generates 3-adsorption/<intermediate>/PW.in for every intermediate using user-defined or default lengths."""
    for inter in intermediates:
        inter_clean = inter.replace("*", "").strip()
        if heights_map and inter_clean.upper() in heights_map:
            h_val = float(heights_map[inter_clean.upper()])
        else:
            h_val = DEFAULT_HEIGHTS.get(inter_clean.upper(), 1.4)
        files = build_adsorbate_system(files, site_index_1based, h_val, inter_clean)
    return files
