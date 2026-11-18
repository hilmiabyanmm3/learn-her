import numpy as np
import openpyxl
from typing import Dict, List, Tuple, Any
from config.base_reaction import BaseReaction

class OERConfig(BaseReaction):
    """Oxygen Evolution Reaction (OER) configuration using the 6-step mechanism as default.
    
    Decouples molecular water adsorption (Step 1) and oxygen desorption (Step 6)
    from the 4 concerted proton-electron transfer steps (Steps 2-5).
    """
    
    name = "OER"
    full_name = "Oxygen Evolution Reaction (6-Step Mechanism)"
    reaction_type = "oxidation"
    intermediates = ["H2O", "OH", "O", "OOH", "O2"]
    gas_references = ["H2O", "H2", "O2"]
    template_filename = "d-oer_data_sheet.xlsx"
    data_sheet_suffix = "_oer_data_sheet.xlsx"
    equilibrium_potential = 1.23
    default_adsorbate = "OH"

    def scaffold_workbook(self, wb: openpyxl.Workbook, surface_name: str) -> None:
        """Pre-populates sheets 1 through 5 with single-row intermediate entries."""
        for s_name in ["1-adsorbates", "3-ads-energy", "5-gibbs-steps"]:
            if s_name in wb.sheetnames:
                ws = wb[s_name]
                for r in range(2, ws.max_row + 1):
                    ws.cell(row=r, column=1, value=surface_name)

        if "2-isolated-mol" in wb.sheetnames:
            ws2 = wb["2-isolated-mol"]
            for r, zpe_v, ts_v in [(2, 0.56, 0.67), (3, 0.272, 0.404), (4, 0.1, 0.64)]:
                ws2.cell(row=r, column=2).value = None
                ws2.cell(row=r, column=3).value = f"=B{r}*13.605698066"
                ws2.cell(row=r, column=4).value = zpe_v
                ws2.cell(row=r, column=5).value = ts_v
                ws2.cell(row=r, column=6).value = f"=D{r}-E{r}"

        if "4-vibrasi" in wb.sheetnames:
            ws4 = wb["4-vibrasi"]
            ws4.delete_rows(1, ws4.max_row + 1)
            headers = [
                "surface", "adsorbate", "zpe_ev", "ts_ev", 
                "mode_1_cm-1", "mode_2_cm-1", "mode_3_cm-1", "mode_4_cm-1", "mode_5_cm-1", 
                "mode_6_cm-1", "mode_7_cm-1", "mode_8_cm-1", "mode_9_cm-1"
            ]
            ws4.append(headers)
            for ads in ["H2O*", "OH*", "O*", "OOH*", "O2*"]:
                ws4.append([surface_name, ads, None, None])

    def calculate_thermodynamics(self, raw_data: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0) -> Dict[str, Any]:
        """Evaluates 6 OER steps. Uses explicit ZPE/TS from 4-vibrasi if provided, else benchmark fallbacks."""
        eads_h2o = float(raw_data.get("eads_h2o", -0.45))
        eads_oh  = float(raw_data.get("eads_oh", 1.20))
        eads_o   = float(raw_data.get("eads_o", 2.80))
        eads_ooh = float(raw_data.get("eads_ooh", 4.40))
        eads_o2  = float(raw_data.get("eads_o2", 4.60))

        # Check for explicit ZPE and TS (from 4-vibrasi)
        zpe = raw_data.get("zpe", {})
        ts  = raw_data.get("ts", {})

        # Gas phase corrections (H2O, H2, O2)
        g_h2o = raw_data.get("g_corr_h2o", 0.56 - 0.67)
        g_h2  = raw_data.get("g_corr_h2", 0.272 - 0.404)

        has_explicit_vibe = all(k in zpe for k in ["h2o", "oh", "o", "ooh"])

        if has_explicit_vibe:
            gc = {k: float(zpe.get(k, 0.0)) - float(ts.get(k, 0.0)) for k in ["h2o", "oh", "o", "ooh", "o2"]}
            
            # Step 1: * + H2O -> H2O*
            dg1 = round(eads_h2o + (gc["h2o"] - g_h2o), 4)
            # Step 2: H2O* -> OH* + H+ + e-
            dg2 = round((eads_oh - eads_h2o) + (gc["oh"] + 0.5 * g_h2 - gc["h2o"]), 4)
            # Step 3: OH* -> O* + H+ + e-
            dg3 = round((eads_o - eads_oh) + (gc["o"] + 0.5 * g_h2 - gc["oh"]), 4)
            # Step 4: O* + H2O -> OOH* + H+ + e-
            dg4 = round((eads_ooh - eads_o) + (gc["ooh"] + 0.5 * g_h2 - gc["o"] - g_h2o), 4)
            # Step 5: OOH* -> O2* + H+ + e-
            dg5 = round((eads_o2 - eads_ooh) + (gc.get("o2", 0.0) + 0.5 * g_h2 - gc["ooh"]), 4)
            # Step 6: O2* -> * + O2
            dg6 = round(4.92 - (dg1 + dg2 + dg3 + dg4 + dg5), 4)
        else:
            # Universal Nørskov CHE benchmark corrections fallback
            dg1 = round(eads_h2o, 4)
            dg2 = round((eads_oh - eads_h2o) + 0.35, 4)
            dg3 = round((eads_o - eads_oh) + 0.05, 4)
            dg4 = round((eads_ooh - eads_o) + 0.40, 4)
            dg5 = round((eads_o2 - eads_ooh) + 0.30, 4)
            dg6 = round(4.92 - (dg1 + dg2 + dg3 + dg4 + dg5), 4)

        # Operational potential and pH shift (Steps 2-5 are electrochemical oxidations)
        shift = u_pot + 0.0592 * ph
        dg1_u = dg1
        dg2_u = round(dg2 - shift, 4)
        dg3_u = round(dg3 - shift, 4)
        dg4_u = round(dg4 - shift, 4)
        dg5_u = round(dg5 - shift, 4)
        dg6_u = dg6

        elec_steps = [dg2, dg3, dg4, dg5]
        g_max = max(elec_steps)
        pds_names = {
            0: "Step 2 (H2O* -> OH* + H+ + e-)",
            1: "Step 3 (OH* -> O* + H+ + e-)",
            2: "Step 4 (O* + H2O -> OOH* + H+ + e-)",
            3: "Step 5 (OOH* -> O2* + H+ + e-)"
        }
        pds = pds_names[elec_steps.index(g_max)]
        u_limiting = g_max
        eta_oer = max(0.0, u_limiting - 1.23)
        descriptor = dg3

        return {
            "reaction": self.name,
            "surface": raw_data.get("surface", "Surface"),
            "eads_h2o": eads_h2o, "eads_oh": eads_oh, "eads_o": eads_o, "eads_ooh": eads_ooh, "eads_o2": eads_o2,
            "dg1": dg1, "dg2": dg2, "dg3": dg3, "dg4": dg4, "dg5": dg5, "dg6": dg6,
            "dg1_u": dg1_u, "dg2_u": dg2_u, "dg3_u": dg3_u, "dg4_u": dg4_u, "dg5_u": dg5_u, "dg6_u": dg6_u,
            "steps": [dg1_u, dg2_u, dg3_u, dg4_u, dg5_u, dg6_u],
            "descriptor": descriptor,
            "g_max": g_max,
            "pds": pds,
            "u_limiting": round(u_limiting, 4),
            "overpotential": round(eta_oer, 4)
        }

    def get_reaction_coordinate_states(self, thermo_summary: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0, step_mode: str = "4-step") -> Tuple[List[str], List[float], List[str]]:
        dg1_u = thermo_summary.get("dg1_u", -0.45)
        dg2_u = thermo_summary.get("dg2_u", 1.65)
        dg3_u = thermo_summary.get("dg3_u", 1.82)
        dg4_u = thermo_summary.get("dg4_u", 1.05)
        dg5_u = thermo_summary.get("dg5_u", 0.55)
        dg6_u = thermo_summary.get("dg6_u", 0.30)

        if step_mode == "6-step":
            labels = [
                r"$* + 2\mathrm{H}_2\mathrm{O}$",
                r"$\mathrm{H}_2\mathrm{O}^* + \mathrm{H}_2\mathrm{O}$",
                r"$\mathrm{OH}^* + \mathrm{H}_2\mathrm{O}$",
                r"$\mathrm{O}^* + \mathrm{H}_2\mathrm{O}$",
                r"$\mathrm{OOH}^*$",
                r"$\mathrm{O}_2^*$",
                r"$* + \mathrm{O}_2$"
            ]
            steps = [dg1_u, dg2_u, dg3_u, dg4_u, dg5_u, dg6_u]
            levels = [0.0]
            for s in steps:
                levels.append(round(levels[-1] + s, 4))

            return labels, levels, []

        # Default: Classical 4-step merged reaction coordinate profile
        labels = [
            r"$* + 2\mathrm{H}_2\mathrm{O}$",
            r"$\mathrm{OH}^* + \mathrm{H}_2\mathrm{O}$",
            r"$\mathrm{O}^* + \mathrm{H}_2\mathrm{O}$",
            r"$\mathrm{OOH}^*$",
            r"$* + \mathrm{O}_2$"
        ]
        step1 = round(dg1_u + dg2_u, 4)
        step2 = round(dg3_u, 4)
        step3 = round(dg4_u, 4)
        step4 = round(dg5_u + dg6_u, 4)
        steps_4 = [step1, step2, step3, step4]

        levels = [0.0]
        for s in steps_4:
            levels.append(round(levels[-1] + s, 4))

        return labels, levels, []

    def get_volcano_parameters(self, thermo_summary: Dict[str, Any]) -> Dict[str, Any]:
        desc_val = thermo_summary.get("descriptor", 1.82)
        u_l = thermo_summary.get("u_limiting", 1.82)

        x_desc = np.linspace(0.8, 2.4, 200)
        x_left = x_desc[x_desc <= 1.60]
        y_left = 3.20 - x_left
        x_right = x_desc[x_desc >= 1.60]
        y_right = x_right

        return {
            "x_label": r"OER Scaling Descriptor $\Delta G_{\mathrm{O}^*} - \Delta G_{\mathrm{OH}^*}$ (eV)",
            "y_label": r"Limiting Potential $U_L$ (V vs. RHE)",
            "title": "OER Limiting Potential ($U_L$) Volcano (6-Step)",
            "branches": [
                {"x": x_left, "y": y_left, "label": r"Step 4 Limiting ($O^* \rightarrow OOH^*$)", "color": "#475569"},
                {"x": x_right, "y": y_right, "label": r"Step 3 Limiting ($OH^* \rightarrow O^*$)", "color": "#007BFF"}
            ],
            "apex": (1.60, 1.60, "Ideal OER Apex (1.60 V, η = 0.37 V)"),
            "data_point": (desc_val, u_l),
            "xlim": (0.8, 2.4),
            "ylim": (1.2, 2.4),
            "ref_lines": [(1.23, "gray", "--")]
        }
