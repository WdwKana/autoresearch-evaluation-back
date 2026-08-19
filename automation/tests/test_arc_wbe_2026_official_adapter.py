from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(ROOT / "automation" / "scripts"))

from arc_wbe_2026_official_adapter import (  # noqa: E402
    materialize_official_adapter,
    scan_workspace_for_official_adapter,
)


def _load_generated_adapter(path: Path):
    module_name = f"generated_adapter_{path.parent.name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _install_whestbench_stub() -> None:
    whestbench_module = types.ModuleType("whestbench")

    class BaseEstimator:
        pass

    whestbench_module.BaseEstimator = BaseEstimator
    sys.modules["whestbench"] = whestbench_module
    return whestbench_module


def test_scan_workspace_detects_aris_estimator(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n    def predict(self, mlp, budget=None):\n        return mlp.weights\n",
        encoding="utf-8",
    )

    result = scan_workspace_for_official_adapter(workspace, framework_hint="03")

    assert result["adapter_kind"] == "aris_estimator_predict"
    assert result["source_path"] == workspace / "estimator.py"


def test_scan_workspace_detects_drclaw_estimator(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class DiagonalGaussianEstimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        return mlp.weights\n"
        "\n"
        "def build_estimator():\n"
        "    return DiagonalGaussianEstimator()\n",
        encoding="utf-8",
    )

    result = scan_workspace_for_official_adapter(workspace, framework_hint="06")

    assert result["adapter_kind"] == "drclaw_build_estimator_predict"
    assert result["source_path"] == workspace / "estimator.py"


def test_scan_workspace_detects_deepscientist_diagonal_moment_estimator(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class DiagonalMomentEstimator:\n    def predict(self, weights):\n        return weights\n",
        encoding="utf-8",
    )

    result = scan_workspace_for_official_adapter(workspace, framework_hint="05")

    assert result["adapter_kind"] == "deepscientist_weights_predict"
    assert result["source_path"] == workspace / "estimator.py"
    assert result["source_symbol"] == "DiagonalMomentEstimator"
    assert result["predict_input"] == "weights"


def test_scan_workspace_detects_deepscientist_diagonal_moment_estimator_with_mlp_signature(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class DiagonalMomentEstimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        return mlp.weights\n",
        encoding="utf-8",
    )

    result = scan_workspace_for_official_adapter(workspace, framework_hint="05")

    assert result["adapter_kind"] == "deepscientist_weights_predict"
    assert result["source_symbol"] == "DiagonalMomentEstimator"
    assert result["predict_input"] == "mlp"


def test_scan_workspace_accepts_framework_name_aliases(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n    def predict(self, mlp, budget=None):\n        return mlp.weights\n",
        encoding="utf-8",
    )

    result = scan_workspace_for_official_adapter(workspace, framework_hint="ARIS")

    assert result["adapter_kind"] == "aris_estimator_predict"


def test_scan_workspace_detects_evoscientist_builder(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n"
        "    def predict(self, mlp):\n"
        "        return mlp.weights\n"
        "\n"
        "def build_estimator():\n"
        "    return Estimator()\n",
        encoding="utf-8",
    )

    result = scan_workspace_for_official_adapter(workspace, framework_hint="EvoScientist")

    assert result["adapter_kind"] == "generic_native_estimator_predict"
    assert result["source_symbol"] == "build_estimator"


def test_scan_workspace_detects_aris_estimator_with_typed_predict_signature(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "from typing import Any\n\n"
        "class Estimator:\n"
        "    def predict(self, mlp: Any, budget: int | None = None):\n"
        "        return mlp.weights\n",
        encoding="utf-8",
    )

    result = scan_workspace_for_official_adapter(workspace, framework_hint="03")

    assert result["adapter_kind"] == "aris_estimator_predict"
    assert result["source_path"] == workspace / "estimator.py"


