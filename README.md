# 📚 Learning Module: Hydrogen Evolution Reaction (HER)
An interactive educational and computational pipeline for Density Functional Theory (DFT) modeling of the Hydrogen Evolution Reaction using Quantum ESPRESSO. This suite guides researchers and students step-by-step through pristine slab preparation, active site detection, finite-displacement vibrational analysis, thermochemical integration, and publication-ready Sabatier volcano plotting.

---

## 💻 Technologies & Frameworks
- **Quantum ESPRESSO (PWscf / `pw.x`)**
- **Streamlit** (Multi-page Web Framework)
- **ASE (Atomic Simulation Environment)**
- **openpyxl** (Dynamic Excel Thermochemical Tracking)
- **Matplotlib & NumPy** (Publication-Grade Visualization Engine)
- **KaTeX** (LaTeX Scientific Typography)

---

## 🚀 Syllabus & Pipeline Architecture

### Phase 1: Structural Setup & Adsorbate Engineering
- **Module 1: Workspace Setup & Data Template**
  - Automated project directory scaffolding with standardized uppercase chemical folders (`2-isolated-gas/H2/`, `2-isolated-gas/H2O/`, `3-adsorption/H/`, `4-vibration/H/`, and `5-data-visual/`).
  - Pre-fills canonical `<SurfaceName>_her_data_sheet.xlsx` with standard headers, surface names, reference molecules, and vibrational mode rows.
- **Module 2: Adsorbate Creation & Active Site Selection**
  - Parses relaxed slab coordinates (`Begin final coordinates`) and ground-state energies from `1-surface/PW.out`.
  - Scans topmost surface transition metal sites (Sc through Zn, 4d/5d, and dopants) within a 1.8 Å depth threshold.
  - Generates `3-adsorption/H/PW.in` with clean card decomposition (zero coordinate duplication) placing H 1.0 Å above the selected active site.

### Phase 2: Vibrations & Thermochemistry
- **Module 3: Adsorption Energy & Vibrational Logistics**
  - **Tab 1:** Extracts ground-state electronic energies, logs them to Excel, and sets up 6 finite-displacement calculations in `4-vibration/H/` (`PWINPUT_atm{N}_{axis}{suffix}` with `calculation = 'scf'`, `nstep = 1`, and `tprnfor = .true.`).
  - **Tab 2:** Dual-branch vibrational handler that computes harmonic frequencies and ZPE from logs, or formats empty input cells in sheet `4-vibrasi` for manual entry.
- **Module 4: Delta Gibbs & Visualization**
  - Evaluates adsorption energy ($\Delta E_{\mathrm{H}^*} = E(\text{slab+H}) - E(\text{slab}) - \frac{1}{2}E(\text{H}_2)$), Zero-Point Energy ($\Delta\text{ZPE}$), and entropic contributions ($-T\Delta S \approx +0.202\text{ eV}$).
  - Computes standard Gibbs free energy ($\Delta G_{\mathrm{H}^*}$) and **Limiting Potential** ($U_L = -|\Delta G_{\mathrm{H}^*}|/e$).
  - Updates sheet `5-gibbs` with evaluated floats and dynamic Excel formulas.
  - Automatically renders two distinct, publication-ready diagrams saved to `5-data-visual/`:
    1. **Gibbs Profile:** Reaction coordinate step profile under tunable electrode potential ($U$) and pH.
    2. **$U_L$ Graph:** Single-surface Sabatier Volcano plot ($U_L$ vs. $\text{*H}$ Adsorption Energy $\Delta E_{\mathrm{H}^*}$).

### Phase 3: Screening & Documentation
- **Module 5: Comparation (Multi-Catalyst Screening)**
  - Ingests multi-surface project archives and extracts thermochemical descriptors across catalysts.
  - Renders **Comparative Reaction Coordinates** with parallel plateaus (60% line width) centered over $\mathrm{H}^*$.
  - Renders the **Comparative $U_L$ Sabatier Volcano Graph** ($U_L$ vs. $\text{*H}$ adsorption energy) mapping catalysts onto Volmer-limiting vs. Heyrovsky-limiting branches.
  - Generates a comparative performance table with limiting potentials, overpotentials, and rate-limiting bottleneck diagnostics.
- **Documentation: Read More**
  - Comprehensive theoretical foundations (Volmer-Heyrovsky-Tafel pathways, Computational Hydrogen Electrode model, Sabatier principle).
  - Technical troubleshooting and error recovery manual.

---

## 📃 The Background
The Hydrogen Evolution Reaction (HER) is the benchmark cathodic half-reaction for clean water splitting and electrochemical hydrogen production. While Density Functional Theory (DFT) workflows using Quantum ESPRESSO are widely utilized, managing directory hierarchies, tracking multi-sheet thermochemical spreadsheets, avoiding coordinate duplication, and computing vibrational corrections can present high barriers to entry.

This learning and computational module bridges fundamental DFT electronic structure calculations with macroscopic electrochemistry. Built following an isolated Three-Tier Architecture (View – Utils – Data), it offers an intuitive graphical interface for both beginner students and computational researchers to conduct reproducible, publication-grade HER screening.

---

## 👟 Running the Project

### Prerequisites
- Python 3.10+ installed on your system.

### Option 1: One-Click Launchers
1. Clone this repository and open the project directory:
   ```bash
   git clone https://github.com/<your-username>/<your-her-repo>.git
   cd <your-her-repo>
   ```
2. Launch according to your operating system:
   - **macOS / Linux:** Run `./run_mac.sh` (or `bash run_mac.sh`)
   - **Windows:** Double-click `run_windows.bat`

### Option 2: Manual Terminal Execution
```bash
# 1. Create and activate a virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# 2. Upgrade pip and install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Launch the Streamlit application
streamlit run Main_Menu.py
```

---

## 📁 Standard Project Workspace Hierarchy
When processing workflows, the application structures and expects project `.zip` archives with the following layout:

```text
<SurfaceName>/
├── <SurfaceName>_her_data_sheet.xlsx   # Canonical 5-sheet tracking workbook
├── 1-surface/                          # Pristine slab PW.in and relaxed PW.out
├── 2-isolated-gas/
│   ├── H2/                             # Isolated H2 PW.in and PW.out
│   └── H2O/                            # Isolated H2O PW.in and PW.out
├── 3-adsorption/
│   └── H/                              # Adsorbed slab PW.in and PW.out
├── 4-vibration/
│   └── H/                              # Displaced PWINPUT files & vibrational logs
└── 5-data-visual/                      # Rendered diagrams (her_free_energy_diagram.png, etc.)
```