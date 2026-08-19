from __future__ import annotations

import re
from pathlib import Path


ARIS_ADAPTER_KIND = "aris_estimator_predict"
DEEPSCIENTIST_ADAPTER_KIND = "deepscientist_weights_predict"
DRCLAW_ADAPTER_KIND = "drclaw_build_estimator_predict"


def _normalize_framework_hint(framework_hint: str | None) -> str | None:
    if framework_hint is None:
        return None
    normalized = framework_hint.strip().lower().replace(".", "").replace("_", "").replace("-", "").replace(" ", "")
    aliases = {
        "03": "03",
        "aris": "03",
        "05": "05",
        "deepscientist": "05",
        "06": "06",
        "drclaw": "06",
    }
    return aliases.get(normalized)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _scan_file(path: Path, framework_hint: str | None) -> dict[str, object] | None:
    if not path.exists():
        return None

    resolved_path = path.resolve()
    text = _read_text(path)
    normalized_hint = _normalize_framework_hint(framework_hint)
    if normalized_hint == "03" and "class Estimator" in text and re.search(
        r"def\s+predict\s*\(\s*self\s*,\s*mlp\b",
        text,
    ):
        return {
            "adapter_kind": ARIS_ADAPTER_KIND,
            "framework_hint": normalized_hint,
            "workspace": resolved_path.parent,
            "source_path": resolved_path,
            "source_symbol": "Estimator",
        }
    if normalized_hint == "05" and re.search(
        r"class\s+(WhiteBoxEstimator|DiagonalMomentEstimator|WeightsOnlyEstimator|Estimator)\b",
        text,
    ):
        source_symbol = next(
            (name for name in ("WhiteBoxEstimator", "DiagonalMomentEstimator", "WeightsOnlyEstimator", "Estimator") if f"class {name}" in text),
            "Estimator",
        )
        predict_input = None
        if re.search(r"def\s+predict\s*\(\s*self\s*,\s*weights\b", text):
            predict_input = "weights"
        elif re.search(r"def\s+predict\s*\(\s*self\s*,\s*mlp\b", text):
            predict_input = "mlp"
        if predict_input is None:
            return None
        return {
            "adapter_kind": DEEPSCIENTIST_ADAPTER_KIND,
            "framework_hint": normalized_hint,
            "workspace": resolved_path.parent,
            "source_path": resolved_path,
            "source_symbol": source_symbol,
            "predict_input": predict_input,
        }
    if normalized_hint == "06" and "def build_estimator" in text:
        predict_input = None
        if re.search(r"def\s+predict\s*\(\s*self\s*,\s*mlp\b", text):
            predict_input = "mlp"
        elif re.search(r"def\s+predict\s*\(\s*self\s*,\s*weights\b", text):
            predict_input = "weights"
        if predict_input is None:
            return None
        return {
            "adapter_kind": DRCLAW_ADAPTER_KIND,
            "framework_hint": normalized_hint,
            "workspace": resolved_path.parent,
            "source_path": resolved_path,
            "source_symbol": "build_estimator",
            "predict_input": predict_input,
        }
    return None


def scan_workspace_for_official_adapter(workspace: Path, framework_hint: str | None = None) -> dict[str, object]:
    normalized_hint = _normalize_framework_hint(framework_hint)
    if normalized_hint not in {"03", "05", "06"}:
        raise ValueError(f"no supported official adapter candidate found under {workspace}")

    workspace = workspace.resolve()
    source_path = workspace / "estimator.py"
    result = _scan_file(source_path, normalized_hint)
    if result is not None:
        result["workspace"] = workspace
        return result
    raise ValueError(f"no supported official adapter candidate found under {workspace}")


def _render_adapter(scan_result: dict[str, object]) -> str:
    source_path = Path(scan_result["source_path"])
    adapter_kind = str(scan_result["adapter_kind"])
    scipy_fallback = """
import math
import types


def _install_scipy_special_erf_fallback():
    if "scipy.special" in sys.modules:
        return
    scipy_module = sys.modules.get("scipy")
    if scipy_module is None:
        scipy_module = types.ModuleType("scipy")
        sys.modules["scipy"] = scipy_module
    special_module = types.ModuleType("scipy.special")

    def erf(values):
        try:
            import numpy as _np

            return _np.vectorize(math.erf)(values)
        except Exception:
            if isinstance(values, (list, tuple)):
                return [math.erf(value) for value in values]
            return math.erf(values)

    special_module.erf = erf
    scipy_module.special = special_module
    sys.modules["scipy.special"] = special_module


_install_scipy_special_erf_fallback()
"""

    if adapter_kind == ARIS_ADAPTER_KIND:
        return f"""from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from whestbench import BaseEstimator

_SOURCE = Path({str(source_path)!r})
_SPEC = importlib.util.spec_from_file_location("framework_estimator", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class OfficialAdapterEstimator(BaseEstimator):
    def __init__(self) -> None:
        self._impl = _MODULE.Estimator()

    def predict(self, mlp, budget=None):
        return self._impl.predict(mlp, budget=budget)
"""

    if adapter_kind == DEEPSCIENTIST_ADAPTER_KIND:
        source_symbol = str(scan_result["source_symbol"])
        predict_input = str(scan_result.get("predict_input", "weights"))
        predict_body = """        weights = mlp.weights
        module_np = getattr(_MODULE, "np", None)
        if module_np is not None and hasattr(module_np, "asarray"):
            weights = module_np.asarray(weights)
        return self._impl.predict(weights)"""
        if predict_input == "mlp":
            predict_body = "        return self._impl.predict(mlp, budget=budget)"
        return f"""from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from whestbench import BaseEstimator
{scipy_fallback}

_SOURCE = Path({str(source_path)!r})
_SPEC = importlib.util.spec_from_file_location("framework_estimator", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class OfficialAdapterEstimator(BaseEstimator):
    def __init__(self) -> None:
        self._impl = getattr(_MODULE, {source_symbol!r})()

    def predict(self, mlp, budget=None):
{predict_body}
"""

    if adapter_kind == DRCLAW_ADAPTER_KIND:
        predict_input = str(scan_result.get("predict_input", "mlp"))
        body = "return self._impl.predict(mlp, budget=budget)"
        if predict_input == "weights":
            body = "return self._impl.predict(mlp.weights, budget=budget)"
        return f"""from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from whestbench import BaseEstimator

_SOURCE = Path({str(source_path)!r})
_SPEC = importlib.util.spec_from_file_location("framework_estimator", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class OfficialAdapterEstimator(BaseEstimator):
    def __init__(self) -> None:
        self._impl = _MODULE.build_estimator()

    def predict(self, mlp, budget=None):
        {body}
"""

    raise ValueError(f"unsupported adapter kind: {adapter_kind}")


def materialize_official_adapter(scan_result: dict[str, object], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "estimator.py"
    path.write_text(_render_adapter(scan_result), encoding="utf-8")
    return path
