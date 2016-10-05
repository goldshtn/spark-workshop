### Lab 6: Movie PageRank

In this lab, you will run the [PageRank](https://en.wikipedia.org/wiki/PageRank) algorithm on a dataset of movie references, and try to identify the most popular movies based on how many references they have. The dataset you'll be working with is [provided by IMDB](http://www.imdb.com/interfaces).

___

#### Task 1: Inspecting the Data

The original IMDB dataset is not very friendly for automatic processing. You can find it in the `~/data` folder of the VirtualBox appliance, or download it yourself from the IMDB FTP website -- it's the `movie-links.list` dataset. Here's a sampler:

```
"#1 Single" (2006)
  (referenced in "Howard Stern on Demand" (2005) {Lisa Loeb & Sister})

"#LawstinWoods" (2013) {The Arrival (#1.1)}
  (references "Lost" (2004))
  (references Kenny Rogers and Dolly Parton: Together (1985) (TV))
  (references The Grudge (2004))
  (references The Ring (2002))
```

Instead of using this raw dataset, there's a pre-processed one available in the `processed-movie-links.txt` file (it doesn't contain all the information from the first one, but we can live with that). Again, here's a sample:

```
$ head processed-movie-links.txt
#LawstinWoods --> Lost
#LawstinWoods --> Kenny Rogers and Dolly Parton: Together
#LawstinWoods --> The Grudge
#LawstinWoods --> The Ring
#MonologueWars --> Trainspotting
Community --> $#*! My Dad Says
Conan --> $#*! My Dad Says
Geeks Who Drink --> $#*! My Dad Says
Late Show with David Letterman --> $#*! My Dad Says
```

___

#### Task 2: Finding Top Movies

Now it's time to implement the PageRank algorithm. It's probably the most challenging task so far, so here are some instructions that might help.

> **NOTE**: This is a very naive implementation of PageRank, which doesn't really try to optimize and minimize data shuffling. The GraphX library, which is also part of Spark, has a [native implementation of PageRank](https://spark.apache.org/docs/1.1.0/graphx-programming-guide.html#pagerank). You can try it in Task 3.

Begin by parsing the movie references to an RDD called `links` (using `SparkContext.textFile` and `map`) and processing it into key/value pairs where the key is the movie and the value is a list of all movies referenced by it.

Next, create an RDD called `ranks` of key/value pairs where the key is the movie and the value is its rank, set to 1.0 initially for all movies.

Next, write a function `computeContribs` that takes a list of referenced movies and the referencing movie's rank, and returns a list of key/value pairs where the key is the movie and the value is its rank contribution. Each of the referenced movies gets an equal portion of the referencing movie's rank. For example, if "Star Wars" currently has rank 1.0 and references "Wizard of Oz" and "Star Trek", then the function should return two pairs: `("Wizard of Oz", 0.5)` and `("Star Trek", 0.5)`.

Next, we're getting to the heart of the algorithm. In a loop that repeats 10 times, compute a new RDD called `contribs` which is formed by joining `links` and `ranks` (the join is on the movie name). Use `flatMap` to collect the results from `computeContribs` on each key/value pair in the result of the join. To understand what we're doing, consider that joining `links` and `ranks` produces a pair RDD whose elements look like this:

```python
("Star Wars", ("Wizard of Oz", "Star Trek", 0.8))
```

Now, invoking `computeContribs` on the value of this pair produces a list of pairs:

```python
[("Wizard of Oz", 0.4), ("Star Trek", 0.4)]
```

By applying `computeContribs` and collecting the results with `flatMap`, we get a pair RDD that has, for each movie, its contribution from each of its neighbors. You should now sum (reduce) this pair RDD by key, so we get the sum of each movie's contributions from its neighbors.

Next, the PageRank algorithm dictates that we should recompute each movie's rank from the `ranks` RDD as 0.15 + 0.85 times its neighbors' contribution (you can use `mapValues` for this). This recomputation produces a new input value for `ranks`.

Finally, when your loop is done, display the 10 highest-ranked movies and their PageRank.

