"""
A labeled float slider row, and a panel of them for one enhancement
method's tunable parameters (currently: Adaptive Grading / gray_world).
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider


def _humanize(param_name):
    return param_name.replace("_", " ").title()


class ParamSlider(QWidget):
    """One parameter: a label+value header row above a full-width slider.

    QSlider only handles integers, so values are stored internally as
    slider ticks and converted to/from the real float range via `step`.
    """

    value_changed = pyqtSignal(str, float)  # param_name, new value

    def __init__(self, param_name, minimum, maximum, step, default):
        super().__init__()
        self.param_name = param_name
        self.step = step
        self._int_min = round(minimum / step)
        self._int_max = round(maximum / step)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        header = QHBoxLayout()
        label = QLabel(_humanize(param_name))
        label.setObjectName("sectionLabel")
        header.addWidget(label)
        header.addStretch()
        self.value_label = QLabel(f"{default:.2f}")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.value_label)
        layout.addLayout(header)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(self._int_min)
        self.slider.setMaximum(self._int_max)
        self.slider.setValue(round(default / step))
        self.slider.valueChanged.connect(self._on_slider_changed)
        # The handle is styled larger than the groove via a negative QSS
        # margin (see theme.py) to get a round grip instead of the default
        # thin tick -- that makes the handle paint outside the slider
        # widget's own (unchanged) allocated height, so its top edge was
        # getting clipped by the widget's own bounds. Needs a real height,
        # not just spacing from neighboring rows.
        self.slider.setFixedHeight(24)
        layout.addWidget(self.slider)

    def _on_slider_changed(self, int_value):
        value = int_value * self.step
        self.value_label.setText(f"{value:.2f}")
        self.value_changed.emit(self.param_name, value)

    def value(self):
        return self.slider.value() * self.step

    def set_value(self, value):
        self.slider.blockSignals(True)
        self.slider.setValue(round(value / self.step))
        self.slider.blockSignals(False)
        self.value_label.setText(f"{value:.2f}")


class EnhancementParamsPanel(QWidget):
    """A stack of ParamSlider rows built from a {name: (min, max, step)}
    spec dict, seeded with a {name: value} defaults dict."""

    params_changed = pyqtSignal()

    def __init__(self, param_specs, defaults):
        super().__init__()
        self._defaults = dict(defaults)
        self._sliders = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)
        # Deliberately generous: these rows sit in a narrow side panel
        # where cramped spacing made adjacent sliders hard to tell apart.
        layout.setSpacing(18)

        for name, (minimum, maximum, step) in param_specs.items():
            slider = ParamSlider(name, minimum, maximum, step, defaults.get(name, minimum))
            slider.value_changed.connect(lambda *_: self.params_changed.emit())
            layout.addWidget(slider)
            self._sliders[name] = slider

    def get_params(self):
        return {name: slider.value() for name, slider in self._sliders.items()}

    def set_params(self, params):
        for name, value in params.items():
            if name in self._sliders:
                self._sliders[name].set_value(value)

    def reset_to_defaults(self):
        self.set_params(self._defaults)
        self.params_changed.emit()