def test_scan_workspace_records_absolute_source_path_from_relative_workspace(
    tmp_path: Path, monkeypatch
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n    def predict(self, mlp, budget=None):\n        return mlp.weights\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = scan_workspace_for_official_adapter(Path("workspace"), framework_hint="03")

    assert result["source_path"] == (workspace / "estimator.py").resolve()


def test_scan_workspace_does_not_infer_framework_without_hint(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n    def predict(self, mlp, budget=None):\n        return mlp.weights\n",
        encoding="utf-8",
    )

    try:
        scan_workspace_for_official_adapter(workspace)
    except ValueError as exc:
        assert "no supported official adapter candidate found" in str(exc)
    else:
        raise AssertionError(
            "expected scan_workspace_for_official_adapter to reject missing framework_hint"
        )


def test_scan_workspace_ignores_nested_estimator_files(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "nested"
    nested.mkdir(parents=True)
    (nested / "estimator.py").write_text(
        "class Estimator:\n    def predict(self, mlp, budget=None):\n        return mlp.weights\n",
        encoding="utf-8",
    )

    try:
        scan_workspace_for_official_adapter(workspace, framework_hint="03")
    except ValueError as exc:
        assert "no supported official adapter candidate found" in str(exc)
    else:
        raise AssertionError(
            "expected scan_workspace_for_official_adapter to ignore nested estimator.py"
        )


def test_scan_workspace_rejects_literal_zero_estimator(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "import numpy as np\n\n"
        "class Estimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        return np.zeros((mlp.depth, mlp.width))\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="placeholder constant prediction"):
        scan_workspace_for_official_adapter(workspace, framework_hint="03")


@pytest.mark.parametrize(
    ("prediction", "message"),
    [
        ("[[0.0, 0.0], [0.0, 0.0]]", "all-zero placeholder"),
        ("[[1.0, 1.0], [2.0, 2.0]]", "width-broadcast"),
        ("[[1.0, 2.0], [1.0, 2.0]]", "depth-broadcast"),
    ],
)
def test_generated_adapter_rejects_runtime_placeholder_predictions(
    tmp_path: Path,
    prediction: str,
    message: str,
) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class Estimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        f"        return {prediction}\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="03")
    adapter_path = materialize_official_adapter(scan_result, output_dir)
    _install_whestbench_stub()
    adapter = _load_generated_adapter(adapter_path).OfficialAdapterEstimator()

    class MLP:
        depth = 2
        width = 2
        weights = [[[1.0]]]

    with pytest.raises(ValueError, match=message):
        adapter.predict(MLP())


def test_materialize_official_adapter_creates_python_entrypoint(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "init_calls = 0\n"
        "predict_calls = 0\n"
        "last_budget = None\n"
        "\n"
        "class Estimator:\n"
        "    def __init__(self):\n"
        "        global init_calls\n"
        "        init_calls += 1\n"
        "\n"
        "    def predict(self, mlp, budget=None):\n"
        "        global predict_calls, last_budget\n"
        "        predict_calls += 1\n"
        "        last_budget = budget\n"
        '        return {"weights": mlp.weights, "budget": budget}\n',
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="03")

    adapter_path = materialize_official_adapter(scan_result, output_dir)

    assert adapter_path == output_dir / "estimator.py"
    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [1, 2, 3]

    mlp = MLP()
    result = adapter.predict(mlp, budget=7)
    again = adapter.predict(mlp, budget=8)

    assert result == {"weights": [1, 2, 3], "budget": 7}
    assert again == {"weights": [1, 2, 3], "budget": 8}
    assert module._MODULE.init_calls == 1
    assert module._MODULE.predict_calls == 2
    assert module._MODULE.last_budget == 8
    assert str((workspace / "estimator.py").resolve()) in adapter_path.read_text(encoding="utf-8")


def test_materialize_official_adapter_loads_dataclass_based_estimator_module(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "from __future__ import annotations\n\n"
        "from dataclasses import dataclass\n\n"
        "@dataclass\n"
        "class MLPRecord:\n"
        "    weights: list[int]\n\n"
        "class Estimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        return MLPRecord(weights=mlp.weights).weights\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="03")
    adapter_path = materialize_official_adapter(scan_result, output_dir)

    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [1, 2, 3]

    assert adapter.predict(MLP()) == [1, 2, 3]


def test_materialize_official_adapter_creates_deepscientist_entrypoint(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "init_calls = 0\n"
        "predict_calls = 0\n"
        "last_weights = None\n"
        "\n"
        "class WhiteBoxEstimator:\n"
        "    def __init__(self):\n"
        "        global init_calls\n"
        "        init_calls += 1\n"
        "\n"
        "    def predict(self, weights):\n"
        "        global predict_calls, last_weights\n"
        "        predict_calls += 1\n"
        "        last_weights = weights\n"
        "        return weights\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="05")

    adapter_path = materialize_official_adapter(scan_result, output_dir)

    assert adapter_path == output_dir / "estimator.py"
    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [4, 5, 6]

    mlp = MLP()
    result = adapter.predict(mlp)
    again = adapter.predict(mlp)

    assert result == [4, 5, 6]
    assert again == [4, 5, 6]
    assert module._MODULE.init_calls == 1
    assert module._MODULE.predict_calls == 2
    assert str((workspace / "estimator.py").resolve()) in adapter_path.read_text(encoding="utf-8")


def test_materialize_official_adapter_creates_drclaw_entrypoint(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "build_calls = 0\n"
        "predict_calls = 0\n"
        "last_budget = None\n"
        "\n"
        "class DiagonalGaussianEstimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        global predict_calls, last_budget\n"
        "        predict_calls += 1\n"
        "        last_budget = budget\n"
        '        return {"weights": mlp.weights, "budget": budget}\n'
        "\n"
        "def build_estimator():\n"
        "    global build_calls\n"
        "    build_calls += 1\n"
        "    return DiagonalGaussianEstimator()\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="06")

    adapter_path = materialize_official_adapter(scan_result, output_dir)

    assert adapter_path == output_dir / "estimator.py"
    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [7, 8, 9]

    mlp = MLP()
    result = adapter.predict(mlp, budget=11)
    again = adapter.predict(mlp, budget=12)

    assert result == {"weights": [7, 8, 9], "budget": 11}
    assert again == {"weights": [7, 8, 9], "budget": 12}
    assert module._MODULE.build_calls == 1
    assert module._MODULE.predict_calls == 2
    assert module._MODULE.last_budget == 12
    assert str((workspace / "estimator.py").resolve()) in adapter_path.read_text(encoding="utf-8")


def test_materialize_official_adapter_adapts_drclaw_weights_predict_signature(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "build_calls = 0\n"
        "predict_calls = 0\n"
        "last_weights = None\n"
        "last_budget = None\n"
        "\n"
        "class DiagonalGaussianEstimator:\n"
        "    def predict(self, weights, budget=None, seed=None, return_stats=False):\n"
        "        global predict_calls, last_weights, last_budget\n"
        "        predict_calls += 1\n"
        "        last_weights = weights\n"
        "        last_budget = budget\n"
        "        return weights\n"
        "\n"
        "def build_estimator():\n"
        "    global build_calls\n"
        "    build_calls += 1\n"
        "    return DiagonalGaussianEstimator()\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="06")
    adapter_path = materialize_official_adapter(scan_result, output_dir)

    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [7, 8, 9]

    result = adapter.predict(MLP(), budget=13)

    assert result == [7, 8, 9]
    assert module._MODULE.build_calls == 1
    assert module._MODULE.predict_calls == 1
    assert module._MODULE.last_weights == [7, 8, 9]
    assert module._MODULE.last_budget == 13


def test_materialize_official_adapter_converts_deepscientist_weights_to_ndarray(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "class _Array:\n"
        "    def __init__(self, values):\n"
        "        self._values = values\n"
        "        self.shape = (len(values), len(values[0]))\n"
        "\n"
        "class np:\n"
        "    @staticmethod\n"
        "    def asarray(values):\n"
        "        return _Array(values)\n"
        "\n"
        "class WhiteBoxEstimator:\n"
        "    def predict(self, weights):\n"
        "        return weights.shape\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="05")
    adapter_path = materialize_official_adapter(scan_result, output_dir)

    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [[1, 2], [3, 4]]

    assert adapter.predict(MLP()) == (2, 2)


def test_materialize_official_adapter_keeps_deepscientist_mlp_signature(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "predict_calls = 0\n"
        "last_budget = None\n"
        "\n"
        "class DiagonalMomentEstimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        global predict_calls, last_budget\n"
        "        predict_calls += 1\n"
        "        last_budget = budget\n"
        "        return mlp.weights\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="05")
    adapter_path = materialize_official_adapter(scan_result, output_dir)

    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [1, 2, 3]

    assert adapter.predict(MLP(), budget=9) == [1, 2, 3]
    assert module._MODULE.predict_calls == 1
    assert module._MODULE.last_budget == 9


def test_materialize_official_adapter_provides_scipy_erf_fallback_for_deepscientist(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    output_dir = tmp_path / "generated"
    workspace.mkdir()
    (workspace / "estimator.py").write_text(
        "from scipy.special import erf\n"
        "\n"
        "class DiagonalMomentEstimator:\n"
        "    def predict(self, mlp, budget=None):\n"
        "        return erf(mlp.weights)\n",
        encoding="utf-8",
    )
    scan_result = scan_workspace_for_official_adapter(workspace, framework_hint="05")
    adapter_path = materialize_official_adapter(scan_result, output_dir)

    sys.modules.pop("scipy", None)
    sys.modules.pop("scipy.special", None)
    _install_whestbench_stub()
    module = _load_generated_adapter(adapter_path)
    adapter = module.OfficialAdapterEstimator()

    class MLP:
        def __init__(self) -> None:
            self.weights = [0.0]

    result = adapter.predict(MLP(), budget=1)
    assert float(result[0]) == 0.0
