import math
import typing

# Set the target color to be matched, use the same format as the output of the measure function
target = [0.5,0.5,0.5]


def growAndMeasure(individual,generation,indvNumber): # Setup individual to create the color and return the sensor value
    
    print(generation,indvNumber)
    grownIndividual = []
    for i in range(len(individual)):       
      grownIndividual.append(individual[i])

    print("Evaluating: ",grownIndividual)
    #overallSum = sum(grownIndividual)
    
    measure = [grownIndividual[0],grownIndividual[1],grownIndividual[2]]# Return a measurement of the color, place the function calling the hardware here

    return measure

def evaluate(individual,generation,indvNumber):
      
      
      
      measure = growAndMeasure(individual,generation,indvNumber) # Call the function to grow the individual and measure the color

      distances  = [10000] * len(target) # Initialize the distances list with a large number to ensure it is overwritten

      for i in range(len(distances)): # Calculate the squared distance between the target and measured color values
        distances[i] = target[i]-measure[i]
        distances[i] = distances[i]*distances[i]

      errorSum = sum(distances) # Sum the squared distances to get the total error
      meanSquaredError = errorSum/(len(target)) # Calculate the mean squared error by dividing the total error by the number of target values

      return meanSquaredError

