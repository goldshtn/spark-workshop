### Lab 1: Multi-File Word Count

In this lab, you will get familiar with Spark and run your first Spark job -- a multi-file word count.

___

#### Task 1: Inspecting the Spark

Open a terminal window. Navigate to the directory where you extracted Apache Spark. On the instructor-provided virtual machine, this is `~/spark`.

Inspect the files in the `bin` directory. You will soon use `spark-shell` to launch your first Spark job. Also note `spark-submit`, which is used to submit standalone Spark programs to a cluster.

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

Navigate to the Spark installation directory, and run `./bin/spark-shell`. 

In this lab, you are going to use the `sc.textFile` method. 
The `textFile` method can work with a directory path or a wildcard filter such as `/home/vagrant/data/*.txt`.

> Of course, if you are not using the instructor-supplied appliance, your `data` directory might reside in a different location.

Your first task is to print out the number of lines in all the text files, combined. In general, you should try to come up with the solution yourself, and only then continue reading for the "school" solution.

**Solution**:

```scala
sc.textFile("/data/books/*.tx").count()
```

Great! Your next task is to implement the actual word-counting program. You've already seen one in class, and now it's time for your own. Print the top 10 most frequent words in the provided books.

**Solution**:

```scala
val lines = sc.textFile("/data/books/*.tx")
val words = lines.flatMap(line => line.split(" ").filter(w => w != null && !w.isEmpty))
val pairs = words.map(word => (word, 1))
val freqs = pairs.reduceByKey((a, b) => a + b)
val top10 = freqs.sortBy(_._2, false).take(10)
top10.foreach(println)
```

To be honest, we don't really care about words like "the", "a", and "of". Ideally, we would have a list of stop words to ignore. For now, modify your solution to filter out words shorter than 4 characters.

Additionally, you might be wondering about the types of all these variables -- most of them are RDDs. To trace the lineage of an RDD, use the `toDebugString` method. For example, `freqs.toDebugString()` should display the logical plan for that RDD's evaluation. We will discuss some of these concepts later. If you have window asking to select modules to include make sure that 2 selected and click OK.

___

#### Task 4: Run a Stand-Alone Spark Program

Open Zeppelin at port 9995. This is a scala interpreter with web UI that will be used in the labs.
Create new note: Notebook -> Create new note.
Now, you can copy and paste your solution into the note and run it(shift+Enter) after changing path of the files to "file:///home/data/*.txt"
First lines in the result are transformations(fast computation) and later(top10) taking much more time as it is an action.


????????????????????????????????????????????????????????????????????????????????????????????????
????????????????????????????????????????????????????????????????????????????????????????????????
You're now ready to convert your multi-file word count into a stand-alone Spark program. Extract SparkStarter and then open IntelliJ IDEA. Click on import project in the popuped window navigate to the SparkStarter folder and click OK. Make sure that SBT is chosen and click next. On the next window check "Use auto-import" and click Finish.

You should see now project explorer in the left window.
Open build.sbt file, here we write all dependencies for your project. Now you have only Spark core imported.

Open src/main/scala-2.11/Starter.
This is the main class of the project. It is almost empty.
Some configuration and SparkContext are initialized.

Now, you can copy and paste your solution instead "<Enter your code here>". Congratulations -- you have a stand-alone Spark program! To run it, navigate in terminal to the project directory and run the following command: 
sbt package
This command will create a jar file that you will submit now to spark.

Now navigate back to the Spark installation directory in your terminal, and run the following command:

```
bin/spark-submit --master 'local[*]' path/to/sparkstarter_2.11-1.0.jar
```


You should replace `path/to/sparkstarter_2.11-1.0.jar` with the actual path on your system( /SparkStarter/target/scala-2.11/sparkstarter_2.11-1.0.jar). If everything went fine, you should see a lot of diagnostic output, but somewhere buried in it would be your top 10 words.
????????????????????????????????????????????????????????????????????????????????????????????????
????????????????????????????????????????????????????????????????????????????????????????????????
___

#### Discussion

Instead of using `reduceByKey`, you could have used a method called `countByValue`. Read its documentation, and try to understand how it works. Would using it be a good idea?
