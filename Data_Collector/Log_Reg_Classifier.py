import os
import numpy as np
import random
from bunch import Bunch

from sklearn.feature_extraction.text import CountVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import precision_recall_fscore_support as prf_evaluator


# the path to the data directories
# DEP = "./reddit_depression"
# NON_DEP = "./reddit_non_depression"
# DEP = "./blogs_depression"
# NON_DEP = "./blogs_non_depression"
DEP = "./mixed_depression"
NON_DEP = "./mixed_non_depression"

# analyzer parameter ('word' - for word tokens, 'char_wb' - for character tokens)
ANALYZER = "word"

# The max for the n-gram range
NGRAM_MAX = 3

# Logistic Regression penalty
PENALTY = "l1"

# number of K-fold splits
KFOLD_SPLITS = 10

# the average parameter for the precision/recall evaluator
EVAL_AVERAGE = "binary"


def process_post(file_path):
    """
    Reads a file and extracts the raw text
    :param file_path: the path to the file
    :return: the processed string of raw text
    """

    # open and read the file
    post = open(file_path, 'r')

    text = ''

    # read the post line by line
    for line in post:

        if line.strip():  # check if the line isn't empty
            # decode the line and append to the text string
            line = line.decode('unicode-escape').encode('utf-8').strip()
            text += line + ' '

    return text


def construct_data(dep_fnames, non_dep_fnames, dep_dir, non_dep_dir):
    """
    Constructs the data bunch that contains file names, file paths, raw file texts, and targets of files
    :param dep_fnames: list of file names in depression directory
    :param non_dep_fnames: list of file names in non-depression directory
    :return: the constructed data bunch
    """
    # instantiate the data bunch
    data = Bunch()

    # join the 2 arrays of file names
    file_names = np.concatenate((dep_fnames, non_dep_fnames))

    # shuffle the data and add to the data bunch
    random.shuffle(file_names)

    # assign the shuffled file names array to data
    data.filenames = file_names

    # instantiate the lists for data attributes
    data.filepath = []  # path to files
    data.data = []  # raw texts
    data.target = []  # target category index

    # iterate the file names
    for index in range(len(file_names)):
        fn = file_names[index]

        # if the file belongs to depression cat
        if file_names[index] in dep_fnames:

            # append the corresponding index to the target attribute
            data.target.append(0)

            # find and append the path of the file to path attribute
            data.filepath.append(os.path.join(dep_dir, fn))

        # repeat for the other category
        else:
            data.target.append(1)
            data.filepath.append(os.path.join(non_dep_dir, fn))

        # get the path of the current file
        f_path = data.filepath[index]

        # read the file and pre-process the text
        post_text = process_post(f_path)

        # append it to the data attribute
        data.data.append(post_text)

    return data


def make_count_vectors(raw_data):
    """
    transforms text data into count vectors
    :param raw_data: data to transform
    :return: the count vectors
    """
    # instantiate the vectorizer
    vectorizer = CountVectorizer(ngram_range=(1, NGRAM_MAX), analyzer=ANALYZER, encoding='utf8')

    # transform the data into vectors
    x_counts = vectorizer.fit_transform(raw_data)

    print "Count vectors shape: ", x_counts.shape

    return x_counts


def make_tfidf_vectors(raw_data):
    """
    transforms text data into tf-idf vectors
    :param raw_data: data to transform
    :return: the tf-idf vectors
    """
    # instantiate the vectorizer
    vectorizer = TfidfVectorizer(ngram_range=(1, NGRAM_MAX), analyzer=ANALYZER, encoding='utf8')

    # transform the data into vectors
    x_tfidf = vectorizer.fit_transform(raw_data)

    print "Tf-idf vectors shape: ", x_tfidf.shape

    return x_tfidf


def train_lr_model(x_train, y_train):
    """
    Creates a logistic regression model and fits the given data to it
    :param x_train: train set to fir to model
    :param y_train: train label set to fit to model
    :return: the model
    """

    # define the logistic regression classifier model
    lr_clf = LogisticRegression(penalty=PENALTY, class_weight='balanced')

    # fit the data to the model
    lr_clf.fit(x_train, y_train)

    return lr_clf


