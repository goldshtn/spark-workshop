### Lab 2: Flight Delay Analysis

In this lab, you will analyze a real-world dataset -- information about US flight delays in January 2016, courtesy of the United States Department of Transportation. You can [download additional datasets](http://www.transtats.bts.gov/DL_SelectFields.asp?Table_ID=236&DB_Short_Name=On-Time) later. Here's another example you might find interesting -- [US border crossing/entry data per port of entry](http://transborder.bts.gov/programs/international/transborder/TBDR_BC/TBDR_BCQ.html).

___

#### Task 1: Inspecting the Data

This dataset ships with two files (in the `/home/data` directory, if you are using the instructor-provided VirtualBox appliance). First, the `airline-format.html` file contains a brief description of the dataset, and the various data fields. For example, the `ArrDelay` field is the flight's arrival delay, in minutes. Second, the `airline-delays.csv` file is a comma-separated collection of flight records, one record per line.

Inspect the fields described in the `airline-format.html` file. Make a note of fields that describe the flight, its origin and destination airports, and any delays encountered on departure and arrival.

Let's start by counting the number of records in our dataset. Run the following command in a terminal window:

```
wc -l airline-delays.csv
```

This dataset has hundreds of thousands of records. To sample 10 records from the dataset picked at probability 0.005%, run the following command (for convenience, its output is also quoted here):

```
$ cat airline-delays.csv | cut -d',' -f1-20 | awk '{ if (rand() <= 0.00005 || FNR==1) { print $0; if (++count > 11) exit; } }'
"Year","Quarter","Month","DayofMonth","DayOfWeek","FlightDate","UniqueCarrier","AirlineID","Carrier","TailNum","FlightNum","OriginAirportID","OriginAirportSeqID","OriginCityMarketID","Origin","OriginCityName","OriginState","OriginStateFips","OriginStateName","OriginWac"
2016,1,1,20,3,2016-01-20,"AA",19805,"AA","N3AFAA","242",14771,1477102,32457,"SFO","San Francisco, CA","CA","06","California"
2016,1,1,9,6,2016-01-09,"AA",19805,"AA","N859AA","284",12173,1217302,32134,"HNL","Honolulu, HI","HI","15","Hawaii"
2016,1,1,9,6,2016-01-09,"AA",19805,"AA","N3GRAA","1227",11278,1127803,30852,"DCA","Washington, DC","VA","51","Virginia"
2016,1,1,4,1,2016-01-04,"AA",19805,"AA","N3BGAA","1450",11298,1129804,30194,"DFW","Dallas/Fort Worth, TX","TX","48","Texas"
2016,1,1,5,2,2016-01-05,"AA",19805,"AA","N3AMAA","1616",11298,1129804,30194,"DFW","Dallas/Fort Worth, TX","TX","48","Texas"
2016,1,1,20,3,2016-01-20,"AA",19805,"AA","N916US","1783",11057,1105703,31057,"CLT","Charlotte, NC","NC","37","North Carolina"
2016,1,1,2,6,2016-01-02,"AS",19930,"AS","N517AS","879",14747,1474703,30559,"SEA","Seattle, WA","WA","53","Washington"
2016,1,1,20,3,2016-01-20,"AS",19930,"AS","N769AS","568",14057,1405702,34057,"PDX","Portland, OR","OR","41","Oregon"
2016,1,1,24,7,2016-01-24,"UA",19977,"UA","","706",14843,1484304,34819,"SJU","San Juan, PR","PR","72","Puerto Rico"
2016,1,1,15,5,2016-01-15,"UA",19977,"UA","N34460","1077",12266,1226603,31453,"IAH","Houston, TX","TX","48","Texas"
2016,1,1,12,2,2016-01-12,"UA",19977,"UA","N423UA","1253",13303,1330303,32467,"MIA","Miami, FL","FL","12","Florida"
```

This displays the first 20 fields of the 10 sampled records from the file. The first line is a header line, so we printed it unconditionally. This is a typical example of structured data that we would have to parse first before analyzing it with Spark.

> We could examine the full dataset using shell commands, because it is not exceptionally big. For larger datasets that couldn't conceivably be processed or even stored on a single machine, we could have used Spark itself to perform the sampling. If you're interested, examine the `takeSample` method that Spark RDDs provide.

___

#### Task 2: Parsing CSV Data

Next, you have to parse the CSV data. The header line provides the column names, and then each subsequent line can be parsed taking these into account. In Spark there is no built-in functionality that can parse CSV files. But there is a library(com.databricks.spark.csv) that you can use to parse CSV lines. 

You must run the following code before running any Spark code. 
Otherwise you restrart Zeppilin Spark Interpreter: Interpreter -> spark box(first one) -> restart button
Now go back to your note and run:

```scala
%dep
z.reset()
z.addRepo("Spark Packages Repo").url("http://dl.bintray.com/spark-packages/maven")
z.load("com.databricks:spark-csv_2.11:1.4.0")
```

Next, create an DataFrame based on the `airline-delays.csv` file by using this library.
Note that you have access to a pre-initialized `SQLContext` object named `sqlContext`.

```scala
val flightsDF = sqlContext.read
    .format("com.databricks.spark.csv")
    .option("header", "true")      // Use first line of all files as header
    .option("inferSchema", "true") // Automatically infer data types
    .load("file:///home/data/airline-delays.csv")
```

You can check the schema by printing it:
```
flightsDF.printSchema
```

___

#### Task 3: Converting dataframe to rdd

In this lab we want to practice RDD operations. Later in this workshop we will use dataframes to manipulate data.
First we need to create case class Flight(use only several fields that you will use in this lab) with fields: Carrier, OriginCityName, ArrDelay, DestCityName,
Distance

And then create FlightsRdd from flightsDF

**Solution**:

```scala
case class Flight(Carrier: String, OriginCityName: String, ArrDelay: Double, DestCityName: String, Distance: Double)
val flightRdd = flightsDF.map(row => Flight(row.getAs("Carrier"), row.getAs("OriginCityName"), row.getAs("ArrDelay"), row.getAs("DestCityName"), row.getAs("Distance")))
```

___

#### Task 4: Querying Flights and Delays

Now that you have the flight objects, it's time to perform a few queries and gather some useful information. Suppose you're in Boston, MA. Which airline has the most flights departing from Boston?


**Solution**:

```scala
val carriersFromBoston = flightRdd.filter(f => f.OriginCityName == "Boston, MA").map(f => (f.Carrier, 1))
val carrierWithMostFlights = carriersFromBoston.reduceByKey(_ + _).sortBy(_._2, false).take(1)
```


Overall, which airline has the worst average delay? How bad was that delay?

> **HINT**: Use `combineByKey`.


**Solution**:

```scala
val avgDelay = flightRdd.filter(f => f.ArrDelay > 0)
.map(f => (f.Carrier, f.ArrDelay))
.combineByKey(d => (d, 1),
             (s:(Double, Int), d: Double) => (s._1 + d, s._2 + 1),
             (s1:(Double, Int) , s2: (Double, Int)) => (s1._1 + s2._1, s1._2 + s2._2)
)

val worstAirline = avgDelay.map{ case (car, (av, cnt)) => ((car, av/cnt)) }
worstAirline.collect()
```


Living in Chicago, IL, what are the farthest 10 destinations that you could fly to? (Note that our dataset contains only US domestic flights.)

**Solution**:

```scala
val chicagoFarthest = flightRdd.filter(f => f.OriginCityName == "Chicago, IL")
.map(f => (f.DestCityName, f.Distance))
.distinct()
.sortBy(_._2, false)
.take(10)
```


Suppose you're in New York, NY and are contemplating direct flights to San Francisco, CA. In terms of arrival delay, which airline has the best record on that route?

**Solution**:

```scala
val nyToSF = flightRdd.filter(f => (f.OriginCityName == "New York, NY") && (f.DestCityName == "San Francisco, CA") && (f.ArrDelay > 0))
.map(f => (f.Carrier, f.ArrDelay))
.reduceByKey(_ + _)
.sortBy(_._2)
.take(1)
```


Suppose you live in San Jose, CA, and there don't seem to be many direct flights taking you to Boston, MA. Of all the 1-stop flights, which would be the best option in terms of average arrival delay? (It's OK to assume that every pair of flights from San Jose to X and from X to Boston is an option that you could use.)

