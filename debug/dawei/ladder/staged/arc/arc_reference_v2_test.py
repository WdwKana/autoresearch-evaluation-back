import time, numpy as np
from scipy.stats import norm
from hf_dataset_reference import load_records, validation_records, local_validation, ground_truth, make_mlp
SCALE = 0.7
def relu_mean(mu, sigma):
    a = mu / np.maximum(sigma, 1e-12)
    return sigma * norm.pdf(a) + mu * norm.cdf(a)
class MeanFieldEstimator:
    def predict(self, mlp):
        out = np.zeros((mlp.depth, mlp.width)); mu = np.zeros(mlp.width); var = np.ones(mlp.width)
        for l, W in enumerate(mlp.weights):
            W = W.astype(np.float64); mz = mu @ W; vz = var @ (W ** 2)
            s = np.sqrt(vz); mu = relu_mean(mz, s); var = SCALE * (vz + mz ** 2) - mu ** 2 + 1e-9; var = np.maximum(var, 1e-9)
            out[l] = mu
        return out
t0 = time.time(); train = load_records(); print("train records", len(train), "load s", round(time.time() - t0, 1), "shape", train[0]["weights"].shape, "ids", train[0]["mlp_id"], train[-1]["mlp_id"])
t0 = time.time(); val = validation_records(); print("validation records", len(val), "load s", round(time.time() - t0, 1), "ids", val[0]["mlp_id"], val[-1]["mlp_id"])
print("truth shape", ground_truth(train[0]).shape, "mlp depth/width", make_mlp(train[0]).depth, make_mlp(train[0]).width)
local_validation("meanfield_obj", MeanFieldEstimator())        # object with a helper + constant + scipy import
local_validation("meanfield_cls", MeanFieldEstimator)          # class
open("zeros_est.py", "w").write("import numpy as np\nclass Estimator:\n    def predict(self, mlp):\n        return np.zeros((mlp.depth, mlp.width))\n")
local_validation("zeros_path", "zeros_est.py")                  # path
LOOKUP = ground_truth(train[0])[-1]                                # depends on loaded data -> cannot be packaged
class BadEstimator:
    def predict(self, mlp):
        return np.tile(LOOKUP, (mlp.depth, 1))
local_validation("bad_dependency", BadEstimator())
import json, glob
for f in sorted(glob.glob("working/*.validation.json")): d = json.load(open(f)); print(f, {k: d[k] for k in ("final_layer_mse", "submittable", "note")})
print("packaged head:", open("working/meanfield_obj.estimator.py").read()[:400].replace("\n", " | "))
