import io
import os
import re
import openpyxl
import zipfile
from typing import Dict, Any, Tuple
from core.qe_parser import RY_TO_EV

def extract_zip_to_dict(zip_bytes: bytes) -> dict[str, bytes]:
    files = {}
    with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
        for name in zf.namelist():
            if not name.endswith('/'):
                files[name] = zf.read(name)
    return files

def build_zip_from_dict(file_dict: dict[str, bytes | str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for path, content in file_dict.items():
            if isinstance(content, str):
                zf.writestr(path, content.encode('utf-8'))
            else:
                zf.writestr(path, content)
    buffer.seek(0)
    return buffer.getvalue()

def find_excel_file(files: dict[str, bytes]) -> tuple[str, bytes] | None:
    """Locates the canonical project Excel spreadsheet in the files map.
    Recognizes `<SurfaceName>_her_data_sheet.xlsx` or `<SurfaceName>_oer_data_sheet.xlsx`.
    Purges any duplicate or secondary spreadsheets.
    """
    xlsx_keys = [
        p for p in list(files.keys())
        if p.endswith(('.xlsx', '.xlsm')) and not os.path.basename(p).startswith('~$')
    ]
    if not xlsx_keys:
        return None

    canonical_key = next((p for p in xlsx_keys if '_oer_data_sheet' in p.lower() or '_her_data_sheet' in p.lower()), None)
    if not canonical_key:
        canonical_key = next((p for p in xlsx_keys if 'oer' in p.lower() or 'her' in p.lower()), None)
    if not canonical_key:
        canonical_key = next((p for p in xlsx_keys if 'data_sheet' in p.lower()), xlsx_keys[0])

    for p in xlsx_keys:
        if p != canonical_key and p in files:
            del files[p]

    return canonical_key, files[canonical_key]

def detect_reaction_type(files: dict[str, bytes], wb: openpyxl.Workbook = None) -> str:
    """Robustly detects whether an archive or workbook belongs to OER, ORR, or HER."""
    for p in files.keys():
        p_lower = p.lower()
        if p_lower.endswith(('.xlsx', '.xlsm')) and not os.path.basename(p_lower).startswith('~$'):
            if re.search(r'(^|[^a-z0-9])oer([^a-z0-9]|$)', p_lower):
                return "OER"
            if re.search(r'(^|[^a-z0-9])orr([^a-z0-9]|$)', p_lower):
                return "ORR"
            if re.search(r'(^|[^a-z0-9])her([^a-z0-9]|$)', p_lower):
                return "HER"

    target_wb = wb
    if target_wb is None:
        excel_info = find_excel_file(files)
        if excel_info:
            try:
                target_wb = openpyxl.load_workbook(io.BytesIO(excel_info[1]), read_only=True)
            except Exception:
                target_wb = None

    if target_wb is not None:
        sheet_names = [s.lower() for s in target_wb.sheetnames]
        if "5-gibbs-steps" in sheet_names or "1-adsorbates" in sheet_names:
            return "OER"
        if "3-ads-energy" in sheet_names and any("oh" in s for s in sheet_names):
            return "OER"
        if "5-gibbs" in sheet_names or "1-adsorbate" in sheet_names:
            return "HER"

    for p in files.keys():
        p_lower = p.lower()
        if any(seg in p_lower for seg in ["3-adsorption/oh/", "3-adsorption/o/", "3-adsorption/ooh/", "3-adsorption/o2/", "4-vibration/oh/"]):
            return "OER"
        if "3-adsorption/h/" in p_lower or "4-vibration/h/" in p_lower:
            return "HER"

    return "HER"

def extract_thermochem_robust(wb: openpyxl.Workbook, reaction_name: str = "HER") -> Dict[str, Any]:
    """Reads thermodynamics from openpyxl workbook and validates that required isolated-mol and slab data exist."""
    if reaction_name == "OER" or "5-gibbs-steps" in wb.sheetnames:
        return _extract_oer_robust(wb)
    return _extract_her_robust(wb)

def _extract_her_robust(wb: openpyxl.Workbook) -> Dict[str, Any]:
    surface_name = "Surface"
    delta_e, delta_g = None, None

    if "1-adsorbate" in wb.sheetnames:
        surface_name = wb["1-adsorbate"].cell(row=2, column=1).value or surface_name

    if "3-ads-energy" in wb.sheetnames:
        val_e = wb["3-ads-energy"].cell(row=2, column=2).value
        if isinstance(val_e, (int, float)):
            delta_e = float(val_e)

    if "5-gibbs" in wb.sheetnames:
        val_g = wb["5-gibbs"].cell(row=2, column=3).value
        if isinstance(val_g, (int, float)):
            delta_g = float(val_g)

    if delta_e is not None and delta_g is not None:
        return {
            "surface": surface_name,
            "delta_e": delta_e,
            "delta_g": delta_g,
            "delta_zpe": 0.0,
            "t_delta_s": -0.2020
        }

    ws1 = wb["1-adsorbate"] if "1-adsorbate" in wb.sheetnames else None
    ws2 = wb["2-isolated-mol"] if "2-isolated-mol" in wb.sheetnames else None
    ws4 = wb["4-vibrasi"] if "4-vibrasi" in wb.sheetnames else None

    if ws2 is None:
        raise ValueError("Missing sheet '2-isolated-mol' in workbook. Please complete isolated gas data before continuing.")

    e_h2 = None
    zpe_h2 = 0.2720
    ts_h2 = 0.4040
    for r in range(2, ws2.max_row + 1):
        mol = str(ws2.cell(row=r, column=1).value or "").strip().lower()
        if "h2" in mol and "h2o" not in mol:
            val_e = ws2.cell(row=r, column=2).value
            if isinstance(val_e, (int, float)):
                e_h2 = float(val_e)
            val_zpe = ws2.cell(row=r, column=3).value
            val_ts = ws2.cell(row=r, column=4).value
            if isinstance(val_zpe, (int, float)):
                zpe_h2 = float(val_zpe)
            if isinstance(val_ts, (int, float)):
                ts_h2 = float(val_ts)

    if e_h2 is None:
        raise ValueError(
            "Missing isolated gas energy for H2 in sheet '2-isolated-mol'. "
            "Please provide 2-isolated-gas/H2/PW.out in Module 3 or fill '2-isolated-mol' in the Excel sheet before continuing."
        )

    if ws1 is None:
        raise ValueError("Missing sheet '1-adsorbate' in workbook. Please complete surface and adsorbate calculations before continuing.")

    e_surf_ry = ws1.cell(row=2, column=2).value
    e_ads_ry = ws1.cell(row=2, column=4).value
    e_surf_ev_cell = ws1.cell(row=2, column=3).value
    e_ads_ev_cell = ws1.cell(row=2, column=5).value

    e_surf_ev = float(e_surf_ev_cell) if isinstance(e_surf_ev_cell, (int, float)) else (
        float(e_surf_ry) * RY_TO_EV if isinstance(e_surf_ry, (int, float)) else None
    )
    e_ads_ev = float(e_ads_ev_cell) if isinstance(e_ads_ev_cell, (int, float)) else (
        float(e_ads_ry) * RY_TO_EV if isinstance(e_ads_ry, (int, float)) else None
    )

    if e_surf_ev is None or e_ads_ev is None:
        raise ValueError(
            "Missing clean surface or H* adsorbate total energy in sheet '1-adsorbate'. "
            "Please complete Modules 2 and 3 before continuing."
        )

    calc_de = e_ads_ev - e_surf_ev - 0.5 * e_h2

    zpe_h = 0.0
    if ws4 is not None:
        zpe_h = sum(
            float(ws4.cell(row=r, column=3).value)
            for r in range(2, ws4.max_row + 1)
            if isinstance(ws4.cell(row=r, column=3).value, (int, float))
        )
    delta_zpe = zpe_h - 0.5 * zpe_h2
    calc_dg = calc_de + delta_zpe + 0.5 * ts_h2

    return {
        "surface": surface_name,
        "delta_e": delta_e if delta_e is not None else calc_de,
        "delta_g": delta_g if delta_g is not None else calc_dg,
        "delta_zpe": delta_zpe,
        "t_delta_s": -0.5 * ts_h2
    }

def _extract_oer_robust(wb: openpyxl.Workbook) -> Dict[str, Any]:
    surface_name = "Surface"
    if "1-adsorbates" in wb.sheetnames:
        s_val = wb["1-adsorbates"].cell(row=2, column=1).value
        if s_val and str(s_val).strip() not in ["<surface>", "Surface", ""]:
            surface_name = str(s_val).strip()
    elif "5-gibbs-steps" in wb.sheetnames:
        s_val = wb["5-gibbs-steps"].cell(row=2, column=1).value
        if s_val and str(s_val).strip() not in ["<surface>", "Surface", ""]:
            surface_name = str(s_val).strip()

    ws1 = wb["1-adsorbates"] if "1-adsorbates" in wb.sheetnames else None
    ws2 = wb["2-isolated-mol"] if "2-isolated-mol" in wb.sheetnames else None
    ws3 = wb["3-ads-energy"] if "3-ads-energy" in wb.sheetnames else None
    ws4 = wb["4-vibrasi"] if "4-vibrasi" in wb.sheetnames else None

    eads_h2o, eads_oh, eads_o, eads_ooh, eads_o2 = None, None, None, None, None

    # 1. Attempt reading cached numeric values from sheet 3-ads-energy
    if ws3:
        headers = [str(ws3.cell(row=1, column=c).value or "").lower() for c in range(1, ws3.max_column + 1)]
        for c, h in enumerate(headers, start=1):
            val = ws3.cell(row=2, column=c).value
            if isinstance(val, (int, float)):
                if "h2o" in h: eads_h2o = float(val)
                elif "ooh" in h: eads_ooh = float(val)
                elif "o2" in h: eads_o2 = float(val)
                elif "oh" in h: eads_oh = float(val)
                elif "o" in h and "oh" not in h and "ooh" not in h and "h2o" not in h and "o2" not in h:
                    eads_o = float(val)

    # 2. Validate 2-isolated-mol has user/extracted data for H2O, H2, and O2 (e_scf, zpe_ev, ts_ev)
    g_corr_map = {}
    zpe_gas_map = {}
    ts_gas_map = {}
    e_gas = {}
    if ws2:
        for r in range(2, ws2.max_row + 1):
            mol_name = str(ws2.cell(row=r, column=1).value or "").strip().lower()
            mol_key = None
            if "h2o" in mol_name:
                mol_key = "h2o"
            elif "h2" in mol_name:
                mol_key = "h2"
            elif "o2" in mol_name:
                mol_key = "o2"

            if mol_key:
                val_ev = ws2.cell(row=r, column=3).value
                val_ry = ws2.cell(row=r, column=2).value
                if isinstance(val_ev, (int, float)):
                    e_gas[mol_key] = float(val_ev)
                elif isinstance(val_ry, (int, float)):
                    e_gas[mol_key] = float(val_ry) * RY_TO_EV

                val_zpe = ws2.cell(row=r, column=4).value
                val_ts = ws2.cell(row=r, column=5).value
                val_gcorr = ws2.cell(row=r, column=6).value
                if isinstance(val_zpe, (int, float)):
                    zpe_gas_map[mol_key] = float(val_zpe)
                if isinstance(val_ts, (int, float)):
                    ts_gas_map[mol_key] = float(val_ts)
                if isinstance(val_gcorr, (int, float)):
                    g_corr_map[mol_key] = float(val_gcorr)
                elif mol_key in zpe_gas_map and mol_key in ts_gas_map:
                    g_corr_map[mol_key] = zpe_gas_map[mol_key] - ts_gas_map[mol_key]

    g_corr_h2o = g_corr_map.get("h2o", 0.56 - 0.67)
    g_corr_h2 = g_corr_map.get("h2", 0.272 - 0.404)
    g_corr_o2 = g_corr_map.get("o2", 0.10 - 0.64)

    e_h2o_gas = e_gas.get("h2o")
    e_h2_gas = e_gas.get("h2")
    e_o2_gas = e_gas.get("o2")

    # If 3-ads-energy does not already contain all 5 numeric adsorption energies, require all 3 isolated gas energies
    all_ads_cached = all(v is not None for v in [eads_h2o, eads_oh, eads_o, eads_ooh, eads_o2])
    if not all_ads_cached:
        missing_gas = []
        if e_h2o_gas is None:
            missing_gas.append("H2O_gas (2-isolated-gas/H2O/PW.out)")
        if e_h2_gas is None:
            missing_gas.append("H2_gas (2-isolated-gas/H2/PW.out)")
        if e_o2_gas is None:
            missing_gas.append("O2_gas (2-isolated-gas/O2/PW.out)")
        if missing_gas:
            raise ValueError(
                f"Missing isolated gas reference energy in sheet '2-isolated-mol' for: {', '.join(missing_gas)}. "
                "Please upload the isolated gas PW.out outputs in Module 3 or fill '2-isolated-mol' in the Excel sheet before continuing."
            )

    # 3. Evaluate missing adsorption energies directly from 1-adsorbates and 2-isolated-mol (using O2_gas for O2*)
    if not all_ads_cached:
        if ws1 is None:
            raise ValueError("Missing sheet '1-adsorbates' in workbook. Please complete Modules 2 and 3 before continuing.")

        e_scf = {}
        for r in range(2, ws1.max_row + 1):
            ads_name = str(ws1.cell(row=r, column=2).value or "").replace("*", "").strip().lower()
            val_ev = ws1.cell(row=r, column=4).value
            val_ry = ws1.cell(row=r, column=3).value
            if isinstance(val_ev, (int, float)):
                e_scf[ads_name] = float(val_ev)
            elif isinstance(val_ry, (int, float)):
                e_scf[ads_name] = float(val_ry) * RY_TO_EV

        e_clean = e_scf.get("clean", e_scf.get("surface"))
        if e_clean is None:
            raise ValueError(
                "Missing clean slab energy in sheet '1-adsorbates' (Row 2). "
                "Please complete Module 2/3 with 1-surface/PW.out before continuing."
            )

        missing_ads = []
        if eads_h2o is None:
            if "h2o" not in e_scf: missing_ads.append("H2O*")
            else: eads_h2o = e_scf["h2o"] - e_clean - e_h2o_gas
        if eads_oh is None:
            if "oh" not in e_scf: missing_ads.append("OH*")
            else: eads_oh = e_scf["oh"] - e_clean - (e_h2o_gas - 0.5 * e_h2_gas)
        if eads_o is None:
            if "o" not in e_scf: missing_ads.append("O*")
            else: eads_o = e_scf["o"] - e_clean - 0.5 * e_o2_gas
        if eads_ooh is None:
            if "ooh" not in e_scf: missing_ads.append("OOH*")
            else: eads_ooh = e_scf["ooh"] - e_clean - (2.0 * e_h2o_gas - 1.5 * e_h2_gas)
        if eads_o2 is None:
            if "o2" not in e_scf: missing_ads.append("O2*")
            else: eads_o2 = e_scf["o2"] - e_clean - e_o2_gas

        if missing_ads:
            raise ValueError(
                f"Missing SCF total energies in sheet '1-adsorbates' for: {', '.join(missing_ads)}. "
                "Please complete all adsorbate calculations in Module 3 before continuing."
            )

    # 4. Read ZPE and TS from sheet 4-vibrasi if populated
    zpe_dict = {}
    ts_dict = {}
    if ws4:
        for r in range(2, ws4.max_row + 1):
            ads_name = str(ws4.cell(row=r, column=2).value or "").replace("*", "").strip().lower()
            val_zpe = ws4.cell(row=r, column=3).value
            val_ts = ws4.cell(row=r, column=4).value
            if isinstance(val_zpe, (int, float)):
                zpe_dict[ads_name] = float(val_zpe)
            if isinstance(val_ts, (int, float)):
                ts_dict[ads_name] = float(val_ts)

    return {
        "surface": surface_name,
        "eads_h2o": round(eads_h2o, 4),
        "eads_oh": round(eads_oh, 4),
        "eads_o": round(eads_o, 4),
        "eads_ooh": round(eads_ooh, 4),
        "eads_o2": round(eads_o2, 4),
        "zpe": zpe_dict,
        "ts": ts_dict,
        "g_corr_h2o": g_corr_h2o,
        "g_corr_h2": g_corr_h2,
        "g_corr_o2": g_corr_o2
    }


def generate_workspace_archive(surface_name: str, reaction, base_app_dir: str) -> bytes:
    clean_surface = surface_name.strip()
    root = f"{clean_surface}/"
    files = {}

    ref_dir = os.path.join(base_app_dir, "assets", "reference_inputs")
    tmpl_dir = os.path.join(base_app_dir, "assets", "templates")

    h2_path = os.path.join(ref_dir, "c-isolated_h2.in")
    h2o_path = os.path.join(ref_dir, "c-isolated_h2o.in")
    o2_path = os.path.join(ref_dir, "c-isolated_o2.in")

    h2_content = open(h2_path, "r").read() if os.path.exists(h2_path) else "&CONTROL\n/\n"
    h2o_content = open(h2o_path, "r").read() if os.path.exists(h2o_path) else "&CONTROL\n/\n"
    o2_content = open(o2_path, "r").read() if os.path.exists(o2_path) else "&CONTROL\n/\n"

    # Core folders
    files[f"{root}1-surface/.keep"] = ""
    files[f"{root}2-isolated-gas/H2/PW.in"] = h2_content
    files[f"{root}2-isolated-gas/H2O/PW.in"] = h2o_content
    if "O2" in getattr(reaction, "gas_references", []):
        files[f"{root}2-isolated-gas/O2/PW.in"] = o2_content
    files[f"{root}5-data-visual/.keep"] = ""

    # Dynamic reaction intermediates
    for inter in reaction.intermediates:
        files[f"{root}3-adsorption/{inter}/.keep"] = ""
        files[f"{root}4-vibration/{inter}/.keep"] = ""

    # Load template workbook
    tmpl_file = os.path.join(tmpl_dir, reaction.template_filename)
    if os.path.exists(tmpl_file):
        wb = openpyxl.load_workbook(tmpl_file)
    else:
        wb = openpyxl.Workbook()

    # Pre-populate using reaction config
    reaction.scaffold_workbook(wb, clean_surface)

    excel_buf = io.BytesIO()
    wb.save(excel_buf)
    files[f"{root}{clean_surface}{reaction.data_sheet_suffix}"] = excel_buf.getvalue()

    return build_zip_from_dict(files)
