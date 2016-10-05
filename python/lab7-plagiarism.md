### Lab 7: Plagiarism Detection

In this lab, you will use Spark's Machine Learning library (MLLib) to perform plagiarism detection -- determine how similar a document is to a collection of existing documents.

You will use the [TF-IDF](https://en.wikipedia.org/wiki/Tf–idf) algorithm, which extracts numeric features (vectors) from text documents. TF-IDF stands for Term Frequency Inverse Document Frequency, and it is a normalized representation of how frequently a term (word) occurs in a document that belongs to a set of documents:

* The *TF*[*t*, *D*] -- term frequency of term *t* in a document *D* -- is simply the number of times *t* appears in *D*.

* The *DF*[*t*] -- document frequency of term *t* in a collection of documents *D*(1), ..., *D*(*n*) -- is the number of documents in which *t* appears.

* The *TFIDF*[*t*, *D*(*i*)] of term *t* in a document *D*(*i*) in a collection of documents *D*(1), ..., *D*(*n*) is *TF*[*t*, *D*(*i*)] · *log*[(*n* + 1) / (*DF*[*t*, *D*(*i*)] + 1)].

These values are not very hard to compute, but when the documents are very large there is a lot of room for optimization. MLLib (the machine learning library that ships with Spark) has optimized versions of these feature extraction algorithms, among many other ML algorithms for clustering, classification, dimensionality reduction, etc.

The similarity between two documents can be obtained by computing the cosine similarity (normalized dot product) of their TF-IDF vectors. For two documents *D*, *E* with TF-IDF vectors *t*, *s* the cosine similarity is defined as *t* ￮ *s* / |*t*| · |*s*| -- note this is a number between 0 and 1, due to normalization. If the cosine similarity is 1, the documents are identical; if the similarity is 0, the documents have nothing in common.

___

#### Task 1: Inspecting the Data

In the `~/data/essays` directory you'll find a collection of 1497 essays written by students of English at the University of Uppsala, also known as the [Uppsala Student English Corpus (USE)](http://www.engelska.uu.se/Forskning/engelsk_sprakvetenskap/Forskningsomraden/Electronic_Resource_Projects/USE-Corpus/). Your task will be to determine whether another essay, in the file `~/data/essays/candidate`, has been plagiarized from one of the other essays, or whether it is original work.

First, let's take a look at some of the files. From a terminal window, execute the following command to inspect the first 10 files:

```
ls ~/data/essays/*.txt | head -n 10 | xargs less
```

In the resulting `less` window, use `:n` to move to the next file, and `q` to quit. As you can see, these are student essays on various topics. Now take a look at the candidate file:

```
less ~/data/essays/candidate
```

___

#### Task 2: Detecting Document Similarity

First, you need to load the documents to an RDD of word vectors, one per document. Note that the documents are need to be cleaned up so that we indeed produce a vector per document. These will be processed by MLLib to obtain an RDD of TF-IDF vectors.

```python
import re

# An even better cleanup would include stemming,
# careful punctuation removal, etc.
def clean(doc):
    return filter(lambda w: len(w) > 2,
                  map(lambda s: s.lower(), re.split(r'\W+', doc)))

essays = sc.wholeTextFiles("file:///home/ubuntu/data/essays/*.txt")    \
           .mapValues(clean)                                            \
           .cache()
essayNames = essays.map(lambda (filename, contents): filename).collect()
docs = essays.map(lambda (filename, contents): contents)
```

Next, you can compute the TF vectors for all the document vectors using the `HashingTF` algorithm:

```python
from pyspark.mllib.feature import HashingTF, IDF

hashingTF = HashingTF()
tf = hashingTF.transform(docs)
tf.cache()      # we will reuse it twice for TF-IDF
```

And now you can find the TF-IDF vectors -- this requires two passes: one to find the IDF vectors and another to scale the terms in the vectors.

```python
idf = IDF().fit(tf)
tfidf = idf.transform(tf)
```

Now that you have the TF-IDF vectors for the entire dataset, you can compute the similarity of a new document, `candidate`, to all the existing documents. To do so, you need to find that document's TF-IDF vector, and then find the cosine similarity of that vector with all the existing TF-IDF vectors:

```python
candidate = clean(open('/home/ubuntu/data/essays/candidate').read())
candidateTf = hashingTF.transform(candidate)
candidateTfIdf = idf.transform(candidateTf)
similarities = tfidf.map(lambda v: v.dot(candidateTfIdf) /
                                   (v.norm(2) * candidateTfIdf.norm(2)))
```

All that's left is pick the most similar documents and see if there's high similarity:

```python
topFive = sorted(enumerate(similarities.collect()), key=lambda (k, v): -v)[0:5]
for idx, val in topFive:
    print("doc '%s' has score %.4f" % (essayNames[idx], val))
```

You can experiment with slight modifications to the text of `candidate` and see if our naive algorithm can still detect its origin.

___

#### Discussion

Why did we use `similarities.collect()` to bring the dataset to the driver program and then sort the results?

Which parts of working with MLLib do you find particularly useful, and which parts seem confusing?
