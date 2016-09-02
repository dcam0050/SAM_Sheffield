#!/usr/bin/python

#
#The University of Sheffield
#WYSIWYD Project
#
#Example of implementation of SAMpy class
#
#Created on 29 May 2015
#
#@authors: Uriel Martinez, Luke Boorman, Andreas Damianou
#
#

import matplotlib.pyplot as plt
import readline
import warnings
import GPy
from SAM.SAM_Core import SAMCore
import threading
from SAM.SAM_Core import SAMDriver
import pylab as pb
import sys 
from sys import executable
import subprocess
from subprocess import Popen, PIPE
import pickle
import os
from os import listdir, walk, system
from os.path import isfile, join, isdir
import time
import operator
import numpy as np
import numpy.ma as ma
import datetime
import yarp
import copy
from itertools import combinations 
from ConfigParser import SafeConfigParser
from scipy.spatial import distance
from numpy.linalg import inv
import math
import itertools
numQ = 6
warnings.simplefilter("ignore")

#--------------------functions------------------------------
def distEuc(a,b):
    temp = a-b
    temp = np.square(temp)
    temp = np.sum(temp,1)
    return np.sqrt(temp)

def qtc_2D(k,l,q,thresh, contactThresh, contact = None):
    d1 = distEuc(k[:-2],l[1:-1])
    d2 = distEuc(k[1:-1],l[1:-1])
    d3 = distEuc(k[2:],l[1:-1])

    func2 = 0
    if(func2 == 0):
        for i in range(len(d1)):
            #threshold distance moved
            diff1 = d2[i]-d1[i]
            if(np.abs(diff1) < thresh):
                diff1 = 0

            diff2 = d3[i]-d2[i]
            if(np.abs(diff2) < thresh):
                diff2 = 0

            #convert to qtc
            if(diff1 > 0 and diff2 > 0):
                q[i] = -1
            elif(diff1 < 0 and diff2 < 0):
                q[i] = +1
            else:
                q[i] = 0
                
    elif(func2 == 1):
            #threshold distances
        inds = d1 < thresh
        d1[inds] = 0

        inds = d2 < thresh
        d2[inds] = 0

        inds = d3 < thresh
        d3[inds] = 0

        for i in range(len(d1)):
            if(d1[i] < d2[i] < d3[i]):
                q[i] = -1
            elif(d1[i] > d2[i] > d3[i]):
                q[i] = +1
            else:
                q[i] = 0
        
        #check contact
        
        #check qtc smoothness

def frenetFrame(arr):
    t_num = np.diff(arr,axis=0)
    t = (t_num/np.abs(t_num)).astype(int)

    b_num = np.cross(t[:-1],t[1:])
    b = b_num/np.abs(b_num)
    t = t[1:]

    n = np.cross(b,t)

    frameArr = np.concatenate((t,n,b),axis=1).T
    fArr = frameArr.reshape((3,3,-1),order = 'F')
    return fArr

def qtc_3D(k, l, thresh, q3, q4, q5):
    fFrameK = frenetFrame(k)
    fFrameL = frenetFrame(l)

    for g in range(fFrameK.shape[2]):
        fKinv = np.linalg.pinv(fFrameK[:,:,g])
        R = np.dot(fFrameL[:,:,g],fKinv)
        
        alpha = np.arctan(R[1,0]/R[0,0])
        den = np.sqrt(pow(R[2,1],2) + pow(R[2,2],2))
        
        beta = np.arctan(-R[2,0]/den)
        gamma = np.arctan(R[2,1]/R[2,2])

        #threshold angles
        if(np.abs(alpha) < thresh or math.isnan(alpha)):
            alpha = 0
        if(np.abs(beta) < thresh or math.isnan(beta)):
            beta = 0
        if(np.abs(gamma) < thresh or math.isnan(gamma)):
            gamma = 0

        q3[g] = np.sign(alpha)
        q4[g] = np.sign(beta)
        q5[g] = np.sign(gamma)

