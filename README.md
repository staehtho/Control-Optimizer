# Control Optimizer

Control Optimizer is a desktop application for modeling dynamic SISO plants, configuring controllers, and evaluating
control performance through simulation and particle swarm optimization (PSO).

The application is built with PySide6 and follows a layered MVVM-style architecture. Numerical control logic,
application state, background computation, and presentation concerns are separated into dedicated modules under `src/`.

## Features

- Define transfer-function-based dynamic plants.
- Configure PI, PID, and feed-forward PID controllers.
- Simulate plant and closed-loop responses with configurable excitation functions.
- Evaluate time-domain and frequency-domain controller behavior.
- Optimize controller parameters with PSO.
- Configure anti-windup behavior and actuator constraints.
- Save and load project data.
- Generate reports from evaluation results.
- Manage German and English translations through a Qt/PySide6 i18n pipeline.

## Requirements

- Python with support for the versions required by the dependencies in `requirements.txt`.
- PowerShell for the translation build script.
- Qt Linguist tools available through the PySide6 installation when updating translations.

Install dependencies from the project root:

```powershell
python -m pip install -r requirements.txt
```

## Running the Application

From the project root:

```powershell
python .\src\main.py
```

The application initializes logging, clears and recreates the temporary output directory, builds the `AppEngine`, shows
the splash screen, preloads the main views, and starts a PSO warmup after startup.

```

## Source Structure


Control_Optimizer/
  +-- src/
  |   +-- app_domain/       # Domain logic, control systems, engines, PSO, and objective functions
  |   +-- app_types/        # Shared dataclasses, enums, navigation types, and controller specs
  |   +-- config/           # Runtime configuration, languages, and QSS themes
  |   +-- i18n/             # Qt translation sources, compiled translations, and build script
  |   +-- infrastructure/   # Background worker classes
  |   +-- models/           # Application state models and model container
  |   +-- resources/        # Icons, static resources, temp output, and resource path helpers
  |   +-- service/          # Simulation orchestration and report generation
  |   +-- settings/         # Persisted local settings
  |   +-- utils/            # Formatting, LaTeX helpers, SVG helpers, and utilities
  |   +-- viewmodels/       # ViewModels connecting models/services to UI widgets
  |   +-- views/            # PySide6 screens, widgets, translations, and view helpers
  +-- requirements.txt
  +-- README.md
```

## Architecture Overview

### Entry Point

- `src/main.py` creates the Qt application, configures logging, prepares temporary output directories, creates the
  `AppEngine`, builds the main view, and starts the Qt event loop.

### Composition Root

- `src/app_domain/app_engine.py` owns the central application composition. It creates the `SimulationService`, owns the
  `ModelContainer`, provides lazy ViewModel factories, handles project save/load, refreshes UI state from models, and
  shuts down background workers.
- `src/app_domain/ui_context.py` provides shared access to settings, theme, and language state for views.

### Domain and Simulation Logic

- `src/app_domain/controlsys/` contains plant and closed-loop controller models, controller enums, anti-windup enums,
  solver enums, and transfer-function behavior.
- `src/app_domain/engine/` contains numerical engines for plant responses, closed-loop responses, frequency responses,
  transfer functions, excitation functions, and PSO execution.
- `src/app_domain/functions/` contains excitation signal implementations such as step, sine, cosine, rectangular, white
  noise, pink noise, brownian noise, and null signals.
- `src/app_domain/PSO/` contains particle swarm optimization primitives.
- `src/app_domain/pso_objective/` contains objective-function code, Numba-accelerated time-domain simulation, frequency
  metrics, and filter-time-constant handling.

### State and Shared Types

- `src/models/` contains models for plant data, controller data, PSO configuration, simulation settings, general
  settings, and data management.
- `src/models/model_container.py` aggregates application models and handles project import/export.
- `src/app_types/` contains shared typed payloads and metadata, including `controller_sepc.py`, which defines
  `ControllerSpec` and the central `CONTROLLER_SPECS` registry.

