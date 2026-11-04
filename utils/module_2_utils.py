import io
import re
import openpyxl
from utils.common import extract_zip_to_dict, build_zip_from_dict, find_excel_file
from utils.qe_parser import parse_qe_total_energy, parse_qe_atomic_positions, filter_topmost_active_sites

def extract_card(content: str, card_names: list) -> str:
    """Extracts a specific QE card and its data block from input content."""
    names_pattern = "|".join(card_names)
    known_cards = r'(?:ATOMIC_SPECIES|ATOMIC_POSITIONS|K_POINTS|KPOINTS|CELL_PARAMETERS|CONSTRAINTS|OCCUPATIONS|ATOMIC_VELOCITIES|ATOMIC_FORCES|HUBBARD|\&[A-Za-z]+)'
    pattern = rf'(?m)^\s*({names_pattern})\b[^\n]*(?:\n|$)(?:(?!^\s*{known_cards}\b).*(?:\n|$))*'
    match = re.search(pattern, content, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    return ""

def inspect_surface_zip(zip_bytes: bytes) -> tuple[dict | None, str | None]:
    """Inspects the uploaded workspace ZIP containing relaxed 1-surface/PW.in and PW.out."""
    files = extract_zip_to_dict(zip_bytes)

    in_key = next((k for k in files if k.endswith("1-surface/PW.in")), None)
    out_key = next((k for k in files if k.endswith("1-surface/PW.out")), None)

    if not in_key or not out_key:
        return None, "Missing `1-surface/PW.in` or `1-surface/PW.out` in the uploaded zip file."

    out_content = files[out_key].decode("utf-8", errors="ignore")
    e_ry, e_ev = parse_qe_total_energy(out_content)
    unit, atoms = parse_qe_atomic_positions(out_content)
    sites = filter_topmost_active_sites(atoms)

    if not atoms:
        return None, "Could not parse relaxed atomic coordinates from `1-surface/PW.out`."

    return {
        "e_ry": e_ry,
        "e_ev": e_ev,
        "atoms": atoms,
        "sites": sites,
        "files": files
    }, None

def build_adsorbate_system(files: dict, selected_site_idx: int, h_height: float = 1.0) -> bytes:
    """
    Constructs 3-adsorption/H/PW.in using clean card decomposition.
    Completely eliminates any possibility of duplicate atomic coordinates.
    """
    in_key = next(k for k in files if k.endswith("1-surface/PW.in"))
    out_key = next(k for k in files if k.endswith("1-surface/PW.out"))

    in_text = files[in_key].decode("utf-8", errors="ignore")
    out_text = files[out_key].decode("utf-8", errors="ignore")
    e_ry, e_ev = parse_qe_total_energy(out_text)

    # Read the FINAL relaxed geometry from PW.out
    _, atoms = parse_qe_atomic_positions(out_text)

    # Target active site coordinates
    site_atom = atoms[selected_site_idx - 1]
    h_x = site_atom["x"]
    h_y = site_atom["y"]
    h_z = site_atom["z"] + h_height

    # 1. Update nat (number of atoms) in &SYSTEM
    nat_match = re.search(r"nat\s*=\s*(\d+)", in_text, re.IGNORECASE)
    if nat_match:
        old_nat = int(nat_match.group(1))
        in_text = re.sub(r"nat\s*=\s*\d+", f"nat = {old_nat + 1}", in_text, count=1)

    # 2. Check ntyp and append H to ATOMIC_SPECIES if missing
    has_h_species = re.search(r"ATOMIC_SPECIES[\s\S]*?\bH\b", in_text, re.IGNORECASE)
    if not has_h_species:
        ntyp_match = re.search(r"ntyp\s*=\s*(\d+)", in_text, re.IGNORECASE)
        if ntyp_match:
            old_ntyp = int(ntyp_match.group(1))
            in_text = re.sub(r"ntyp\s*=\s*\d+", f"ntyp = {old_ntyp + 1}", in_text, count=1)

        species_pattern = re.compile(r"(ATOMIC_SPECIES[\s\S]*?)(^\s*\n|^[A-Z_]+)", re.MULTILINE)
        if species_pattern.search(in_text):
            in_text = species_pattern.sub(r"\g<1>H   1.00794 h_pbe_v1.4.uspp.F.UPF\n\g<2>", in_text, count=1)
        else:
            in_text += "\nATOMIC_SPECIES\nH   1.00794 h_pbe_v1.4.uspp.F.UPF\n"

    # 3. Clean Card Decomposition
    template_clean = re.split(r'ATOMIC_POSITIONS', in_text, flags=re.IGNORECASE)[0].strip()

    kpoints_card = extract_card(in_text, ['K_POINTS', 'KPOINTS'])
    cell_card = extract_card(in_text, ['CELL_PARAMETERS'])
    extra_cards = ""
    if kpoints_card:
        extra_cards += f"\n\n{kpoints_card}"
    if cell_card:
        extra_cards += f"\n\n{cell_card}"

    # 4. Construct the clean new ATOMIC_POSITIONS block
    pos_lines = ["ATOMIC_POSITIONS (angstrom)"]
    for a in atoms:
        pos_lines.append(f"{a['element']:<4} {a['x']:20.10f} {a['y']:20.10f} {a['z']:20.10f}")
    pos_lines.append(f"{'H':<4} {h_x:20.10f} {h_y:20.10f} {h_z:20.10f}")
    pos_block = "\n".join(pos_lines)

    clean_pw_in = f"{template_clean}\n\n{pos_block}{extra_cards}\n"

    root_match = re.match(r"^([^/]+)/", in_key)
    root = f"{root_match.group(1)}/" if root_match else ""
    files[f"{root}3-adsorption/H/PW.in"] = clean_pw_in

    # Update clean slab energy in the Excel sheet
    excel_info = find_excel_file(files)
    if excel_info and e_ry is not None:
        excel_path, excel_bytes = excel_info
        wb = openpyxl.load_workbook(io.BytesIO(excel_bytes))
        if "1-adsorbate" in wb.sheetnames:
            ws = wb["1-adsorbate"]
            ws.cell(row=2, column=2, value=e_ry)
            ws.cell(row=2, column=3, value="='1-adsorbate'!B2*13.605698066")
        out_buf = io.BytesIO()
        wb.save(out_buf)
        files[excel_path] = out_buf.getvalue()

    return build_zip_from_dict(files)
