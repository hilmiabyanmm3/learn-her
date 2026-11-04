import io
import os
import openpyxl
from utils.common import build_zip_from_dict

# Standard column headers across all 5 sheets
SHEET_HEADERS = {
    "1-adsorbate": ["surface", "e-tot-surface-energy_ry", "e-tot-surface-energy-ev", "adsorbate_h_ry", "adsorbate_h_ev"],
    "2-isolated-mol": ["isolated_mol", "e_tot", "zpe", "ts"],
    "3-ads-energy": ["surface", "eads_h_ev"],
    "4-vibrasi": ["surface", "adsorbate", "energy_ev", "vib_mode"],
    "5-gibbs": ["surface", "adsorbate", "e_g_1"]
}

def _resolve_asset_path(base_dir: str, target_filename: str) -> str:
    """Resolves asset file paths robustly on macOS and Linux, handling case-sensitivity."""
    candidate = os.path.join(base_dir, target_filename)
    if os.path.exists(candidate):
        return candidate
    if os.path.exists(base_dir):
        for fname in os.listdir(base_dir):
            if fname.lower() == target_filename.lower():
                return os.path.join(base_dir, fname)
    return candidate

def generate_module_1_workspace(surface_name: str, reaction: str = "HER") -> bytes:
    """Generates the initial project workspace zip with folder templates and renamed data sheet."""
    clean_surface = surface_name.strip()
    root = f"{clean_surface}/"
    files = {}

    current_dir = os.path.dirname(os.path.realpath(__file__))
    assets_dir = os.path.abspath(os.path.join(current_dir, "..", "assets"))

    h2_path = _resolve_asset_path(assets_dir, "c-isolated_h2.in")
    h2o_path = _resolve_asset_path(assets_dir, "c-isolated_h2o.in")
    excel_tmpl_path = _resolve_asset_path(assets_dir, "d-her_data_sheet.xlsx")

    h2_content = open(h2_path, "r").read() if os.path.exists(h2_path) else "&CONTROL\n/\n"
    h2o_content = open(h2o_path, "r").read() if os.path.exists(h2o_path) else "&CONTROL\n/\n"

    # Strict hierarchy
    files[f"{root}1-surface/.keep"] = ""
    files[f"{root}2-isolated-gas/H2/PW.in"] = h2_content
    files[f"{root}2-isolated-gas/H2O/PW.in"] = h2o_content
    files[f"{root}3-adsorption/H/.keep"] = ""
    files[f"{root}4-vibration/H/.keep"] = ""
    files[f"{root}5-data-visual/.keep"] = ""

    # Load template or construct workbook with guaranteed headers
    if os.path.exists(excel_tmpl_path):
        wb = openpyxl.load_workbook(excel_tmpl_path)
    else:
        wb = openpyxl.Workbook()
        default_sheet = wb.active
        for s_name, headers in SHEET_HEADERS.items():
            ws = wb.create_sheet(title=s_name)
            ws.append(headers)
        if default_sheet and "Sheet" in wb.sheetnames:
            wb.remove(default_sheet)

    if "1-adsorbate" in wb.sheetnames:
        wb["1-adsorbate"].cell(row=2, column=1, value=clean_surface)
        
    if "2-isolated-mol" in wb.sheetnames:
        ws2 = wb["2-isolated-mol"]
        if ws2.max_row < 2:
            ws2.append(["H2", -31.7452, 0.2720, 0.4040])
            ws2.append(["H2O", -467.2185, 0.5600, 0.6700])
            
    if "3-ads-energy" in wb.sheetnames:
        wb["3-ads-energy"].cell(row=2, column=1, value=clean_surface)
        
    if "5-gibbs" in wb.sheetnames:
        wb["5-gibbs"].cell(row=2, column=1, value=clean_surface)
        wb["5-gibbs"].cell(row=2, column=2, value="H")

    excel_buf = io.BytesIO()
    wb.save(excel_buf)
    files[f"{root}{clean_surface}_her_data_sheet.xlsx"] = excel_buf.getvalue()

    return build_zip_from_dict(files)