def evaluate(model, x_test, y_test):
    """
    Calculates 2 types of accuracies, precision, recall, f-score and support for the given fold
    :param model: trained model
    :param x_test: test set
    :param y_test: test label set
    :return: bunch with evaluation scores as attributes
    """

    # create the evaluation bunch for the given fold
    ev = Bunch()

    # calculate the cross validation
    ev.cv = model.score(x_test, y_test)

    # calculate the roc score
    y_pred_lr = model.predict_proba(x_test)[:, 1]
    ev.roc = roc_auc_score(y_test, y_pred_lr)

    # get the precision, recall, f-score
    ev.precision, ev.recall, ev.fscore, ev.supp = \
        prf_evaluator(y_test, model.predict(x_test), average=EVAL_AVERAGE)

    return ev


def classify_kfold(x, y):
    """
    Splits the data into K stratified folds and calculates the accuracy means of a logistic regression classifier
    :param x: vector data to split into train/test sets
    :param y: target labels of the data
    :return: mean cross validation accuracy and roc accuracy
    """

    # Create the stratified fold splits model
    skf = StratifiedKFold(n_splits=KFOLD_SPLITS, shuffle=True)

    # create the evaluation bunch and its attributes
    evaluation = Bunch()
    evaluation.precision = []
    evaluation.recall = []
    evaluation.fscore = []

    cv_mean = []
    roc_mean = []

    # iterate all the indices the split() method returns
    for indx, (train_indices, test_indices) in enumerate(skf.split(x, y)):
        # print the running fold
        print "Training on fold " + str(indx + 1) + "/10..."

        # Generate batches from indices
        x_train, x_test = x[train_indices], x[test_indices]
        y_train, y_test = y[train_indices], y[test_indices]

        # fit the data to the logistic regression model
        lr_model = train_lr_model(x_train, y_train)

        # evaluate the model
        fold_ev = evaluate(lr_model, x_test, y_test)

        # append all evaluation values to the mean lists and evaluation bunch
        cv_mean.append(fold_ev.cv)
        roc_mean.append(fold_ev.roc)

        evaluation.precision.append(fold_ev.precision)
        evaluation.recall.append(fold_ev.recall)
        evaluation.fscore.append(fold_ev.fscore)

    # calculate the mean for both accuracies and add to the evaluation
    evaluation.cv = np.mean(cv_mean)
    evaluation.roc = np.mean(roc_mean)

    # return the evaluation bunch
    return evaluation


# -------------------------------------------------------------------------------
# Process the data
# -------------------------------------------------------------------------------

print "\nProcessing data"

# lists of file names in both directories
dep_fnames = np.array(os.listdir(DEP))
non_dep_fnames = np.array(os.listdir(NON_DEP))

print "number of depression files: ", len(dep_fnames)
print "number of non-depression files: ", len(non_dep_fnames)

# Construct the data
data = construct_data(dep_fnames, non_dep_fnames, DEP, NON_DEP)

print "number of texts in data ", len(data.data)
print "targets for the first 10 files: ", data.target[:10]
print "number of targets of files in data", len(data.target)
print "first 2 files: ", data.data[:2]


# -------------------------------------------------------------------------------
# Vectors and Model
# -------------------------------------------------------------------------------

print "\ncreating data vectors"

print("\ncount vectors: \n")

# create the target labels array
labels = np.array(data.target)

# --------------------------------------------
# Frequency count vectors
# --------------------------------------------

# transform raw data into count vectors
X_counts = make_count_vectors(data.data)

# fit the data to the model and get the accuracy scores
count_eval = classify_kfold(X_counts, labels)


print "\ncross validation: ", count_eval.cv
print "roc: ", count_eval.roc
print "precision for the first 10: ", count_eval.precision[:10]
print "recall for the first 10: ", count_eval.recall[:10]
print "f-score for the first 10: ", count_eval.fscore[:10]


# ---------------------------------------------
# Tf-idf vectors
# ---------------------------------------------

print("\nTf-idf vectors: \n")

# transform raw data into tf-idf vectors
X_tfidf = make_tfidf_vectors(data.data)

# fit the data to the model and get the accuracy scores
tfidf_eval = classify_kfold(X_tfidf, labels)

print "\ncross validation: ", tfidf_eval.cv
print "roc: ", tfidf_eval.roc
print "precision for the first 10: ", tfidf_eval.precision[:10]
print "recall for the first 10: ", tfidf_eval.recall[:10]
print "f-score for the first 10: ", tfidf_eval.fscore[:10]