def most_common(L):
	# get an iterable of (item, iterable) pairs
	SL = sorted((x, i) for i, x in enumerate(L))
	# print 'SL:', SL
	groups = itertools.groupby(SL, key=operator.itemgetter(0))
	# auxiliary function to get "quality" for an item
	def _auxfun(g):
		item, iterable = g
		count = 0
		min_index = len(L)
		for _, where in iterable:
			count += 1
			min_index = min(min_index, where)
		# print 'item %r, count %r, minind %r' % (item, count, min_index)
		return count, -min_index
	# pick the highest-count/earliest item
	return max(groups, key=_auxfun)[0]

class AR_Driver(SAMDriver):
    def testing(self, testInstance):
		# Returns the predictive mean, the predictive variance and the axis (pp) of the latent space backwards mapping.            
        #mm,vv,pp=self.SAMObject.pattern_completion(testFace, visualiseInfo=visualiseInfo)
        ret=self.SAMObject.pattern_completion(testInstance, visualiseInfo=None)

        mm = ret[0]
        vv = ret[1]
        post = ret[3]        

        # find nearest neighbour of mm and SAMObject.model.X
        dists = np.zeros((self.SAMObject.model.X.shape[0],1))

        for j in range(dists.shape[0]):
            dists[j,:] = distance.euclidean(self.SAMObject.model.X.mean[j,:], mm[0].values)
        nn, min_value = min(enumerate(dists), key=operator.itemgetter(1))
        if self.SAMObject.type == 'mrd':
            #print "With " + str(vv.mean()) +" prob. error the new action is " + self.labelName[int(self.SAMObject.model.bgplvms[1].Y[nn,:])]
            textStringOut=self.labelName[int(self.SAMObject.model.bgplvms[1].Y[nn,:])]

        elif self.SAMObject.type == 'bgplvm':
            #print "With " + str(vv.mean()) +" prob. error the new action is " + self.labelName[int(self.L[nn,:])]
            textStringOut=self.labelName[int(self.L[nn,:])]
        # print textStringOut

        # if(vv.mean()<0.00012):            
        #     print "The action is " + textStringOut
        # elif(vv.mean()>0.00012):
        #     print "I think the action is " + textStringOut + " but I am not sure"      

        # # Plot the training NN of the test image (the NN is found in the INTERNAl, compressed (latent) memory space!!!)
        # if visualiseInfo is not None:
        #     fig_nn = visualiseInfo['fig_nn']
        #     fig_nn = pb.figure(11)
        #     pb.title('Training NN')
        #     fig_nn.clf()
        #     pl_nn = fig_nn.add_subplot(111)
        #     pl_nn.imshow(numpy.reshape(self.SAMObject.recall(nn),(self.imgHeightNew, self.imgWidthNew)), cmap=plt.cm.Greys_r)
        #     pb.title('Training NN')
        #     pb.show()
        #     pb.draw()
        #     pb.waitforbuttonpress(0.1)
        #return pp

        return [textStringOut, vv.mean()]
    
    def readData(self, root_data_dir, participant_index):
		onlyfiles = [f for f in listdir(dataPath) if isfile(join(dataPath, f))]
		dataLogList = [f for f in onlyfiles if 'data' in f]
		dataLogList.sort()
		labelsLogList = [f for f in onlyfiles if 'label' in f]
		labelsLogList.sort()

		numJoints = 9
		data = dict()
		firstPass = True
		jointsList = []
		objectsList = []
		labelsList = []
		numFiles = len(dataLogList)

		print 'loading data from files'
		for k in range(len(dataLogList)):
			print 'data file: ' + str(join(dataPath, dataLogList[k]))
			print 'model file: ' + str(join(dataPath, labelsLogList[k]))
			print
			dataFile = open(join(dataPath, dataLogList[k]),'r')
			labelFile = open(join(dataPath, labelsLogList[k]),'r')

			#number of lines in dataFile
			for i, l in enumerate(dataFile):
					pass
			lenDataFile = i+1

			#number of lines in labelFile
			for i, l in enumerate(labelFile):
					pass
			lenLabelFile = i+1
			dataFile.close()
			labelFile.close()

			if(lenLabelFile != lenDataFile):
				print str(dataLogList[k]) + ' will not be used because its lenght differs from ' + str(labelsLogList[k])
			else:
				dataFile = open(join(dataPath, dataLogList[k]),'r')
				labelFile = open(join(dataPath, labelsLogList[k]),'r')
				labelsList.append([])

				for curr in range(lenDataFile):
					line = dataFile.readline()
					labelLine = labelFile.readline()

					t = line.replace('(','').replace(')','').split(' ')
					del t[0:4]
					#parse skeleton data which has 9 sections by (x,y,z)
					for i in range(numJoints):
						a = i*4
						if(firstPass):
							data[t[a]] = [None]*numFiles
							data[t[a]][k] = (np.array([float(t[a+1]), float(t[a+2]), float(t[a+3])]))
							jointsList.append(t[a])
						else:
							arr =  np.array([float(t[a+1]), float(t[a+2]), float(t[a+3])])
							if(data[t[a]][k] != None):
								data[t[a]][k] = np.vstack((data[t[a]][k],arr))
							else:
								data[t[a]][k] = arr

					currIdx = (numJoints*4 -1)
					numObjs = (len(t) - currIdx)/5

					for i in range(numObjs):
						a = currIdx + 1 + (i*5)
						if(t[a] in data):
							arr = np.array([float(t[a+1]), float(t[a+2]), float(t[a+3])])
							if(data[t[a]][k] != None):
								data[t[a]][k] =  np.vstack((data[t[a]][k],arr))
							else:
								data[t[a]][k] = arr
						else:
							data[t[a]] = [None]*(numFiles+1)
							data[t[a]][k] = np.array([float(t[a+1]), float(t[a+2]), float(t[a+3])])
							data[t[a]][-1] = int(t[a+4])
							objectsList.append(t[a])

					firstPass = False
					try:
						v = labelLine.split(' ')[2].replace('\n','').replace('(','').replace(')','')
					except IndexError:
						print labelLine

					labelsList[k].append(v)

		#compile a list of all unique labels
		print
		print 'Unique labels in labels files:'
		print
		setList = []
		for x in labelsList:
		    setList.append(list(set(x)))
		flattenedList = [val for sublist in setList for val in sublist]
		labels = list(set(flattenedList))
		labels.sort()
		for k in range(0,len(labels)):
			print str(k) + '  ' + labels[k]
		print
		print 'Of these, config.ini specifies [' + ', '.join(ignoreLabels) + '] to be ignored'

		ignoreInds = []
		for k in ignoreLabels:
			ignoreInds.append(labels.index(k))

		#prepare list of indices for labels which will be used
		#important that no other labels are removed because that would interfere with temporal continuity of data
		#no temporal continuity would make QTC calculation with big jumps which is not desirable
		#future work needs to go through data and split it into subsections depend

		doLabels = [x for i,x in enumerate(labels) if i not in ignoreInds]
		indicesList = []
		currIdxList = []
		func = 0
		if(func == 0):
			for ll in labelsList:
				indicesList.append([i for i, x in enumerate(ll) if x in doLabels])
		elif(func == 1):
			for ll in labelsList:
				#iterate over items of ll
				#indicesList stores contiguous regions between ignoredLabels 
				for l in ll:
					if(l in doLabels):
						currIdxList.append(l)
					elif(l not in doLabels):
						if(len(currIdxList) > 0):
							indicesList.append(currIdxList)
							currIdxList = []

		#apply indices
		subsetData = None
		subsetLabels = None
		#CHECK
		subsetData = copy.deepcopy(data)
		subsetLabels = copy.deepcopy(labelsList)
		if(func == 0):
			for k in range(numFiles):
				for j in jointsList + objectsList:	
					subsetData[j][k] = np.squeeze(data[j][k][[indicesList[k]],:])
					subsetLabels[k] = [labelsList[k][i] for i in indicesList[k]]

		#apply indices
		# count = 0
		# off1 = 3
		# off2 = 2
		# off3 = 15
		# off4 = 25
		# for k in range(numFiles):
		# 	for j in jointsList + objectsList:
		# 		count += 1
		# 		print str(count).ljust(off1) + ' Folder ' + str(k).ljust(off2) + ' object: ' + j.ljust(off3) + \
		# 		' data shape: '.ljust(off4) + str(len(data)) + ' ' + str(len(data[j])) + ' ' + str(data[j][k].shape)
		# 		print str(count).ljust(off1) + ' Folder ' + str(k).ljust(off2) + ' object: ' + j.ljust(off3) + \
		# 		' subset data shape: '.ljust(off4) + str(len(subsetData)) + ' ' + str(len(subsetData[j])) + ' ' + str(subsetData[j][k].shape)
		# 		print str(count).ljust(off1) + ' Folder ' + str(k).ljust(off2) + ' object: ' + j.ljust(off3) + \
		# 		' labels shape: '.ljust(off4) + str(len(labelsList)) + '     ' + str(len(labelsList[k]))
		# 		print str(count).ljust(off1) + ' Folder ' + str(k).ljust(off2) + ' object: ' + j.ljust(off3) + \
		# 		' subset labels shape: '.ljust(off4) + str(len(subsetLabels)) + '     ' + str(len(subsetLabels[k]))
		# 		print str(count).ljust(off1) + ' Folder ' + str(k).ljust(off2) + ' object: ' + j.ljust(off3) + \
		# 		' good inds shape: '.ljust(off4) + str(len(indicesList)) + '     ' + str(len(indicesList[k]))
		# 		print

		allObjs = jointsList + objectsList
		print
		print 'Unique joints and objects in data files: '
		print
		print '\n'.join(allObjs)
		print 
		print 'Of these, config.ini specifies [' + ', '.join(ignoreParts) + '] to be ignored'
		print

		remObjs = ignoreParts
		impObjs = copy.deepcopy(allObjs)
		for x in remObjs:
			impObjs.remove(x)
		objCombs = list(combinations(impObjs, 2))
		print 'Creating ' + str(len(objCombs)) + ' combinations out of ' + str(len(impObjs)) + ' objects'  
		print 

		qtcDataList = dict()
		angleThreshold = 0.1
		distanceThreshold = 0.001
		contactThreshold = 0.1
		allJoints = []
		#for all combs
		for arr in range(len(subsetData[objCombs[0][0]])):
			print 'Preprocessing file ' + str(arr)
			jointArr = None
			for currComb in objCombs:
				Pk = subsetData[currComb[0]]
				Pl = subsetData[currComb[1]]
				#for all arrays in Pk and Pl
				currPk = Pk[arr]
				currPl = Pl[arr]

				q1 = np.zeros(currPk.shape[0]-2, dtype=np.int)
				q2 = np.zeros(currPk.shape[0]-2, dtype=np.int)
				q3 = np.zeros(currPk.shape[0]-2, dtype=np.int)
				q4 = np.zeros(currPk.shape[0]-2, dtype=np.int)
				q5 = np.zeros(currPk.shape[0]-2, dtype=np.int)
				q6 = np.zeros(currPk.shape[0]-2, dtype=np.int)
				#currPk contains xyz and currPl contains xyz
				#calculate QTC
				#step 1: q1 = {-1,0,+1} Pk relative to Pl
				qtc_2D(currPk,currPl,q1, distanceThreshold, contactThreshold, q6)
				#step 2: q2 = {-1,0,+1} Pl relative to Pk
				qtc_2D(currPl,currPk,q2, distanceThreshold, contactThreshold)
				#step 3: calculate q3, q4 and q5
				qtc_3D(currPk, currPl, angleThreshold, q3, q4, q5)
				if(numQ == 5):
					tempArr = np.vstack((q1,q2,q3,q4,q5))
				elif(numQ == 6):
					tempArr = np.vstack((q1,q2,q3,q4,q6))
				if(jointArr == None):
					jointArr = tempArr.T
				else:
					jointArr = np.hstack((jointArr,tempArr.T))
			allJoints.append(jointArr)

			#updating labelsList
			subsetLabels[arr] = subsetLabels[arr][1:-1]

		#create mask to temporaly segment actions temporally
		mask = np.zeros(allJoints[0].shape[1], dtype = int)
		for i in range(0,len(mask),numQ):
		    mask[i+0] = 1
		    mask[i+1] = 1

		actionsIdxList = []
		actionsLabelsList = []

		#for each item in list
		print
		print 'Temporal segmentation of data:'
		print
		for k in range(len(allJoints)):
			print 'Segmenting file ' + str(k)
			actionsIdxList.append([])
			actionsLabelsList.append([])
			#create array that masks q2,q3 and q4
			maJoints = allJoints[k]*mask
			#sum abs(rows) of array
			maAbs = np.abs(maJoints)
			maSum = np.sum(maAbs, axis = 1)
			#indices with maAbs =  0 are regions with no movement 
			#.ie action demarcation between actions
			#maSum = maSum[:50]
			actionCount = 0
			actionsIndices = None
			actionsLabels = []
			started = False

			for n in range(len(maSum)):
				if(maSum[n] == 0):
					#here we need to close action if previous is not zero
					#start action if next is not zero
					#ignore otherwise

					#if n-1 not 0 end action
					#check n-1 exists 
					if(n-1 >= 0):
						if(maSum[n-1] != 0):
							#end action including 0 at n
							actionsIndices = np.hstack((actionsIndices, allJoints[k][n]))
							actionsLabels.append(subsetLabels[k][n])
							started = False
							actionsIdxList[k].append(actionsIndices)
							actionsLabelsList[k].append(actionsLabels)
							actionsIndices = None
							actionsLabels = []

					#check n+1 exists
					if(n+1 < len(maSum)):
						#if n+1 exists but not 0 start an action
						if(maSum[n+1] != 0):
							#start action including 0 at n
							actionsIndices = allJoints[k][n]
							actionsLabels.append(subsetLabels[k][n])
							started = True
						#else ignore current index
					#else we are at the end so ignore

				else: #current index is not zero
					if(started):
						#here if started = True we are in middle of action so concatenate
						actionsIndices = np.hstack((actionsIndices, allJoints[k][n]))
						actionsLabels.append(subsetLabels[k][n])
						if(n+1 == len(maSum)):
							actionsIdxList[k].append(actionsIndices)
							actionsLabelsList[k].append(actionsLabels)
					else:
						#here action has not started meaning a zero was not found
						#this occurs if vector does not start with a zero
						actionsIndices = allJoints[k][n]
						actionsLabels.append(subsetLabels[k][n])
						started = True
		#find maximum length vector for SAM
		maxLen = 0
		for n in actionsIdxList:
			for k in n:
				if(k.shape[0] > maxLen):
					maxLen = k.shape[0]
		print
		#create Y and L
		Y = None
		L = []
		for n in range(len(actionsIdxList)):
			for k in range(len(actionsIdxList[n])):
				currLen = len(actionsIdxList[n][k])
				augMat = np.zeros(maxLen-currLen)
				if(Y == None): 
					Y = np.hstack((actionsIdxList[n][k],augMat))
				else:
					Y = np.vstack((Y, np.hstack((actionsIdxList[n][k],augMat))))
				L.append(actionsLabelsList[n][k])

		L2 = [most_common(sublist) for sublist in L]
		Larr = np.zeros(len(L2))
		for f in range(len(L2)):
			Larr[f] = labels.index(L2[f])

		print
		self.Y = Y
		self.L = Larr[:,None]
		self.labelName = textLabels

    def prepareData(self, model='mrd', Ntr = 50, randSeed=0):    

        Nts=self.Y.shape[0]-Ntr
        np.random.seed(randSeed)
        perm = np.random.permutation(self.Y.shape[0])
        indTs = perm[0:Nts]
        indTs.sort()
        indTr = perm[Nts:Nts+Ntr]
        indTr.sort()
        YtestAll = self.Y[indTs].copy() ##
        self.Ytest = self.Y[indTs]
        LtestAll = self.L[indTs].copy()##
        self.Ltest = self.L[indTs]
        Yall = self.Y[indTr].copy()##
        self.Y = self.Y[indTr]
        Lall = self.L[indTr].copy()##
        self.L = self.L[indTr]
    
        # Center data to zero mean and 1 std
        # self.Ymean = self.Y.mean()
        # self.Yn = self.Y - self.Ymean
        # self.Ystd = self.Yn.std()
        # self.Yn /= self.Ystd
        self.Yn = self.Y
        # Normalise test data similarly to training data
        #self.Ytestn = self.Ytest - self.Ymean
        self.Ytestn = self.Ytest
        #self.Ytestn /= self.Ystd

        if model == 'mrd':    
            self.X=None     
            self.Y = {'Y':self.Yn,'L':self.L}
            self.data_labels = self.L.copy()
        elif model == 'bgplvm':
            self.X=None     
            self.Y = {'Y':self.Yn}
            self.data_labels = self.L.copy()
        return Yall, Lall, YtestAll, LtestAll
