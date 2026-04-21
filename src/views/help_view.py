from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout

from app_types import NavLabels
from resources.resources import Icons
from views.view_mixin import ViewMixin

if TYPE_CHECKING:
    from app_domain import UiContext
    from views.widgets import SectionFrame


class HelpView(ViewMixin, QWidget):
    def __init__(self, ui_context: UiContext, parent: QWidget = None):
        QWidget.__init__(self, parent)

        ViewMixin.__init__(self, ui_context)

    # ============================================================
    # UI Initialization
    # ============================================================
    def _init_ui(self) -> None:
        """Create and configure all UI components."""
        main_layout = self._create_page_layout()

        # Title row (icon + title)
        icon = self._load_icon(Icons.help, self._title_icon_size)
        self._label_icon = QLabel(self)
        self._label_icon.setPixmap(icon.pixmap(self._title_icon_size, self._title_icon_size))
        self._label_icon.setFixedSize(self._title_icon_size, self._title_icon_size)

        self._lbl_title = QLabel(self)
        self._lbl_title.setObjectName("viewTitle")

        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(10)
        title_layout.addWidget(self._label_icon)
        title_layout.addWidget(self._lbl_title)
        title_layout.addStretch()
        main_layout.addLayout(title_layout)

        self._frm_pso = self._create_pso_frame()
        main_layout.addWidget(self._frm_pso)

        self._frm_report = self._create_report_frame()
        main_layout.addWidget(self._frm_report)

        self._frm_imp_exp = self._create_import_export_frame()
        main_layout.addWidget(self._frm_imp_exp)

        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_pso_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card(parent=self)

        self._lbl_pso_help = QLabel(self)
        self._lbl_pso_help.setWordWrap(True)
        layout.addWidget(self._lbl_pso_help)

        return frame

    def _create_report_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card(parent=self)

        self._lbl_report_help = QLabel(self)
        self._lbl_report_help.setWordWrap(True)
        layout.addWidget(self._lbl_report_help)

        return frame

    def _create_import_export_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card(parent=self)

        self._lbl_imp_exp_help = QLabel(self)
        self._lbl_imp_exp_help.setWordWrap(True)
        layout.addWidget(self._lbl_imp_exp_help)

        return frame

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self._enum_translation(NavLabels.HELP))
        self._frm_pso.setText(self.tr("Particle Swarm Optimization (PSO)"))
        self._frm_imp_exp.setText(self.tr("Import and Export of Application Data"))
        self._frm_report.setText(self.tr("Report Generation (Dynamic Report)"))

        self._lbl_pso_help.setText(self.tr(
            """<p>
            Particle Swarm Optimization is a population-based optimization method inspired by the
            collective motion of natural swarms. Each particle represents a candidate solution in
            the parameter space and updates its position according to a combination of inertia,
            individual learning, and social learning. This mechanism enables an adaptive balance
            between exploration of the search space and convergence toward promising regions.
            </p>
            
            <p>
            Candidate evaluation follows a feasibility-aware lexicographic criterion. Feasible
            solutions are always preferred over infeasible ones. Among infeasible candidates, the
            solution with the smaller total constraint violation is considered superior. Among
            feasible candidates, the solution with the lower performance value is preferred. This
            approach ensures robustness with respect to constraints while enabling precise
            fine‑tuning within the feasible region.
            </p>
            
            <p><b>Hyperparameters (configurable in the settings)</b></p>
            
            <ul>
            <li>
            <b>Repeat runs:</b> Executes the entire PSO procedure multiple times with different
            random initializations. This increases robustness and reduces the likelihood of
            converging to local minima. The best solution across all runs is selected as the final
            result.
            </li>
            
            <li>
            <b>Swarm size:</b> Specifies the number of particles in the swarm. Larger populations
            provide broader coverage of the search space but increase computational cost.
            </li>
            
            <li>
            <b>Randomness factor:</b> Controls the stochastic component of the velocity update.
            Higher values promote exploration, whereas lower values support more stable convergence.
            </li>
            
            <li>
            <b>Initial range:</b> Define the admissible range
            for the inertia weight. The inertia weight determines the influence of the previous
            velocity and is adaptively adjusted within this interval.
            </li>
            
            <li>
            <b>Cognitive factor (u1):</b> Determines the strength of the particle’s attraction
            toward its own best-known position.
            </li>
            
            <li>
            <b>Social factor (u2):</b> Determines the strength of the attraction toward the best
            position found within the dynamically selected neighborhood.
            </li>
            
            <li>
            <b>Initial swarm span:</b> Specifies the initial spatial distribution of particles
            within the parameter bounds. A larger span results in a broader initialization and
            therefore stronger exploration.
            </li>
            
            <li>
            <b>Min. neighbors fraction:</b> Defines the minimum fraction of the swarm considered as
            the local neighborhood. Smaller neighborhoods increase diversity, while larger
            neighborhoods accelerate convergence.
            </li>
            
            <li>
            <b>Max stall:</b> Indicates how many iterations without significant improvement are
            allowed before a stall window is detected.
            </li>
            
            <li>
            <b>Required stall windows:</b> Specifies how many consecutive stall windows must occur
            before the optimization process is terminated.
            </li>
            
            <li>
            <b>Max iterations:</b> Sets a hard upper limit on the number of iterations performed
            during a single PSO run.
            </li>
            
            <li>
            <b>Search space factor:</b> Terminates the optimization once the hypervolume spanned by
            the swarm falls below a defined fraction of the initial search space, indicating spatial
            convergence.
            </li>
            
            <li>
            <b>Convergence factor:</b> Defines the minimum relative improvement required within a
            stall window for the optimization to continue.
            </li>
            </ul>
            
            <li>
            Together, these parameters govern the exploratory behavior, convergence dynamics, and
            overall robustness of the PSO algorithm.
            </li>"""
        ))

        self._lbl_imp_exp_help.setText(self.tr(
            """<p>
            The Data Management module provides functionality for importing and exporting complete
            application states. This mechanism enables users to archive, transfer, or restore
            projects in a reproducible manner. All relevant configuration data are stored in a
            single JSON file, ensuring transparency and long-term accessibility.
            </p>
            
            <p>
            During export, the application serializes the current project into a structured JSON
            representation. This file contains all essential model parameters, including the plant
            definition, excitation function settings, controller configuration, PSO configuration,
            and the solver settings defined in the Settings. The exported file therefore
            captures the full state of the optimization environment and can be used to reproduce
            results or continue work on another system.
            </p>
            
            <p>
            During import, the application reads a previously exported JSON file and restores the
            entire project state. All parameters are reloaded into their corresponding models,
            including PSO hyperparameters and solver settings. This ensures that imported projects
            behave identically to the original environment from which they were exported.
            </p>"""
        ))

        self._lbl_report_help.setText(self.tr(
            """<p>
            The reporting functionality enables the creation of a comprehensive dynamic report that
            summarizes all relevant aspects of a completed PSO-based controller optimization. The
            report is generated as a PDF document and integrates both numerical results and
            graphical representations of the system behaviour.
            </p>
            
            <p>
            Each section of the report is generated dynamically based on two primary data sources:
            the <i>simulation snapshot</i> and the <i>PSO result</i>. The simulation snapshot
            captures the complete configuration state at the moment the PSO simulation is executed.
            It includes the plant model, the excitation function, the controller configuration, the
            PSO parameter bounds, and all constraint settings used during the optimization. In
            addition, the snapshot contains the simulation time interval, the excitation target, and
            all active time‑domain and frequency‑domain performance criteria. It therefore
            represents a precise and immutable record of the conditions under which the optimization
            was performed.
            </p>
            
            <p>
            The PSO result complements the snapshot by providing the optimized controller
            parameters, feasibility information, recommended sampling rate, and the evaluated
            performance metrics obtained from the best particle. Together, the snapshot and the
            result form a complete description of both the optimization setup and its outcome.
            </p>
            
            <p>
            The report is assembled from modular sections that reflect the user’s selection in the
            Data Management. Depending on the chosen configuration, the report may include the
            plant model, the excitation function, the controller configuration, the PSO
            configuration, the optimization results, and a set of diagnostic plots such as the block
            diagram, time-domain response, Bode plot, and transfer functions.
            </p>"""
        ))
