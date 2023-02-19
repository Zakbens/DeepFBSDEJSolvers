import numpy as np
import tensorflow as tf
import os
from Networks import Net
from Models import MertonJumpModel
from MertonSolvers import SolverGlobalFBSDE, SolverMultiStepFBSDE,SolverSumLocalFBSDE, SolverGlobalMultiStepReg, SolverGlobalSumLocalReg, SolverOsterleeFBSDE
from ClosedFormulaMerton import Option_param, Merton_process, Merton_pricer
import argparse
import matplotlib.pyplot as plt
import sys 

os.environ['KMP_DUPLICATE_LIB_OK']='True'
parser = argparse.ArgumentParser()
parser.add_argument('--nbNeuron_hat', type=int, default=15)
parser.add_argument('--nbNeuron', type=int, default=20)
parser.add_argument('--nbLayer', type=int, default=2)
parser.add_argument('--nEpochExt', type=int, default=100)
parser.add_argument('--nEpoch', type=int, default=200)
parser.add_argument('--batchSize',  type=int, default=128)
parser.add_argument('--rafCoef',  type=int, default=1000)
parser.add_argument('--lRateY0',type=float, default =0.001)
parser.add_argument('--lRateLoc',type=float, default =0.00015)
parser.add_argument('--lRateReg',type=float, default =0.0001)
parser.add_argument('--activation',  type= str, default="tanh")
parser.add_argument('--coefOsterlee', type= float, default = 1)
    
args = parser.parse_args()
print("Args ", args)
nbNeuron = args.nbNeuron
print("Nb neurons ", nbNeuron)
nbLayer= args.nbLayer
print("Nb hidden layers ", nbLayer)
batchSize = args.batchSize
print("batchSize " , batchSize)
num_epochExt = args.nEpochExt
print("num_epochExt " , num_epochExt)
num_epoch =args.nEpoch
print("Number epoch ", num_epoch)
rafCoef = args.rafCoef
print("refining coeff ",rafCoef)
jumpFactor=args.jumpFac
print("Jump factor ", jumpFactor)
lRateY0 =args.lRateY0
print("Learning rate Global", lRateY0)
lRateLoc =args.lRateLoc
print("Learning rate Local", lRateLoc)
lRateReg =args.lRateReg
print("Learning rate Regression", lRateReg)
activation = args.activation
if activation not in ['tanh', 'relu']:
    print(activation, 'is invalid. Please choose tanh or relu.')
    sys.exit(0)
print('activation', activation)
coefOsterlee = args.coefOsterlee
print('Osterlee coefficient', coefOsterlee)
nbSimul = args.nbSimulation
print('number of trajectories', nbSimul)
# Layers
######################################
layerSize = nbNeuron*np.ones((nbLayer,), dtype=np.int32) 
# parameter models
######################################
dict_parameters = {'T':1 , 'N':40, 'r':0.04, 'sig': 0.25, 'lam':0.3, 'muJ': 0.5, 'sigJ': 0.5, 'K': 0.9, 'x0': 1}
T, N, r, sig, lam, muJ, sigJ, K, x0 = dict_parameters.values()
# DL model
######################################
if activation == 'tanh':
    activ = tf.nn.tanh
elif activation == 'relu':
    activ = tf.nn.relu
# Closed formula Merton
######################################
opt_param = Option_param(x0, K, T, exercise="European", payoff="call" )
Merton_param = Merton_process(r, sig, lam, muJ, sigJ)
Merton = Merton_pricer(opt_param, Merton_param)
closedformula = Merton.closed_formula()
print('Merton real price:', closedformula)

# Train
#######################################
listLoss = []
fig, ax = plt.subplots(figsize=(10, 6))
for method in ['Global', 'SumMultiStep', 'SumLocal', 'SumLocalReg', 'SumMultiStepReg', 'Osterlee']:
  # math model
  ##########################
  mathModel = MertonJumpModel(T, N, r, muJ, sigJ, sig, lam, K, x0)

  # DL model
  ##########################
  if activation == 'tanh':
      activ = tf.nn.tanh
  elif activation == 'relu':
      activ = tf.nn.relu
  elif activation == 'sigmoid':
      activ = tf.math.sigmoid
      
  if method in ['SumMultiStepReg', 'SumLocalReg']:
      kerasModel = Net(method, 1, layerSize, activation)
  elif method in ['SumMultiStep', 'SumLocal', 'Osterlee']:
      kerasModel = Net(method, 3, layerSize, activation)
  else:
      kerasModel = Net(method, 2, layerSize, activation)

  # solver
  #########################
  if method == "Global":
      solver = SolverGlobalFBSDE(mathModel,kerasModel, lRateY0)
  elif method == "SumMultiStep":
      solver= SolverMultiStepFBSDE(mathModel,kerasModel, lRateLoc)
  elif method == "SumLocal":
      solver=  SolverSumLocalFBSDE(mathModel,kerasModel, lRateLoc)
  elif method == 'SumMultiStepReg':
      solver = SolverGlobalMultiStepReg(mathModel,kerasModel, lRateReg)
  elif method == 'SumLocalReg':
      solver =  SolverGlobalSumLocalReg(mathModel,kerasModel, lRateReg)
  elif method == 'Osterlee':
      solver = SolverOsterleeFBSDE(mathModel,kerasModel, lRateReg, coefOsterlee)

  # train and  get solution
  Y0List=  solver.train(batchSize,batchSize*10, num_epoch,num_epochExt )
  print('Y0',Y0List[-1])
  # Store loss
  listLoss.append(solver.lossList)
  # simulate if BSDE
  nbSimTest = 100000      
  ax.plot(Y0List, label = f"Y0 DL {method}")
ax.plot(closedformula*np.ones(num_epochExt), label = 'Y0 closed formula', linestyle = 'dashed')
ax.grid()
plt.legend()
plt.show()