#-----------------------------------------------------------

#yarpRunning = False
dataPath = sys.argv[1]
modelPath = sys.argv[2]
interactionConfPath = sys.argv[3]

splitPath = modelPath.split('__')
modelBase = '__'.join(splitPath[:-1])

msplit = modelPath.split('/')
modelFolder = '/'.join(msplit[:-1])
modelName = modelBase.split('/')[-1]

participantList = [f for f in listdir(dataPath) if isdir(join(dataPath, f))]
modelList = [join(modelFolder,f.replace('.pickle','')) for f in listdir(modelFolder) if isfile(join(modelFolder, f)) if modelName in f if '.pickle' in f if '~' not in f]

#parameters are common across all items of modelList
modelPickle = pickle.load(open(modelList[0]+'.pickle' ,'rb'))
ignoreLabels = modelPickle['ignoreLabels']
ignoreParts = modelPickle['ignoreParts']
ratioData = modelPickle['percentTestData']
angThresh = modelPickle['angleThreshold']
distThresh = modelPickle['distanceThreshold']
contThresh = modelPickle['contactThreshold']
model_type = modelPickle['model_type']
model_num_inducing = modelPickle['num_inducing']
model_init_iterations = modelPickle['model_init_iterations']
model_num_iterations = modelPickle['model_num_iterations']
kernelString = modelPickle['kernelString']
Q = modelPickle['Q']
Ytrain = modelPickle['YALL']
Ltrain = modelPickle['LALL']
objCombs = modelPickle['objCombs']
textLabels = modelPickle['textLabels']
#Ytest = modelPickle['YTEST']
#Ltest = modelPickle['LTEST']

