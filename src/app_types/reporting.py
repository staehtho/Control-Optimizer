from dataclasses import dataclass


@dataclass
class DynamicReportSections:
    include_plant: bool = True
    include_function: bool = True


@dataclass
class DynamicReportData:
    plant_data: DynamicReportPlant
    function_data: DynamicReportFunction


@dataclass
class DynamicReportPlant:
    formula_svg: str


@dataclass
class DynamicReportFunction:
    formula_svg: str
    parameters: dict[str, float]
