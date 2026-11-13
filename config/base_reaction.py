from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any
import openpyxl

class BaseReaction(ABC):
    """Abstract Base Class defining the schema and physics for an electrochemical reaction."""
    
    name: str = ""
    full_name: str = ""
    reaction_type: str = "reduction"  # "reduction" or "oxidation"
    intermediates: List[str] = []
    gas_references: List[str] = ["H2", "H2O"]
    template_filename: str = ""
    data_sheet_suffix: str = ""
    equilibrium_potential: float = 0.00
    default_adsorbate: str = ""
    
    @abstractmethod
    def scaffold_workbook(self, wb: openpyxl.Workbook, surface_name: str) -> None:
        """Pre-populates the reaction-specific tracking sheets in openpyxl."""
        pass
        
    @abstractmethod
    def calculate_thermodynamics(self, raw_data: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0) -> Dict[str, Any]:
        """Evaluates elementary step free energies, limiting potential (U_L), PDS, and overpotential."""
        pass

    @abstractmethod
    def get_reaction_coordinate_states(self, thermo_summary: Dict[str, Any], u_pot: float = 0.0, ph: float = 0.0) -> Tuple[List[str], List[float], List[str]]:
        """Returns (state_labels, energy_levels, step_annotations) for reaction profile rendering."""
        pass

    @abstractmethod
    def get_volcano_parameters(self, thermo_summary: Dict[str, Any]) -> Dict[str, Any]:
        """Returns parameters needed for the Sabatier volcano plot."""
        pass