economy_save = True
yarpRunning = False

# # Creates a SAMpy object
print 'Loading model ...'
mySAMpy = AR_Driver(yarpRunning)
mySAMpy.contactThreshold = contThresh
mySAMpy.distanceThreshold = distThresh
mySAMpy.angleThreshold = angThresh

if model_type == 'mrd':    
	mySAMpy.X=None     
	mySAMpy.Y = {'Y':Ytrain,'L':Ltrain}
	mySAMpy.data_labels = Ltrain.copy()
	mySAMpy.labelName = textLabels
elif model_type == 'bgplvm':
	mySAMpy.X=None     
	mySAMpy.Y = {'Y':Ytain}
	mySAMpy.data_labels = Ltrain.copy()
	mySAMpy.labelName = textLabels
 
fname = modelList[0]

if Q > 100:
	#one could parse and execute the string kernelStr for kernel instead of line below
	kernel = GPy.kern.RBF(Q, ARD=False) + GPy.kern.Bias(Q) + GPy.kern.White(Q)
else:
	kernel = None

# Simulate the function of storing a collection of events
mySAMpy.SAMObject.store(observed=mySAMpy.Y, inputs=mySAMpy.X, Q=Q, kernel=kernel, num_inducing=model_num_inducing)
SAMCore.load_pruned_model(fname, economy_save, mySAMpy.SAMObject.model)
	
