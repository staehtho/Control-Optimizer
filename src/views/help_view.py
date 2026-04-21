from __future__ import annotations
from typing import TYPE_CHECKING

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout

from app_types import NavLabels
from resources.resources import Icons
from views.view_mixin import ViewMixin

if TYPE_CHECKING:
    from app_domain import UiContext
    from views.widgets import SectionFrame

# TODO: following feature are to describe
#   Data Management -> Json and Report

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
        main_layout.addStretch()

        self.setLayout(main_layout)

    def _create_pso_frame(self) -> SectionFrame:
        frame: SectionFrame
        frame, layout = self._create_card(parent=self)

        self._lbl_pso_help = QLabel(self)
        self._lbl_pso_help.setWordWrap(True)
        layout.addWidget(self._lbl_pso_help)

        return frame

    # ============================================================
    # Translation
    # ============================================================
    def _retranslate(self) -> None:
        """Update all UI texts after a language change."""
        self._lbl_title.setText(self._enum_translation(NavLabels.HELP))
        self._frm_pso.setText(self.tr("Particle Swarm Optimization (PSO)"))

        self._lbl_pso_help.setText((
            """
            <p>
                PSO is a population-based optimization method inspired by swarm behavior.
                Each particle represents one candidate solution and moves through the
                parameter space using:
            </p>
            
            <ul>
                <li><b>Inertia</b> – keeps the previous movement direction</li>
                <li><b>Cognitive influence</b> – moves toward the particle’s own best</li>
                <li><b>Social influence</b> – moves toward the neighborhood best</li>
            </ul>
            
            <p><b>Feasibility-Aware Comparison</b></p>
            <p>
                Your implementation always prefers feasible solutions. Among infeasible
                solutions, smaller violation is better. Among feasible solutions, smaller
                performance value is better.
            </p>
            
            <p><b>Hyperparameters (Configurable in Settings)</b></p>
            
            <ul>
                <li><b>Swarm Size:</b> More particles improve exploration but increase runtime.</li>
                <li><b>Randomness:</b> Controls stochasticity; higher values increase exploration.</li>
                <li><b>Inertia Weight:</b> Balances exploration vs. convergence.</li>
                <li><b>Cognitive Coefficient (c1):</b> Attraction to the particle’s own best.</li>
                <li><b>Social Coefficient (c2):</b> Attraction to the neighborhood best.</li>
                <li><b>Neighborhood Size:</b> Controls how many neighbors influence a particle.</li>
                <li><b>Initial Swarm Span:</b> Defines the initial distribution of particles.</li>
                <li><b>Max Iterations:</b> Hard stop for the optimization.</li>
                <li><b>Max Stall / Stall Windows:</b> Convergence detection based on improvement.</li>
                <li><b>Space Factor:</b> Stops when the particle space collapses.</li>
                <li><b>Convergence Factor:</b> Minimum improvement required to continue.</li>
            
                <li><b>Repeat Runs:</b> Runs the entire PSO algorithm multiple times with different
                    random initializations. This improves robustness and reduces the chance of
                    getting stuck in local minima. The best solution across all runs is selected
                    as the final result.</li>
            </ul>
            
            <p>
                These parameters influence how aggressively or cautiously the swarm explores
                the parameter space and how quickly it converges.
            </p>
            """
        ))
