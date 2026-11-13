from typing import Dict
from config.base_reaction import BaseReaction
from config.her_config import HERConfig
from config.oer_config import OERConfig
from config.orr_config import ORRConfig

REACTION_REGISTRY: Dict[str, BaseReaction] = {
    "HER": HERConfig(),
    "OER": OERConfig(),
    "ORR": ORRConfig()
}

def get_reaction(name: str = "HER") -> BaseReaction:
    """Returns the reaction instance by name (case-insensitive fallback to HER)."""
    clean_name = name.upper().strip()
    for key in REACTION_REGISTRY:
        if key in clean_name:
            return REACTION_REGISTRY[key]
    return REACTION_REGISTRY["HER"]