**Solution**:

```python
# links is RDD of (movie, [referenced movies])
links = sc.textFile("file:///home/vagrant/data/processed-movie-links.txt") \
          .map(lambda line: line.split("-->"))                             \
          .map(lambda (a, b): (a.strip(), b.strip()))                      \
          .distinct()                                                      \
          .groupByKey()                                                    \
          .cache()

# ranks is RDD of (movie, 1.0)
ranks = links.map(lambda (movie, _): (movie, 1.0))

# each of our references gets a contribution of our rank divided by the
# total number of our references
def computeContribs(referenced, rank):
    count = len(referenced)
    for movie in referenced:
        yield (movie, rank / count)

for _ in range(0, 10):
    # recompute each movie's contributions from its referencing movies
    contribs = links.join(ranks).flatMap(lambda (_, (referenced, rank)):
        computeContribs(referenced, rank)
                                        )
    # recompute the movie's ranks by accounting all its referencing
    # movies' contributions
    ranks = contribs.reduceByKey(lambda a, b: a + b)                       \
                    .mapValues(lambda rank: rank*0.85 + 0.15)

for movie, rank in ranks.sortBy(lambda (_, rank): -rank).take(10):
    print('"%s" has rank %2.2f' % (movie, rank))
```

___

#### Task 3: GraphX PageRank

The PageRank algorithm we implemented in the previous task is not very efficient. For example, running it on our dataset for 100 iterations took approximately 15 minutes on a 4-core machine. Considering that there are "just" about 25,000 movies ranked, this is not a very good result.

Spark ships with a native graph algorithm library called GraphX. Unfortunately, it doesn't yet have a Python binding -- you can only use it from Scala and Java. But we're not going to let that stop us!

Navigate to the Spark installation directory (`~/spark` in the VirtualBox appliance) and run `bin/spark-shell`. This is the Spark Scala REPL, which is very similar to PySpark, except it uses Scala. First, you're going to need a couple of import statements:

```scala
import org.apache.spark._
import org.apache.spark.graphx._
import org.apache.spark.graphx.lib._
```

Next, load the graph edges from the supplied `~/data/movie-edges.txt` file:

```scala
val graph = GraphLoader.edgeListFile(sc,
    "file:///home/vagrant/data/movie-edges.txt")
```

This file was generated from the same dataset, but it has a format that GraphX natively supports. You can check out the format by running the following commands:

```
$ head ~/data/movie-edges.txt
0 1
2 3
2 4
2 5
2 6
7 8
9 10
11 10
12 10
13 10
$ head ~/data/movie-vertices.txt
0 Howard Stern on Demand
1 #1 Single
2 #LawstinWoods
3 Lost
4 Kenny Rogers and Dolly Parton: Together
5 The Grudge
6 The Ring
7 #MonologueWars
8 Trainspotting
9 Community
```

That's it -- we can run PageRank. Instead of working with a set number of iterations, the PageRank implementation in GraphX can run until the ranks converge (stop changing). We'll set the tolerance threshold to 0.0001, which means we're waiting for convergence up to that threshold. This computation took just under 2 minutes on the same machine!

```scala
val pageRank = PageRank.runUntilConvergence(graph, 0.0001).vertices.map(
    p => (p._1.toInt, p._2)).cache()
```

> The resulting graph vertices are pairs of the vertex id and its rank. We use `toInt` to convert it to an int for the subsequent join operation.

Next, load the vertices file that specifies the movie title for each id:

```scala
val titles = sc.textFile("file:///home/vagrant/data/movie-vertices.txt").map(
    line => {
        val parts = line.split(" ");
        (parts(0).toInt, parts.drop(1).mkString(" "))
    }
)
```

Finally, join the ranks and the titles and sort the result to print the top 10 movies by rank:

```scala
titles.join(pageRank).sortBy(-_._2._2).map(_._2).take(10)
```

___

#### Discussion

Besides being easier to use than implementing your own algorithms, why do you think GraphX has potential for being faster than something you'd roll by hand?
