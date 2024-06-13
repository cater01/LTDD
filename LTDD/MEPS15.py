import pandas as pd
import random, time, csv
import numpy as np
import math, copy, os
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from scipy import stats

import sys
sys.path.append(os.path.abspath('..'))

from aif360.datasets import MEPSDataset19
from aif360.datasets import BinaryLabelDataset, StructuredDataset
from aif360.metrics import ClassificationMetric, BinaryLabelDatasetMetric

# Load dataset
dataset_orig = MEPSDataset19()
dataset_orig = dataset_orig.convert_to_dataframe()[0]

dataset_orig.rename(index=str, columns={"UTILIZATION": "Probability"}, inplace=True)
dataset_orig.rename(index=str, columns={"RACE": "race"}, inplace=True)

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
idi_b = []
idi_a = []
pe_b = []
pe_a = []
ce_times = []

# Function to calculate IDI
def calculate_idi(y_true, y_pred):
    imbalance_degree = abs(sum(y_true) - sum(y_pred)) / len(y_true)
    return imbalance_degree

# Function to calculate PE
def calculate_pe(y_true, y_pred, privileged, unprivileged):
    privileged_accuracy = accuracy_score(y_true[privileged], y_pred[privileged])
    unprivileged_accuracy = accuracy_score(y_true[unprivileged], y_pred[unprivileged])
    return abs(privileged_accuracy - unprivileged_accuracy)

for k in range(100):
    print('------the {}th turn------'.format(k))

    dataset_orig_train, dataset_orig_test = train_test_split(dataset_orig, test_size=0.15, random_state=None, shuffle=True)

    X_train, y_train = dataset_orig_train.loc[:, dataset_orig_train.columns != 'Probability'], dataset_orig_train['Probability']
    X_test, y_test = dataset_orig_test.loc[:, dataset_orig_test.columns != 'Probability'], dataset_orig_test['Probability']

    column_train = [column for column in X_train]

    clf = LogisticRegression(C=1.0, penalty='l2', solver='liblinear', max_iter=100)

    dataset_t = BinaryLabelDataset(favorable_label=1.0,
                                   unfavorable_label=0.0,
                                   df=dataset_orig_test,
                                   label_names=['Probability'],
                                   protected_attribute_names=['race'],
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

    # Calculate IDI and PE before debiasing
    privileged_indices = [i for i in range(len(y_test)) if X_test.iloc[i]['race'] == privileged_groups[0]['race']]
    unprivileged_indices = [i for i in range(len(y_test)) if X_test.iloc[i]['race'] == unprivileged_groups[0]['race']]
    idi_b.append(calculate_idi(y_test, y_pred))
    pe_b.append(calculate_pe(y_test, y_pred, privileged_indices, unprivileged_indices))

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
        if i != 'race':
            slope, intercept, rvalue, pvalue, stderr = stats.linregress(X_train['race'], X_train[i])
            rvalue_store.append(rvalue)
            pvalue_store.append(pvalue)
            if i != 'sex':
                if pvalue < 0.05:
                    times = times + 1
                    column_u.append(i)
                    ce.append(flag)
                    slope_store.append(slope)
                    intercept_store.append(intercept)
                    X_train[i] = X_train[i] - Linear_regression(X_train['race'], slope, intercept)

    ce_times.append(times)
    ce_list.append(ce)

    X_train = X_train.drop(['race'], axis=1)

    for i in range(len(column_u)):
        X_test[column_u[i]] = X_test[column_u[i]] - Linear_regression(X_test['race'], slope_store[i],
                                                                      intercept_store[i])

    X_test = X_test.drop(['race'], axis=1)

    dataset_t = BinaryLabelDataset(favorable_label=1.0,
                                   unfavorable_label=0.0,
                                   df=dataset_orig_test,
                                   label_names=['Probability'],
                                   protected_attribute_names=['race'],
                                   )
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

    # Calculate IDI and PE after debiasing
    idi_a.append(calculate_idi(y_test, y_pred))
    pe_a.append(calculate_pe(y_test, y_pred, privileged_indices, unprivileged_indices))

print('---Original---')
print('Aod before:', np.mean(np.abs(aod_b)))
print('Eod before:', np.mean(np.abs(eod_b)))
print('Acc before:', np.mean(acc_b))
print('Far before:', np.mean(false_b))
print('recall before:', np.mean(recall_b))
print('DI before:', np.mean(DI_b))
print('SPD before:', np.mean(np.abs(SPD_b)))
print('IDI before:', np.mean(idi_b))
print('PE before:', np.mean(pe_b))

print('---LTDD---')
print('Aod after:', np.mean(np.abs(aod_a)))
print('Eod after:', np.mean(np.abs(eod_a)))
print('Acc after:', np.mean(acc_a))
print('Far after:', np.mean(false_a))
print('recall after:', np.mean(recall_a))
print('DI after:', np.mean(DI_a))
print('SPD after:', np.mean(np.abs(SPD_a)))
print('IDI after:', np.mean(idi_a))
print('PE after:', np.mean(pe_a))
