import numpy as np
import openpyxl
from typing import Dict, List, Tuple, Any
from config.base_reaction import BaseReaction

class ORRConfig(BaseReaction):
    """Oxygen Reduction Reaction (ORR) configuration (4-electron reduction)."""
    
    name = "ORR"
    full_name = "Oxygen Reduction Reaction"
    reaction_type = "reduction"
    intermediates = ["OOH", "O", "OH"]
    gas_references = ["H2O", "H2", "O2"]
    template_filename = "d-oer_data_sheet.xlsx"
    data_sheet_suffix = "_orr_data_sheet.xlsx"
    equilibrium_potential = 1.23
    default_adsorbate = "OH"

    def scaffold_workbook(self, wb: openpyxl.Workbook, surface_name: str) -> None:
        for s_name in ["1-adsorbates", "3-ads-energy", "4-vibrasi", "5-gibbs-steps"]:
            if s_name in wb.sheetnames:
                ws = wb[s_name]
                for r in range(2, ws.max_row + 1):
                    ws.cell(row=r, column=1, value=surface_name)

    def calculate_thermodynamics(self, raw_data: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0) -> Dict[str, Any]:
        # ORR is reverse of OER: Delta G_i^ORR = - Delta G_{5-i}^OER
        eads_oh = float(raw_data.get("eads_oh", 1.20))
        eads_o = float(raw_data.get("eads_o", 2.80))
        eads_ooh = float(raw_data.get("eads_ooh", 4.40))
        
        dg1_oer = eads_oh + 0.35
        dg2_oer = (eads_o - eads_oh) + 0.05
        dg3_oer = (eads_ooh - eads_o) + 0.40
        dg4_oer = 4.92 - (dg1_oer + dg2_oer + dg3_oer)
        
        # 4 reduction steps (O2 -> OOH* -> O* -> OH* -> H2O):
        dg1 = round(-dg4_oer, 4)
        dg2 = round(-dg3_oer, 4)
        dg3 = round(-dg2_oer, 4)
        dg4 = round(-dg1_oer, 4)
        
        shift = u_pot - 0.0592 * ph
        dg1_u = round(dg1 + shift, 4)
        dg2_u = round(dg2 + shift, 4)
        dg3_u = round(dg3 + shift, 4)
        dg4_u = round(dg4 + shift, 4)
        
        steps_list = [dg1, dg2, dg3, dg4]
        # In reduction, limiting potential is determined by step that is hardest to make exergonic (max Delta G)
        g_max = max(steps_list)
        u_limiting = -g_max
        eta_orr = max(0.0, 1.23 - u_limiting)
        
        return {
            "reaction": self.name,
            "surface": raw_data.get("surface", "Surface"),
            "dg1": dg1, "dg2": dg2, "dg3": dg3, "dg4": dg4,
            "dg1_u": dg1_u, "dg2_u": dg2_u, "dg3_u": dg3_u, "dg4_u": dg4_u,
            "steps": [dg1_u, dg2_u, dg3_u, dg4_u],
            "pds": "Step 4 (OH* + H+ + e- -> H2O)" if dg4 == g_max else "Step 1 (O2 + H+ + e- -> OOH*)",
            "u_limiting": round(u_limiting, 4),
            "overpotential": round(eta_orr, 4)
        }

    def get_reaction_coordinate_states(self, thermo_summary: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0) -> Tuple[List[str], List[float], List[str]]:
        labels = [
            r"$\mathrm{O}_2 + 4(\mathrm{H}^+ + \mathrm{e}^-)$",
            r"$\mathrm{OOH}^* + 3(\mathrm{H}^+ + \mathrm{e}^-)$",
            r"$\mathrm{O}^* + 2(\mathrm{H}^+ + \mathrm{e}^-)$",
            r"$\mathrm{OH}^* + (\mathrm{H}^+ + \mathrm{e}^-)$",
            r"$* + 2\mathrm{H}_2\mathrm{O}$"
        ]
        steps = [
            thermo_summary.get("dg1_u", -0.50),
            thermo_summary.get("dg2_u", -1.05),
            thermo_summary.get("dg3_u", -1.82),
            thermo_summary.get("dg4_u", -1.55)
        ]
        levels = [0.0]
        for s in steps:
            levels.append(levels[-1] + s)
        return labels, levels, []

    def get_volcano_parameters(self, thermo_summary: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "x_label": r"ORR Descriptor $\Delta G_{\mathrm{OH}^*}$ (eV)",
            "y_label": r"Limiting Potential $U_L$ (V vs. RHE)",
            "title": f"ORR Limiting Potential Volcano",
            "branches": [],
            "apex": (0.80, 0.80, "Ideal ORR Apex"),
            "data_point": (0.80, thermo_summary.get("u_limiting", 0.70)),
            "xlim": (0.0, 1.8),
            "ylim": (0.0, 1.23),
            "ref_lines": [(1.23, "gray", "--")]
        }