#open ports
yarp.Network.init()

sect = splitPath[0].split('/')[-1].lower()

parser2 = SafeConfigParser()
parser2.read(interactionConfPath)
portNameList = parser2.items(sect)
print
portsList = []
for j in range(len(portNameList)):
	if(portNameList[j][0] == 'rpcbase'):
		portsList.append(yarp.Port())
		portsList[j].open(portNameList[j][1]+':i')
		svPort = j
	elif(portNameList[j][0] == 'callsign'):
		callSignList = portNameList[j][1].split(',')
	else:
		parts = portNameList[j][1].split(' ')

		if(parts[1].lower() == 'imagergb'):
			portsList.append(yarp.BufferedPortImageRgb())
			portsList[j].open(parts[0])

		elif(parts[1].lower() == 'imagemono'):
			portsList.append(yarp.BufferedPortImageMono())
			portsList[j].open(parts[0])

		elif(parts[1].lower() == 'bottle'):
			portsList.append(yarp.BufferedPortBottle())
			portsList[j].open(parts[0])
		#mrd models with label/instance training will always have:
		#1 an input data line which is used when a label is requested
		#2 an output data line which is used when a generated instance is required
		if(parts[0][-1] == 'i'):
			labelPort = j
		elif(parts[0][-1] == 'o'):
			instancePort = j

