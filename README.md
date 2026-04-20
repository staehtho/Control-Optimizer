# Control-Optimizer

`Control-Optimizer` is a desktop application for modeling dynamic plants, configuring controllers, and evaluating
control performance through simulation and particle swarm optimization (PSO).  
The `src/` codebase follows a layered MVVM-style architecture built on **PySide6**, separating numerical control logic,
application state, background computation, and presentation concerns.

The application provides an interactive workflow for:

- Defining transfer-function-based dynamic systems
- Tuning controller parameters PSO
- Analyzing time-domain and frequency-domain behavior
- Exporting project data and generating reports

---

# 🌍 Internationalization (i18n)

The project includes a PowerShell-based i18n build pipeline for managing translations using **PySide6**.

Languages are configured in: `src/config/languages.json`.
To add a new language, add its language code to the `languages` array in that JSON file. To remove a language, delete
its code from the same array.

## 📌 Overview

The script:

- Scans the source code for translatable strings  
- Updates `.ts` translation files  
- Opens **Qt Linguist** if new strings are detected  
- Compiles `.qm` files for runtime use  
- Keeps translation files in sync with the configuration  

---

## ▶️ Usage

From the project root:


```powershell
cd src
.\i18n\build-i18n.ps1
```

---

# 📁 Source Structure

The application source code lives in `src/` and is organized around a PySide6 MVVM-style architecture.

## Entry Point

- `src/main.py`: application bootstrap, splash screen, logging setup, temp/output directory initialization, `AppEngine`
  creation, and main window startup.

## Core Application Composition

- `src/app_domain/app_engine.py`: central composition root. It creates the `SimulationService`, owns the
  `ModelContainer`, lazily builds ViewModels, and handles warmup, project save/load, and shutdown.
- `src/app_domain/ui_context.py`: shared UI context used across views for settings, theme, and language access.

## Domain Logic

- `src/app_domain/controlsys/`: control-system logic such as plants, closed-loop behavior, PID handling, metrics, enums,
  and PSO-oriented optimization helpers.
- `src/app_domain/engine/`: numerical and simulation engines for transfer functions, frequency response, plant response,
  closed-loop response, and PSO execution.
- `src/app_domain/functions/`: excitation/input signal implementations such as step, sine, cosine, rectangular, and
  noise functions.
- `src/app_domain/PSO/`: particle swarm optimization primitives.

## State and Shared Types

- `src/models/`: application models for plant, controller, PSO configuration, simulation state, settings, and data
  management.
- `src/models/model_container.py`: aggregates the main models and provides import/export of project state.
- `src/app_types/`: typed data structures, enums, plotting payloads, navigation items, reporting payloads, and
  validation results shared across layers.

## Services and Infrastructure

- `src/service/`: orchestration services, including simulation and report generation.
- `src/service/reporting/`: report builders and report sections for generated output.
- `src/infrastructure/`: worker classes that run heavier computations outside the UI thread.

## Presentation Layer

- `src/viewmodels/`: ViewModels that connect UI widgets to models and services.
- `src/views/`: top-level screens such as plant setup, excitation function, controller setup, PSO configuration,
  evaluation, simulation, data management, and settings.
- `src/views/widgets/`: reusable custom widgets used by multiple screens.
- `src/views/view_helpers/`: helper utilities for layout, icons, widget binding, and validation.
- `src/views/translations/`: UI-facing translation helpers for enums and labels.

## Configuration and Assets

- `src/config/`: runtime configuration such as available languages and QSS themes.
- `src/resources/`: static assets including icons, SVG block-diagram parts, and resource helpers.
- `src/i18n/`: Qt translation source files (`.ts`), compiled translation files (`.qm`), and the i18n build script.
- `src/settings/settings.ini`: persisted local application settings.
- `src/logs/`: runtime log output.

# ▶️ Typical Runtime Flow

1. `main.py` creates the Qt application and initializes logging and temporary output paths.
2. `AppEngine` wires models, services, and lazy ViewModel factories together.
3. `MainView` builds the navigation shell and loads screen factories.
4. Views interact with ViewModels, which read/write models and trigger background simulation workers through the service
   layer.
5. Results are pushed back into plots, evaluation screens, simulation views, and reporting/data-management features.

# 📦 Summary

Control-Optimizer provides a structured, extensible environment for control-system modeling, simulation, and
optimization.
Its MVVM architecture, modular domain logic, and integrated i18n pipeline make it suitable for both research and
production-grade control engineering workflows.