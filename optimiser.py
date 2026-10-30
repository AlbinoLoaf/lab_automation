import time
import numpy as np
from skopt import gp_minimize

DEFAULT_TARGET = [13, 19, 16, 2, 25, 637, 7, 13, 16, 14, 25, 637, 2, 10, 3, 6, 25, 636]

class ColorOptimizer:
    def __init__(self, controller, tracker=None, target=None):
        self.controller = controller
        self.tracker = tracker
        self.target = np.array(target if target else DEFAULT_TARGET, dtype=float)
        self.step = 0

    def evaluate(self, individual: list) -> float:
        self.step += 1
        dur_a, dur_b = int(individual[0]), int(individual[1])
        print(f"\n[Step {self.step}] Mixing -> Pump A: {dur_a}ms, Pump B: {dur_b}ms")

        self.controller.run_pump_by_params("a", True, dur_a)
        if self.tracker:
            self.tracker.add_usage("a", dur_a)

        self.controller.run_pump_by_params("b", True, dur_b)
        if self.tracker:
            self.tracker.add_usage("b", dur_b)

        time.sleep(1.0)
        readings = self.controller.read_sensor()
        if not readings or len(readings) != 18:
            print("Sensor error, returning high penalty.")
            return 1e9

        mse = float(np.mean((self.target - np.array(readings, dtype=float)) ** 2))
        print(f"[Step {self.step}] Result MSE: {mse:.2f}")

        self.controller.clean()
        return mse

    def run(self, calls: int = 10, init_points: int = 3):
        print(f"Optimizing for target: {self.target.tolist()}")
        res = gp_minimize(
            func=self.evaluate,
            dimensions=[(500, 4000), (500, 4000)], 
            acq_func="LCB",
            n_calls=calls,
            n_initial_points=init_points,
            random_state=777
        )
        best_a, best_b = int(res.x[0]), int(res.x[1])
        print(f"\n--- Optimization Done ---")
        print(f"Best Mix: Pump A = {best_a}ms, Pump B = {best_b}ms (Best MSE: {res.fun:.2f})")
        return res