#making sure all ports are connected
out = 0
while(out == 0):
	out = portsList[svPort].getOutputCount() + portsList[svPort].getInputCount()
	print 'Waiting for ' + portNameList[svPort][1] + ' to receive a connection'
	time.sleep(1)
print 'Connection received'
print
print '--------------------'
inputBottle = yarp.Bottle();
outputBottle = yarp.Bottle();
dataReceived = yarp.Bottle();

#wrap = yarp.BufferedPortBottle(portsList[svPort].asPort())
#prepare yarp variables
# imageArray = numpy.zeros((imgH, imgW, 3), dtype=numpy.uint8)
# yarpImage = yarp.ImageRgb()
# yarpImage.resize(imgH,imgW)
# yarpImage.setExternal(imageArray, imageArray.shape[1], imageArray.shape[0])

# numFaces = 10
# testFace = numpy.zeros([numFaces,imgHNew*imgWNew])
# images = numpy.zeros((numFaces, imgHNew*imgWNew), dtype=numpy.uint8)
replyString = ''
print 'Responding to callsigns: ' + ', '.join(callSignList)

def readCommands(supPort, inBottle, replyBool, replyStr, exception, recActions ):
	while(1):
		supPort.read(inBottle,replyBool)
		message = inBottle.get(0).asString()
		print(message + ' received')
		print 'responding to ' + message + ' request'

		if(message == 'EXIT'):
			exception[0] =  'keyInterupt'
			replyStr = 'ack'
		elif('label' in message):
			if(len(recActions) > 0):
				print 'label'
				print recActions
				replyStr = '__'.join(recActions)
				replyStr = 'ack ' + replyStr 
			else:
				replyStr = 'ack no_actions_recognised'
		elif('instance' in message):
			# parse all remaining Bottle contents
			if(portsList[instancePort].getInputCount() != 0):
				replyStr = 'ack'
			else:
				replyStr = 'nack'
				print 'No connections to ' + portsList[instancePort].getName()
		else:
			replyStr = 'nack'
			print message + ' is not a valid request'
		print
		supPort.reply(yarp.Bottle(replyStr))