> **NOTE**: To answer this question, you will probably need a cartesian product of the dataset with itself. Beside the fact that it's a fairly expensive operation, we haven't learned about multi-RDD operations yet. Still, you can explore the `join` RDD method, which applies to pair (key-value) RDDs, discussed later in our workshop.

**Solution**:

```scala
val flightsByDst = flightRdd.filter(f => f.OriginCityName == "San Jose, CA")
.map(f => (f.DestCityName, f))

val flightsByOrg = flightRdd.filter(f => f.DestCityName == "Boston, MA")
.map(f  => (f.OriginCityName, f))

def addDelays(f1:Flight, f2:Flight) = {
    var total = 0.0
    total += f1.ArrDelay
    total += f2.ArrDelay
    total
}
    
flightsByDst.join(flightsByOrg)
            .map{ case (city, (f1, f2)) => (city, addDelays(f1, f2)) }
            .combineByKey(d => (d, 1),
                          (s: (Double, Int), d: Double) => (s._1 + d, s._2 + 1),
                          (s1:  (Double, Int), s2:  (Double, Int)) => (s1._1 + s2._1, s1._2 + s2._2))
            .map { case (city, s) => (city, s._1/s._2) }
            .sortBy(_._2)
            .take(1)    
```

___

### Discussion

Suppose you had to calculate multiple aggregated values from the `flights` RDD -- e.g., the average arrival delay, the average departure delay, and the average flight duration for flights from Boston. How would you express it using SQL, if `flights` was a table in a relational database? How would you express it using transformations and actions on RDDs? Which is easier to develop and maintain?



