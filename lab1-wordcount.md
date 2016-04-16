### Lab 1: Multi-File Word Count

In this lab, you will become acquainted with your Spark installation, and run your first Spark job -- a multi-file word count.

> The instructor should have explained how to install Spark on your machine. One option is to use the instructor's VirtualBox appliance, which you can import in the VirtualBox application. The appliance has Spark 1.6.1 installed, and has all the necessary data files for this and subsequent exercises in the `~/data` directory.
> 
> Alternatively, you can install Spark yourself. Download it from [spark.apache.org](http://spark.apache.org/downloads.html) -- make sure to select a prepackaged binary version, such as [Spark 1.6.1 for Hadoop 2.6](http://www.apache.org/dyn/closer.lua/spark/spark-1.6.1/spark-1.6.1-bin-hadoop2.6.tgz). Extract the archive to some location on your system. Then, download the [data files](https://www.dropbox.com/s/un1zr1jg6buoe3a/data.zip?dl=0) for the labs and place them in `~/data`.
> 
> **NOTE**: If you install Spark on Windows (not in a virtual machine), many things are going to be more difficult. Ask the instructor for advice if necessary.

___

#### Task 1: Inspecting the Spark Installation

Open a terminal window. Navigate to the directory where you extracted Apache Spark. On the instructor-provided virtual machine, this is `~/spark`.

Inspect the files in the `bin` directory. You will soon use `pyspark` to launch your first Spark job. Also note `spark-submit`, which is used to submit standalone Spark programs to a cluster.

Inspect the scripts in the `sbin` directory. These scripts help with setting up a stand-alone Spark cluster, deploying Spark to EC2 virtual machines, and a bunch of additional tasks.

Finally, take a look at the `examples` directory. You can find a number of stand-alone demo programs here, covering a variety of Spark APIs.

___

#### Task 2: Inspecting the Lab Data Files

In this lab, you will implement a multi-file word count. The texts you will use are freely available books from [Project Gutenberg](http://www.gutenberg.org), including classics such as Lewis Carroll's "Alice in Wonderland" and Jane Austin's "Pride and Prejudice".

Take a look at some of the text files in the `~/data` directory. From the terminal, run:

```
head -n 50 ~/data/*.txt | less
```

This shows the first 50 lines of each file. Press SPACE to scroll, or `q` to exit `less`.

___

#### Task 3: Implementing a Multi-File Word Count

Navigate to the Spark installation directory, and run `bin/pyspark`. After a few seconds, you should see an interactive Python shell, which has a pre-initialized `SparkContext` object called `sc`.

```
Welcome to
      ____              __
     / __/__  ___ _____/ /__
    _\ \/ _ \/ _ `/ __/  '_/
   /__ / .__/\_,_/_/ /_/\_\   version 1.6.1
      /_/

Using Python version 2.7.6 (default, Jun 22 2015 17:58:13)
SparkContext available as sc, HiveContext available as sqlContext.
>>>
```

To explore the available methods, run the following command:

```python
dir(sc)
```

In this lab, you are going to use the `sc.textFile` method. To figure out what it does, run the following command:

```python
help(sc.textFile)
```

Note that even though it's not mentioned in the short documentation snippet you just read, the `textFile` method can also work with a directory path or a wildcard filter such as `/home/vagrant/data/*.txt`.

> Of course, if you are not using the instructor-supplied appliance, your `data` directory might reside in a different location.

Your first task is to print out the number of lines in all the text files, combined. In general, you should try to come up with the solution yourself, and only then continue reading for the "school" solution.

**Solution**:

```python
sc.textFile("/home/vagrant/data/*.txt").count()
```

Great! Your next task is to implement the actual word-counting program. You've already seen one in class, and now it's time for your own. Print the top 10 most frequent words in the provided books.

**Solution**:

```python
lines = sc.textFile("/home/vagrant/data/*.txt")
words = lines.flatMap(lambda line: line.split())
pairs = words.map(lambda word: (word, 1))
freqs = pairs.reduceByKey(lambda a, b: a + b)
top10 = freqs.sortBy(lambda (word, count): -count).take(10)
for (word, count) in top10:
    print("the word '%s' appears %d times" % (word, count))
```

To be honest, we don't really care about words like "the", "a", and "of". Ideally, we would have a list of stop words to ignore. For now, modify your solution to filter out words shorter than 4 characters.

Additionally, you might be wondering about the types of all these variables -- most of them are RDDs. To trace the lineage of an RDD, use the `toDebugString` method. For example, `print(freqs.toDebugString())` should display the logical plan for that RDD's evaluation. We will discuss some of these concepts later.

___

#### Task 4: Run a Stand-Alone Spark Program

You're now ready to convert your multi-file word count into a stand-alone Spark program. Create a new file called `wordcount.py`.

Initialize a `SparkContext` as follows:

```python
from pyspark import SparkContext

def run():
    sc = SparkContext()
    # TODO Your code goes here

if __name__ == "__main__":
    run()
```

Now, you can copy and paste your solution in the `run` method. Congratulations -- you have a stand-alone Spark program! To run it, navigate back to the Spark installation directory in your terminal, and run the following command:

```
bin/spark-submit --master 'local[*]' path/to/wordcount.py
```

You should replace `path/to/wordcount.py` with the actual path on your system. If everything went fine, you should see a lot of diagnostic output, but somewhere buried in it would be your top 10 words.

___

#### Discussion

Instead of using `reduceByKey`, you could have used a method called `countByValue`. Read its documentation, and try to understand how it works. Would using it be a good idea?
