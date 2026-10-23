# BayesianOpt

A small Bayesian optimization example for matching a target three-component value, currently modeled as a color. The optimization starts in `bayesianOpt.py` and uses `scikit-optimize` to search for the parameter combination with the lowest mean squared error.

## How It Works

1. Running `bayesianOpt.py` calls `main()`.
2. `main()` asks `skopt.gp_minimize` to search three parameters. Each parameter is bounded from `0.0` to `5.0`.
3. The optimizer makes up to a number of evaluations, using the Lower Confidence Bound (`LCB`) acquisition function.
4. Each candidate is passed to `evaluate()` in `bayesianOpt.py`.
5. `evaluate()` calls `evaluateFitness.evaluate(...)`.
6. `evaluateFitness.py` obtains a measurement through `growAndMeasure()` and calculates the mean squared error against the target `[0.5, 0.5, 0.5]`.
7. `PlotterCallback` displays progress in a Matplotlib window and prints the current function value and minimum. A checkpoint is written to `checkpoint.pkl` after each iteration.
8. The final `scikit-optimize` result is printed to the console.

The current `growAndMeasure()` implementation is a simulation: it returns the candidate values unchanged. To connect real equipment, replace the placeholder measurement logic in that function with the hardware setup and sensor-reading code.

## Requirements

- Python 3
- Dependencies listed in `requirements.txt`
- A graphical environment for the live Matplotlib plot
- Permission for the `keyboard` package to register the F12 key on some systems

Install the dependencies with:

```text
python -m pip install -r requirements.txt
```

## Run From Scratch

From this directory, run:

```text
python bayesianOpt.py
```

The script opens a progress plot, prints each candidate and fitness value, and saves the latest optimizer state as `checkpoint.pkl`.

Press **F12** to pause or resume evaluations. Pausing takes effect before the next candidate is evaluated; the program waits until it is resumed.

## Resume From A Checkpoint

The `main(checkPoint=None)` function supports resuming from a checkpoint. 

Resume mode loads `./checkpoint.pkl`, reuses the stored candidates and fitness values, and performs the remaining evaluations up to the configured total.

## Configuration

The main settings are in `bayesianOpt.py`:

- `NSamples`: maximum number of optimizer evaluations, currently `20`.
- Search bounds in `gp_minimize`: three dimensions, each from `0.0` to `5.0`.
- `n_initial_points`: number of initial points, currently `5`.
- `acq_func`: acquisition function, currently `LCB` Lower confidence bound.
- `random_state` and NumPy seed: both set to `777` for repeatable optimizer behavior.

The target value is defined in `evaluateFitness.py`:

```python
target = [0.5, 0.5, 0.5]
```

The optimizer minimizes the average of the three squared component errors using the Mean Squared Error:

```text
((target[0] - measure[0]) ** 2
 + (target[1] - measure[1]) ** 2
 + (target[2] - measure[2]) ** 2) / 3
```

Lower fitness is better, and an exact match has a fitness of `0.0`.

## Project Files

- `bayesianOpt.py`: optimization entry point, pause handling, checkpoint setup, and final result reporting.
- `evaluateFitness.py`: target definition, measurement hook, and fitness calculation.
- `customCallbacks.py`: live plotting and per-iteration progress reporting.
- `requirements.txt`: Python dependencies.
- `checkpoint.pkl`: generated optimizer checkpoint; it is not included in the source tree.