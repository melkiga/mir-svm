# -*- coding: utf-8 -*-

"""
LightTwinSVM Program - Simple and Fast
Version: 0.2.0-alpha - 2018-05-30
Developer: Mir, A. (mir-am@hotmail.com)
License: GNU General Public License v3.0

Module: twinsvm.py
In this module, functios is defined for training and testing TwinSVM classifier.

TwinSVM classifier generates two non-parallel hyperplanes.
For more info, refer to the original papar.
Khemchandani, R., & Chandra, S. (2007). Twin support vector machines for pattern classification. IEEE Transactions on pattern analysis and machine intelligence, 29(5), 905-910.

Motivated by the following paper, the multi-class TSVM is developed.
Tomar, D., & Agarwal, S. (2015). A comparison on multi-class classification methods based on least squares twin support vector machine. Knowledge-Based Systems, 81, 131-147.
"""

# ClippDCD optimizer is an extension module which is implemented in C++
from ..utils.dataproc import read_data
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.utils.estimator_checks import check_estimator
#import clippdcd
import numpy as np
import time


class TSVM(BaseEstimator, ClassifierMixin):

    def __init__(self, kernel_type='linear', rect_kernel=1, c1=2**0, c2=2**0, \
                 gamma=2**0):

        """
            Input:
            Kernel_type: 1->Linear, 2->RBF(Gaussion)
            c1, c2: Penalty parameters
            gamma: RBF function parameter
        """

        self.C1 = c1
        self.C2 = c2
        self.u = gamma
        self.kernel_t = kernel_type
        self.rectangular_size = rect_kernel
        #self.mat_C_t = None

        # Two hyperplanes attributes
        #self.w1, self.b1, self.w2, self.b2 = None, None, None, None

#    def set_parameter(self, c1=2**0, c2=2**0, gamma=2**0):
#
#        """
#        It changes the parametes for TSVM classifier.
#        DO NOT USE THIS METHOD AFTER INSTANTIATION OF TSVM CLASS!
#        THIS METHOD CREATED ONLY FOR Validator CLASS.
#        Input:
#            c1, c2: Penalty parameters
#            gamma: RBF function parameter
#        """
#
#        self.C1 = c1
#        self.C2 = c2
#        self.u = gamma

    def fit(self, X, y):

        """
        It trains TwinSVM classfier on given data
        Input:    
            X_train: Training samples
            y_train: Samples' category
        output:

            w1, w2: Coordinates of two non-parallel hyperplanes
            b1, b2: Biases
            """

        # Matrix A or class 1 samples
        mat_A = X[y == 1]

        # Matrix B  or class -1 data 
        mat_B = X[y == -1]

        # Vectors of ones
        mat_e1 = np.ones((mat_A.shape[0], 1))
        mat_e2 = np.ones((mat_B.shape[0], 1))

        if self.kernel_t == 'linear':  # Linear kernel
            
            mat_H = np.column_stack((mat_A, mat_e1))
            mat_G = np.column_stack((mat_B, mat_e2))

        elif self.kernel_t == 'RBF': # Non-linear 

            # class 1 & class -1
            mat_C = np.row_stack((mat_A, mat_B))

            self.mat_C_t = np.transpose(mat_C)[:, :int(mat_C.shape[0] * self.rectangular_size)]

            mat_H = np.column_stack((rbf_kernel(mat_A, self.mat_C_t, self.u), mat_e1))

            mat_G = np.column_stack((rbf_kernel(mat_B, self.mat_C_t, self.u), mat_e2))


        mat_H_t = np.transpose(mat_H)
        mat_G_t = np.transpose(mat_G)

        # Compute inverses:
        # Regulariztion term used for ill-possible condition
        reg_term = 2 ** float(-7)

        mat_H_H = np.linalg.inv(np.dot(mat_H_t, mat_H) + (reg_term * np.identity(mat_H.shape[1])))
        mat_G_G = np.linalg.inv(np.dot(mat_G_t, mat_G) + (reg_term * np.identity(mat_G.shape[1])))

        # Wolfe dual problem of class 1
        mat_dual1 = np.dot(np.dot(mat_G, mat_H_H), mat_G_t)
        # Wolfe dual problem of class -1
        mat_dual2 = np.dot(np.dot(mat_H, mat_G_G), mat_H_t)

        # Obtaining Lagrane multipliers using ClippDCD optimizer
        alpha_d1 = np.array(clippdcd.clippDCD_optimizer(mat_dual1, self.C1)).reshape(mat_dual1.shape[0], 1)
        alpha_d2 = np.array(clippdcd.clippDCD_optimizer(mat_dual2, self.C2)).reshape(mat_dual2.shape[0], 1)

        # Obtain hyperplanes
        hyper_p_1 = -1 * np.dot(np.dot(mat_H_H, mat_G_t), alpha_d1)

        # Class 1
        self.w1 = hyper_p_1[:hyper_p_1.shape[0] - 1, :]
        self.b1 = hyper_p_1[-1, :]

        hyper_p_2 = np.dot(np.dot(mat_G_G, mat_H_t), alpha_d2)

        # Class -1
        self.w2 = hyper_p_2[:hyper_p_2.shape[0] - 1, :]
        self.b2 = hyper_p_2[-1, :]


    def predict(self, X):

        """
            Predictes class of test samples
            Input:
                X_test: Test samples    
        """

        # Calculate prependicular distances for new data points 
        prepen_distance = np.zeros((X.shape[0], 2))

        kernel_f = {'linear': lambda i: X[i, :] , 'RBF': lambda i: rbf_kernel(X[i, :], \
                    self.mat_C_t, self.u)}

        for i in range(X.shape[0]):

            # Prependicular distance of data pint i from hyperplanes
            prepen_distance[i, 1] = np.abs(np.dot(kernel_f[self.kernel_t](i), self.w1) + self.b1)

            prepen_distance[i, 0] = np.abs(np.dot(kernel_f[self.kernel_t](i), self.w2) + self.b2)

        # Assign data points to class +1 or -1 based on distance from hyperplanes
        output = 2 * np.argmin(prepen_distance, axis=1) - 1

        return output


def rbf_kernel(x, y, u):

    """
        It transforms samples into higher dimension  
        Input:
            x,y: Samples
            u: Gamma parameter      
        Output:
            Samples with higher dimension
    """

    return np.exp(-2 * u) * np.exp(2 * u * np.dot(x, y))


if __name__ == '__main__':
    
    train_data, lables, file_name = read_data('../dataset/pima-indian.csv')
    
    #model = TSVM()
    #check_estimator(TSVM)
    
    
