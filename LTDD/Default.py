import pandas as pd
import random, time, csv
import numpy as np
import math, copy, os
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn import tree
from sklearn.naive_bayes import GaussianNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
import sklearn.metrics as metrics

import sys
sys.path.append(os.path.abspath('..'))

from scipy import stats

## Load dataset
dataset_orig = pd.read_csv('datasets\\default_of_credit_card_clients_first_row_removed.csv')

## Change column values
dataset_orig['sex'] = np.where(dataset_orig['sex'] == 2, 0, 1)

## Drop NULL values
dataset_orig = dataset_orig.dropna()

from sklearn.preprocessing import MinMaxScaler

scaler = MinMaxScaler()
dataset_orig = pd.DataFrame(scaler.fit_transform(dataset_orig), columns=dataset_orig.columns)

np.random.seed(0)

aod_b = []
eod_b = []
aod_a = []
eod_a = []
acc_a = []
acc_b = []
ce_list = []
recall_a = []
recall_b = []
false_a = []
false_b = []
DI_a = []
SPD_a = []
DI_b = []
SPD_b = []
IDI_a = []
IDI_b = []
PE_a = []
PE_b = []
ce_times = []

for k in range(100):
    print('------the {}th turn------'.format(k))
    dataset_orig_train, dataset_orig_test = train_test_split(dataset_orig, test_size=0.15, random_state=None, shuffle=True)

    X_train, y_train = dataset_orig_train.loc[:, dataset_orig_train.columns != 'Probability'], dataset_orig_train['Probability']
    X_test, y_test = dataset_orig_test.loc[:, dataset_orig_test.columns != 'Probability'], dataset_orig_test['Probability']

    column_train = [column for column in X_train]

    clf = LogisticRegression(C=1.0, penalty='l2', solver='liblinear', max_iter=100)

    from aif360.datasets import BinaryLabelDataset, StructuredDataset
    from aif360.algorithms.preprocessing import Reweighing
    from aif360.metrics import ClassificationMetric
    from aif360.metrics import BinaryLabelDatasetMetric

    dataset_t = BinaryLabelDataset(favorable_label=1.0,
                                   unfavorable_label=0.0,
                                   df=dataset_orig_test,
                                   label_names=['Probability'],
                                   protected_attribute_names=['sex'],
                                   )
    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    dataset_pred = dataset_t.copy()
    dataset_pred.labels = y_pred
    attr = dataset_t.protected_attribute_names[0]
    idx = dataset_t.protected_attribute_names.index(attr)
    privileged_groups = [{attr: dataset_pred.privileged_protected_attributes[idx][0]}]
    unprivileged_groups = [{attr: dataset_pred.unprivileged_protected_attributes[idx][0]}]

    class_metrics = ClassificationMetric(dataset_t, dataset_pred, unprivileged_groups=unprivileged_groups,
                                         privileged_groups=privileged_groups)
    b_metrics = BinaryLabelDatasetMetric(dataset_pred, unprivileged_groups=unprivileged_groups,
                                         privileged_groups=privileged_groups)
    print("Disparate Impact:", class_metrics.disparate_impact())
    print("Statistical Parity Difference:", class_metrics.statistical_parity_difference())
    DI_b.append(class_metrics.disparate_impact())
    SPD_b.append(class_metrics.statistical_parity_difference())

    print("accuracy :", class_metrics.accuracy())
    print("recall :", class_metrics.recall())
    print("far:", class_metrics.false_positive_rate())
    print("aod:", class_metrics.average_odds_difference())
    print("eod:", class_metrics.equal_opportunity_difference())
    acc_b.append(class_metrics.accuracy())
    recall_b.append(class_metrics.recall())
    false_b.append(class_metrics.false_positive_rate())
    aod_b.append(class_metrics.average_odds_difference())
    eod_b.append(class_metrics.equal_opportunity_difference())

    IDI_b.append(1 / class_metrics.disparate_impact())
    PE_b.append(class_metrics.false_positive_rate_difference())

    slope_store = []
    intercept_store = []
    rvalue_store = []
    pvalue_store = []
    column_u = []
    flag = 0
    ce = []
    times = 0
    def Linear_regression(x, slope, intercept):
        return x * slope + intercept
    for i in column_train:
        flag = flag + 1
        if i != 'sex':
            slope, intercept, rvalue, pvalue, stderr = stats.linregress(X_train['sex'], X_train[i])
            rvalue_store.append(rvalue)
            pvalue_store.append(pvalue)
            if pvalue < 0.05:
                times = times + 1
                column_u.append(i)
                ce.append(flag)
                slope_store.append(slope)
                intercept_store.append(intercept)
                X_train[i] = X_train[i] - Linear_regression(X_train['sex'], slope, intercept)

    ce_times.append(times)
    ce_list.append(ce)

    X_train = X_train.drop(['sex'], axis=1)

    for i in range(len(column_u)):
        X_test[column_u[i]] = X_test[column_u[i]] - Linear_regression(X_test['sex'], slope_store[i], intercept_store[i])

    X_test = X_test.drop(['sex'], axis=1)

    clf.fit(X_train, y_train)
    y_pred = clf.predict(X_test)
    dataset_pred = dataset_t.copy()
    dataset_pred.labels = y_pred
    class_metrics = ClassificationMetric(dataset_t, dataset_pred, unprivileged_groups=unprivileged_groups,
                                         privileged_groups=privileged_groups)
    b_metrics = BinaryLabelDatasetMetric(dataset_pred, unprivileged_groups=unprivileged_groups,
                                         privileged_groups=privileged_groups)
    print("Disparate Impact:", class_metrics.disparate_impact())
    print("Statistical Parity Difference:", class_metrics.statistical_parity_difference())
    DI_a.append(class_metrics.disparate_impact())
    SPD_a.append(class_metrics.statistical_parity_difference())

    print("accuracy :", class_metrics.accuracy())
    print("recall :", class_metrics.recall())
    print("far:", class_metrics.false_positive_rate())
    print("aod:", class_metrics.average_odds_difference())
    print("eod:", class_metrics.equal_opportunity_difference())
    acc_a.append(class_metrics.accuracy())
    recall_a.append(class_metrics.recall())
    false_a.append(class_metrics.false_positive_rate())
    aod_a.append(class_metrics.average_odds_difference())
    eod_a.append(class_metrics.equal_opportunity_difference())

    IDI_a.append(1 / class_metrics.disparate_impact())
    PE_a.append(class_metrics.false_positive_rate_difference())

# DI, SPD are the original value, different from the value reported in the paper.
print('---Original---')
print('Aod before:', np.mean(np.abs(aod_b)))
print('Eod before:', np.mean(np.abs(eod_b)))
print('Acc before:', np.mean(acc_b))
print('Far before:', np.mean(false_b))
print('recall before:', np.mean(recall_b))
print('DI before:', np.mean(DI_b))
print('SPD before:', np.mean(np.abs(SPD_b)))
print('IDI before:', np.mean(np.abs(IDI_b)))
print('PE before:', np.mean(np.abs(PE_b)))

print('---LTDD---')
print('Aod after:', np.mean(np.abs(aod_a)))
print('Eod after:', np.mean(np.abs(eod_a)))
print('Acc after:', np.mean(acc_a))
print('Far after:', np.mean(false_a))
print('recall after:', np.mean(recall_a))
print('DI after:', np.mean(DI_a))
print('SPD after:', np.mean(np.abs(SPD_a)))
print('IDI after:', np.mean(np.abs(IDI_a)))
print('PE after:', np.mean(np.abs(PE_a)))