### Presentation Layer

- `src/viewmodels/` connects models and services to the UI.
- `src/views/` contains the main navigation shell and screens for plant setup, excitation functions, controller setup,
  PSO configuration, evaluation, simulation, data management, help, and settings.
- `src/views/widgets/` contains reusable PySide6 widgets.
- `src/views/view_helpers/` contains layout, icon, validation, and widget-binding helpers.
- `src/views/translations/` contains UI-facing translation helpers for enums and labels.

### Services and Infrastructure

- `src/service/` contains orchestration services, including simulation and reporting.
- `src/service/reporting/` contains report builders and report sections.
- `src/infrastructure/` contains background worker classes for heavier computations.

## Runtime Flow

1. `main.py` creates the Qt application and shows the splash screen.
2. Logging and temporary output paths are initialized.
3. `AppEngine` creates services, models, shared UI context, and lazy ViewModel factories.
4. `MainView` builds the navigation shell and screen factories.
5. Views interact with ViewModels, which update models and request simulations from the service layer.
6. Background workers perform heavier computations without blocking the UI.
7. Simulation and optimization results are displayed in plots, evaluation views, simulation views, and generated reports.

## Internationalization

Translations are managed with the PowerShell build script in `src/i18n/build-i18n.ps1`.

Configured languages are defined in:

```text
src/config/languages.json
```

To add or remove a language, update the `languages` array in that JSON file. The current configuration contains:

- `en`
- `de`

Run the translation pipeline from the project root:

```powershell
cd src
.\i18n\build-i18n.ps1
```

The script scans source files for translatable strings, updates `.ts` files, opens Qt Linguist when needed, compiles
`.qm` files, and keeps application and report translations aligned with `languages.json`.

## Extending the System with a New Controller

New controllers must be integrated in both the frequency-domain and time-domain paths. The current built-in controller
types are:

- `ControllerType.PI`
- `ControllerType.PID`
- `ControllerType.FFPID`

Adding another controller requires updates in these areas:

1. Register the controller enum value.
2. Add UI translation support.
3. Implement a frequency-domain `ClosedLoop` subclass.
4. Add controller and closed-loop block-diagram builders.
5. Register a `ControllerSpec`.
6. Implement the Numba time-domain step function.
7. Register the step function in the simulation core.

### 1. Register the Controller Type

Update `src/app_domain/controlsys/enums.py`:

```python
class ControllerType(Enum):
    PI = "pi"
    PID = "pid"
    FFPID = "ffpid"
    EXAMPLE = "example"
```

### 2. Add UI Translation Support

Update `src/views/translations/enum_translations.py` so the new enum value can be displayed in the UI:

```python
@register_translation(ControllerType)
def _controller_type(self, value: Enum) -> str:
    match value:
        case ControllerType.PI:
            return QCoreApplication.translate("ControlEnums", "PI")
        case ControllerType.PID:
            return QCoreApplication.translate("ControlEnums", "PID")
        case ControllerType.FFPID:
            return QCoreApplication.translate("ControlEnums", "Feed-forward PID")
        case ControllerType.EXAMPLE:
            return QCoreApplication.translate("ControlEnums", "Example")
        case _:
            raise ValueError(...)
```

After adding or changing translatable strings, run the i18n build script.

### 3. Implement the Frequency-Domain ClosedLoop Class

Create a new class under `src/app_domain/controlsys/` and inherit from `ClosedLoop`.

```python
class ExampleClosedLoop(ClosedLoop):
    controller_type = ControllerType.EXAMPLE
    tf_link_index = -1
    has_integrator = True

    def get_controller_params(self) -> list[float]:
        return [self._a, self._b]

    def controller(self, s: complex | np.ndarray) -> complex | np.ndarray:
        ...

    @classmethod
    def frf_batch(
        cls,
        plant_tf: Callable[[np.ndarray | complex], np.ndarray | complex],
        X: np.ndarray,
        s: np.ndarray,
    ) -> np.ndarray:
        ...
```

