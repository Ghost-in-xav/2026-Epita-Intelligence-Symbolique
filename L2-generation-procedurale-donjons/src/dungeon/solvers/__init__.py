from .base import GenerationResult, LevelGenerator
from .cpsat_generator import CPSATDungeonGenerator
from .wfc import WFCDungeonGenerator

REGISTRY = {
    "cpsat": CPSATDungeonGenerator,
    "wfc": WFCDungeonGenerator,
}

__all__ = ["GenerationResult", "LevelGenerator", "CPSATDungeonGenerator", "WFCDungeonGenerator", "REGISTRY"]
