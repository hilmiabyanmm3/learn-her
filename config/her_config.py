import numpy as np
import openpyxl
from typing import Dict, List, Tuple, Any
from config.base_reaction import BaseReaction

class HERConfig(BaseReaction):
    """Hydrogen Evolution Reaction (HER) configuration and thermodynamic model.
    Accounts for both Volmer and Heyrovsky elementary steps under the CHE model.
    """
    
    name = "HER"
    full_name = "Hydrogen Evolution Reaction"
    reaction_type = "reduction"
    intermediates = ["H"]
    gas_references = ["H2", "H2O"]
    template_filename = "d-her_data_sheet.xlsx"
    data_sheet_suffix = "_her_data_sheet.xlsx"
    equilibrium_potential = 0.00
    default_adsorbate = "H"

    def scaffold_workbook(self, wb: openpyxl.Workbook, surface_name: str) -> None:
        """Pre-populates sheets 1 through 5 for HER."""
        if "1-adsorbate" in wb.sheetnames:
            wb["1-adsorbate"].cell(row=2, column=1, value=surface_name)
            
        if "2-isolated-mol" in wb.sheetnames:
            ws2 = wb["2-isolated-mol"]
            if ws2.max_row < 2:
                ws2.append(["H2", -31.7452, 0.2720, 0.4040])
                ws2.append(["H2O", -467.2185, 0.5600, 0.6700])
                
        if "3-ads-energy" in wb.sheetnames:
            wb["3-ads-energy"].cell(row=2, column=1, value=surface_name)
            
        if "4-vibrasi" in wb.sheetnames:
            ws4 = wb["4-vibrasi"]
            ws4.cell(row=2, column=1, value=surface_name)
            ws4.cell(row=2, column=2, value="H")
            
        if "5-gibbs" in wb.sheetnames:
            ws5 = wb["5-gibbs"]
            ws5.cell(row=1, column=1, value="surface")
            ws5.cell(row=1, column=2, value="adsorbate")
            ws5.cell(row=1, column=3, value="e_g_1")  # Volmer
            ws5.cell(row=1, column=4, value="e_g_2")  # Heyrovsky
            ws5.cell(row=1, column=5, value="u_l")
            ws5.cell(row=2, column=1, value=surface_name)
            ws5.cell(row=2, column=2, value="H")
            ws5.cell(row=2, column=4, value="=-'5-gibbs'!C2")
            ws5.cell(row=2, column=5, value="=-ABS('5-gibbs'!C2)")

    def calculate_thermodynamics(self, raw_data: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0) -> Dict[str, Any]:
        """Evaluates Volmer (dg1) and Heyrovsky (dg2) steps under CHE model, ensuring G2 = -G1."""
        delta_e = raw_data.get("delta_e", 0.0)
        delta_zpe = raw_data.get("delta_zpe", 0.0)
        t_delta_s = raw_data.get("t_delta_s", -0.2020)
        
        # Standard Gibbs adsorption energy
        delta_g_base = delta_e + delta_zpe - t_delta_s
        
        # 1. Volmer step (* + H+ + e- -> H*)
        dg_volmer_base = round(delta_g_base, 4)
        
        # 2. Heyrovsky step (H* + H+ + e- -> * + H2) strictly enforces G2 = -G1 at baseline
        dg_heyrovsky_base = round(-delta_g_base, 4)
        
        # Potential and pH shifts under CHE model (cathodic reduction: +eU + 0.0592*pH)
        shift = u_pot + 0.0592 * ph
        dg_volmer_shifted = round(dg_volmer_base + shift, 4)
        dg_heyrovsky_shifted = round(dg_heyrovsky_base + shift, 4)
        
        # Potential determining step (PDS)
        pds = "Volmer (* + H⁺ + e⁻ → *H)" if delta_g_base > 0 else "Heyrovsky (*H + H⁺ + e⁻ → * + H₂)"
        u_limiting = -abs(delta_g_base)
        overpotential = abs(delta_g_base)
        
        return {
            "reaction": self.name,
            "surface": raw_data.get("surface", "Surface"),
            "delta_e": round(delta_e, 4),
            "delta_zpe": round(delta_zpe, 4),
            "t_delta_s": round(t_delta_s, 4),
            "delta_g": round(delta_g_base, 4),
            "dg_volmer": dg_volmer_base,
            "dg_volmer_shifted": dg_volmer_shifted,
            "dg_heyrovsky": dg_heyrovsky_base,
            "dg_heyrovsky_shifted": dg_heyrovsky_shifted,
            "steps": [dg_volmer_shifted, dg_heyrovsky_shifted],
            "pds": pds,
            "u_limiting": round(u_limiting, 4),
            "overpotential": round(overpotential, 4)
        }

    def get_reaction_coordinate_states(self, thermo_summary: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0) -> Tuple[List[str], List[float], List[str]]:
        """Returns 3 states: Initial (* + 2(H+ + e-)), Intermediate (H* + H+ + e-), Product (* + H2)."""
        labels = [
            r"$* + 2(\mathrm{H}^+ + \mathrm{e}^-)$",
            r"$\mathrm{H}^* + (\mathrm{H}^+ + \mathrm{e}^-)$",
            r"$* + \mathrm{H}_2$"
        ]
        dg_v = thermo_summary.get("dg_volmer_shifted", 0.0)
        dg_h = thermo_summary.get("dg_heyrovsky_shifted", 0.0)
        
        levels = [0.0, dg_v, dg_v + dg_h]
        return labels, levels, []

    def get_volcano_parameters(self, thermo_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Volcano parameters: X = Delta E_H* (eV), Y = U_L (V)."""
        delta_e = thermo_summary.get("delta_e", -0.24)
        dg_volmer = thermo_summary.get("dg_volmer", 0.0)
        u_l = thermo_summary.get("u_limiting", -0.04)
        
        corr = dg_volmer - delta_e if delta_e is not None else 0.24
        de_peak = -corr
        
        de_neg = np.linspace(-1.0, de_peak, 100)
        de_pos = np.linspace(de_peak, 0.6, 100)
        
        ul_neg = de_neg + corr      # Heyrovsky branch: slope = +1
        ul_pos = -(de_pos + corr)   # Volmer branch: slope = -1
        
        return {
            "x_label": r"*H Adsorption Energy $\Delta E_{\mathrm{H}^*}$ (eV)",
            "y_label": r"Limiting Potential $U_L$ (V vs. RHE)",
            "title": f"HER Limiting Potential ($U_L$) Volcano",
            "branches": [
                {"x": de_neg, "y": ul_neg, "label": rf"Heyrovsky Limiting ($\Delta E < {de_peak:.2f}$ eV, slope = +1)", "color": "#475569"},
                {"x": de_pos, "y": ul_pos, "label": rf"Volmer Limiting ($\Delta E > {de_peak:.2f}$ eV, slope = -1)", "color": "#007BFF"}
            ],
            "apex": (de_peak, 0.0, f"Ideal Volcano Apex ({de_peak:.2f} eV, 0.0 V)"),
            "data_point": (delta_e, u_l),
            "xlim": (-1.0, 0.6),
            "ylim": (-0.85, 0.1),
            "ref_lines": [(0.0, "gray", "--")]
        }
