from dataclasses import dataclass


@dataclass
class DataManagementModel:
    plant: bool = True
    excitation_function: bool = True
    controller_configuration: bool = True
    pso_configuration: bool = True
    pso_result: bool = True
    block_diagram: bool = True
    time_domain_plot: bool = True
    bode_plot: bool = True
    transfer_functions: bool = True