exception = []
actionsRec = []
exception.append('')
read_thread = threading.Thread(target=readCommands, args=(portsList[svPort], inputBottle, True, replyString, exception, actionsRec,  ))
read_thread.start()
#portsList[svPort].setTimeout(1)

numJoints = 9
data = dict()
objectsList = []
angleThreshold = mySAMpy.angleThreshold
distanceThreshold = mySAMpy.distanceThreshold
contactThreshold = mySAMpy.contactThreshold
qtcData = None
vecLen = mySAMpy.Y['Y'].shape[1]
actionSegments = []
mask = np.zeros(len(objCombs)*numQ, dtype = int)
for i in range(0,len(mask),numQ):
	mask[i+0] = 1
	mask[i+1] = 1
firstPass = True
dataStartPoint = 0

while( True ):
		try:
			if(portsList[labelPort].getInputCount() == 0):
				print "Waiting for data connection"
				time.sleep(1)
			elif(portsList[labelPort].getPendingReads() > 0):
				#process incoming stream of data and keep last zero to zero
				#step 1: parse bottle
				dataReceived = portsList[labelPort].read(True)
				dataMessage = dataReceived.toString()
				t = dataMessage.replace('(','').replace(')','').split(' ')
				if(t > 40):
					del t[0:2]

					for i in range(numJoints):
						a = i*4
						arr =  np.array([float(t[a+1]), float(t[a+2]), float(t[a+3])])
						if(t[a] in data):
							if(data[t[a]] != None):
								data[t[a]] = np.vstack((data[t[a]],arr))
							else:
								data[t[a]] = arr
						else:
							data[t[a]] = arr

					currIdx = (numJoints*4 -1)
					numObjs = (len(t) - currIdx)/5

					for i in range(numObjs):
						a = currIdx + 1 + (i*5)
						if(t[a] in data):
							arr = np.array([float(t[a+1]), float(t[a+2]), float(t[a+3])])
							if(data[t[a]] != None):
								data[t[a]] =  np.vstack((data[t[a]],arr))
							else:
								data[t[a]] = arr
						else:
							data[t[a]] = arr
							objectsList.append(t[a])
					# print data['head']
					# print
					#step 2: extract qtc vector
					qtcData = None
					if(data['head'].shape[0] >= 4):
						for currComb in objCombs:
							Pk = data[currComb[0]][dataStartPoint:]
							Pl = data[currComb[1]][dataStartPoint:]
							#print str(currComb) + ' ' + str(Pk.shape) + 'info'

							q1 = np.zeros(Pk.shape[0]-2, dtype=np.int)
							q2 = np.zeros(Pk.shape[0]-2, dtype=np.int)
							q3 = np.zeros(Pk.shape[0]-2, dtype=np.int)
							q4 = np.zeros(Pk.shape[0]-2, dtype=np.int)
							q5 = np.zeros(Pk.shape[0]-2, dtype=np.int)
							q6 = np.zeros(Pk.shape[0]-2, dtype=np.int)
							#currPk contains xyz and currPl contains xyz
							#calculate QTC
							#step 1: q1 = {-1,0,+1} Pk relative to Pl
							qtc_2D(Pk,Pl,q1, distanceThreshold, contactThreshold, q6)
							#step 2: q2 = {-1,0,+1} Pl relative to Pk
							qtc_2D(Pl,Pk,q2, distanceThreshold, contactThreshold)
							#step 3: calculate q3, q4 and q5
							qtc_3D(Pk, Pl, angleThreshold, q3, q4, q5)
							if(numQ == 5):
								tempArr = np.vstack((q1,q2,q3,q4,q5))
							elif(numQ == 6):
								tempArr = np.vstack((q1,q2,q3,q4,q5,q6))
							if(qtcData == None):
								qtcData = tempArr.T
							else:
								qtcData = np.hstack((qtcData,tempArr.T))
						
						# print qtcData.shape

						zeroCheck = np.abs(qtcData*mask)
						zeroCheck = np.sum(zeroCheck, axis = 1)
						# print zeroCheck.shape
						# print zeroCheck
						Idx = []
						label = []
						for dataIdx in range(zeroCheck.shape[0]):
							if(zeroCheck[dataIdx] == 0):
								if(dataIdx-1 >= 0 and zeroCheck[dataIdx-1] != 0):
									#end of an action
									# print 'action end'
									Idx.append(dataIdx)
									label.append('end')
								if(dataIdx+1 < len(zeroCheck) and zeroCheck[dataIdx+1] != 0):
									#start action
									# print 'action start'
									Idx.append(dataIdx)
									label.append('start')

						if(len(label) > 0):
							if(label[0] == 'end'):
									dataStartPoint = Idx[0] + dataStartPoint
									del Idx[0]
									del label[0]
						# print 'zero check'
						# print zeroCheck
						if(len(Idx) % 2 == 0 and len(Idx) != 0 ):
							if((Idx[1]-Idx[0]) > 3):
								# print 'action of lenght ' + str((Idx[1]-Idx[0]+1)) + ' found'
								#do recognition and store in actionsRec
								actionVec = qtcData[Idx[0]:Idx[1]+1,:]
								actionVec = np.reshape(actionVec, (1,-1))
								#check it is lenght used to train
								currLen = actionVec.shape[1]
				
								if(currLen < vecLen):
 									augMat = np.zeros((vecLen-currLen))
 									augMat = augMat[None,:]
									actionVec = np.hstack((actionVec, augMat))
									[textStringOut, conf] = mySAMpy.testing(actionVec)
									if(conf < 0.00012):
										print 'action is ' + textStringOut + ' with high confidence of ' + str(conf)[:8] + ' < ' + str(0.00012)
									else:
										print 'action is ' + textStringOut + ' with low confidence of ' + str(conf)[:8] + ' > ' + str(0.00012)
									actionsRec.append(textStringOut)
								else:
									#ignore
									print 'collected vector too long'

							else:
								print 'action too short'

							dataStartPoint = Idx[1] + dataStartPoint
							Idx = []
							label = []

				else:
					print 'Incorrect message received'

			if(exception[0] == 'keyInterupt'):
				raise KeyboardInterrupt

		except KeyboardInterrupt:
			print 'Exiting ...'
			for j in portsList:
				j.close()
			try:
				sys.exit(0)
			except SystemExit:
				os._exit(0)
for j in portsList:
	j.close()