`tf_link_index` links the controller's filter time constant to the controller parameter vector. Controllers without a
filter time constant should use `-1`. For controllers with a generated filter time constant, the effective `Tf` value is
appended internally as the final entry of the optimization parameter vector; `frf_batch` must follow the same convention.

The base `ClosedLoop` implementation provides the standard unity-feedback relations:

- `L(s) = C(s) * G(s)`
- `T(s) = L(s) / (1 + L(s))`
- `S(s) = 1 / (1 + L(s))`

Override these methods when the controller structure differs from the standard PI/PID feedback path, as is done for
feed-forward PID behavior.

### 4. Add Block-Diagram Builders

Controller SVG builders live in:

```text
src/utils/svg/controller_builders.py
src/utils/svg/layout_closed_loop.py
```

Add a controller builder and, if the closed-loop structure is not the default unity-feedback layout, add a closed-loop
layout builder as well.

### 5. Register the ControllerSpec

Update `src/app_types/controller_sepc.py` and register the controller in `CONTROLLER_SPECS`.

```python
example_spec = ControllerSpec(
    controller_class=ExampleClosedLoop,
    param_names=["A", "B"],
    bounds=([0.0, 0.0], [10.0, 10.0]),
    build_controller_svg=c.get_example_controller_svg,
    build_closed_loop_svg=cl.closed_loop_builder_svg,
    tf_controller=r"C(s) = ...",
)

CONTROLLER_SPECS = {
    ControllerType.PI: pi_spec,
    ControllerType.PID: pid_spec,
    ControllerType.FFPID: ff_pid_spec,
    ControllerType.EXAMPLE: example_spec,
}
```

`param_names`, default bounds, controller formulas, block-diagram builders, and the controller implementation must stay
in the same parameter order.

### 6. Implement the Time-Domain Controller

Time-domain PSO simulation is implemented in:

```text
src/app_domain/pso_objective/time_domain_numba.py
```

Every controller step function must use the shared signature:

```python
@njit(inline="always")
def example_step(
    state: np.ndarray,
    i: int,
    r: float,
    e: float,
    dt: float,
    controller_param: np.ndarray,
    u_min: float,
    u_max: float,
    anti_windup_method: int,
    ka: float,
) -> float:
    ...
```

The `state` array stores controller-internal dynamic state for each particle or simulation instance. The current shared
state layout is:

```python
STATE_E_PREV = 0
STATE_INTEGRAL = 1
STATE_D_FILTERED = 2

N_CONTROLLER_STATE = 3
```

If a new controller requires additional time-dependent state, extend `N_CONTROLLER_STATE` and define named state indices
so the simulation and Numba compilation remain consistent.

### 7. Register the Controller in the Simulation Core

Register the step function in `CONTROLLER_REGISTRY`:

```python
CONTROLLER_REGISTRY = {
    ControllerType.PI: ControllerRegistry(step_fn=pi_step),
    ControllerType.PID: ControllerRegistry(step_fn=pid_step),
    ControllerType.FFPID: ControllerRegistry(step_fn=ff_pid_step),
    ControllerType.EXAMPLE: ControllerRegistry(step_fn=example_step),
}
```

Even controllers that do not use the reference value directly must still accept `r` in the function signature so the
generic simulation core can call all controllers uniformly.

## Notes for Maintainers

- Some source files still contain legacy names such as `controller_sepc.py`; update imports carefully if renaming.
- Runtime logs are written under `src/logs/`.
- Temporary generated resources are written under `src/resources/temp/`.

## Authors

- Florin Büchi
- Thomas Stähli

## Acknowledgments

This project was developed under the supervision of Prof. Dr. Roland Büchi.
