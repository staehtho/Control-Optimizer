from dataclasses import dataclass


@dataclass
class TransferFunctions:
    plant: str
    controller: str
    open_loop: str
    closed_loop: str
    sensitivity: str