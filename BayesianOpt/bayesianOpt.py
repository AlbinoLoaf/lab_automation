import random
import evaluateFitness
from customCallbacks import PlotterCallback
import matplotlib.pyplot as plt
import numpy as np
import pickle
import time
import keyboard

from skopt import gp_minimize
from skopt import callbacks
from skopt.callbacks import CheckpointSaver
from skopt import load
from skopt.plots import plot_convergence
from skopt.plots import plot_gaussian_process

# Tracker class to keep track of the current step in the optimization process
class Tracker(object):
    step = 0

tracker = Tracker()


pause = False
np.random.seed(777)
noise_level = 0.1
step = 0

# Start with a high best fitness value to ensure that any evaluated fitness will be lower
bestFitness = 100000000000

# Function to toggle the pause state when the F12 key is pressed, this will allow the user to pause and unpause the optimization process to make changes to the hardware setup or resume at a different time.
def toggle_pause(exception):
    global pause
    pause = not pause
    if pause:
        print("Paused!")
    else:
        print("Unpaused!")

# Register the F12 key to toggle the pause state
keyboard.on_press_key("f12", toggle_pause)

# Function to evaluate the fitness of an individual, this function will be called by the Bayesian optimization algorithm to evaluate the performance of different parameter combinations.
def evaluate(individual):
    """
    Evaluate the fitness of an individual by calling the evaluateFitness module and returning the fitness value.
    @param individual: A list of parameters representing the individual to be evaluated. Can be a collection of values in the form of an array or list.
    @return: The fitness value of the individual, representing how well it performs in matching the color. It is a single value.
    """
    global pause
    global bestFitness
    #print(tracker.step,tracker.step)
    # Wait for the pause state to be False before proceeding with the evaluation, this will allow the user to pause the optimization process and make changes to the hardware setup or resume at a different time.
    while pause:
        pass
    # Evaluate the fitness of the individual using the evaluateFitness module, this will return a fitness value that represents how well the individual performs in matching the target color.
    fitness = evaluateFitness.evaluate(individual,tracker.step,tracker.step)
    print(individual,fitness)
    # Keep track of the best fitness value seen so far, if the current fitness is better than the best fitness, update the best fitness value.
    if fitness < bestFitness:
        bestFitness = fitness
    return fitness





def main(checkPoint=None):
    """
    Main function to run the Bayesian optimization process for color matching.
    @param checkPoint: Optional parameter to specify a checkpoint file to resume the optimization process from. If provided, the optimization will continue from the saved state in the checkpoint file.
    """

    # Problem size
    N = 3 #Sample (Individual) dimension, individuals are represented by 3 values (e.g., RGB values for color matching)
    NSamples = 20 # Max number of samples to be taken
    checkpoint_saver = CheckpointSaver("./checkpoint.pkl", compress=9) # Creates a checkpoint saver object that will save the progress in a .pkl file at every iteration, keyword arguments will be passed to `skopt.dump`

    
    # Check if a checkpoint file is provided, if so, load the previous optimization state from the checkpoint file and continue the optimization process from where it left off.
    if checkPoint:
        result = load('./checkpoint.pkl')
        evaluationsDone = len(result.x_iters)
        # Populate the x0 and y0 lists with the previously evaluated individuals and their corresponding fitness values to continue the optimization process from the saved state.
        x0 = result.x_iters
        y0 = result.func_vals

        # Helper function to plot the convergence of the optimization process, this will allow the user to visualize how the optimization is progressing over time.
        plotter = PlotterCallback(NSamples-evaluationsDone,tracker)

        
        result = gp_minimize(evaluate,            # the function to minimize
            [(0.0, 5.0),(0.0,5.0),(0.0,5.0)],    # the bounds on each dimension of x (the individuals to be evaluated)
            x0=x0,              # already examined values for x
            y0=y0,              # observed values for x0
            acq_func="LCB",     # the acquisition function (optional), in this case Lower Confidence Bound (LCB) is used to balance exploration and exploitation during the optimization process
            n_calls=NSamples-evaluationsDone,         # number of evaluations of f minus the ones already done
            n_initial_points=5,  # the number of random initialization points
            callback=[checkpoint_saver,plotter], # Callbacks to helper functions, including the checkpoint saver and plotter to visualize the optimization progress
            random_state=777) # Random seed for reproducibility of results

    else:    
        # Helper function to plot the convergence of the optimization process, this will allow the user to visualize how the optimization is progressing over time.
        plotter = PlotterCallback(NSamples,tracker)

        result = gp_minimize(evaluate,            # the function to minimize
            [(0.0, 5.0),(0.0,5.0),(0.0,5.0)],    # the bounds on each dimension of x (the individuals to be evaluated)
            acq_func="LCB",     # the acquisition function (optional), in this case Lower Confidence Bound (LCB) is used to balance exploration and exploitation during the optimization process
            n_calls=NSamples,         # number of evaluations of f
            #n_random_starts=3,
            n_initial_points=5,  # the number of random initial points
            callback=[checkpoint_saver,plotter], # Callbacks to helper functions, including the checkpoint saver and plotter to visualize the optimization progress
            random_state=777) # Random seed for reproducibility of results

    # Print the final optimization result, which includes the best individual found and its corresponding fitness value.
    print(result)



if __name__ == "__main__":
    #main("checkpoint_gen_9.pkl",True) # Uncomment this line to resume from a checkpoint file, specify the checkpoint file name as an argument
    main() # Start the optimization process from scratch without resuming from a checkpoint file








