### Lab 4: Analyzing UK Property Prices

In this lab, you will work with another real-world dataset that contains residential property sales across the UK, as reported to the Land Registry. You can download this dataset and many others from [data.gov.uk](https://data.gov.uk/dataset/land-registry-monthly-price-paid-data).

___

#### Task 1: Inspecting the Data

As always, we begin by inspecting the data, which is in the `/home/data/prop-prices.csv` file. Run the following command to take a look at some of the entries:

```
head /home/data/prop-prices.csv
```

Note that this time, the CSV file does not have headers. To determine which fields are available, consult the [guidance page](https://www.gov.uk/guidance/about-the-price-paid-data).

___

#### Task 2: Importing the Data

We are going to use the `com.databricks.spark.csv` library to create a `DataFrame` from CSV file.

First we need to restart Scala interpreter of Zeppelin:
  Interpreter -> spark box(first one) -> restart button
Then we need to import `com.databricks.spark.csv` as we did in Lab 2.

```scala
%dep
z.reset()
z.addRepo("Spark Packages Repo").url("http://dl.bintray.com/spark-packages/maven")
z.load("com.databricks:spark-csv_2.11:1.4.0")
```

After we will define a schema for our data.
And load the `prop-prices.csv` file as a `DataFrame` and register it as a temporary table so that you can run SQL queries:


```scala
import org.apache.spark.sql.types._
val custSchema = StructType(Array(
    StructField("id",StringType,true), 
    StructField("price",IntegerType,true), 
    StructField("date",TimestampType,true), 
    StructField("zip",StringType,true),
    StructField("type",StringType,true), 
    StructField("new",StringType,true), 
    StructField("duration",StringType,true), 
    StructField("PAON",StringType,true), 
    StructField("SAON",StringType,true), 
    StructField("street",StringType,true), 
    StructField("locality",StringType,true),
    StructField("town",StringType,true),
    StructField("district",StringType,true), 
    StructField("county",StringType,true), 
    StructField("ppd",StringType,true), 
    StructField("status",StringType,true)))

val df = sqlContext.read
    .format("com.databricks.spark.csv")
    .schema(custSchema)
    .load("file:///home/data/prop-prices.csv")

df.registerTempTable("properties")
df.persist()
```

___

#### Task 3: Analyzing Property Price Trends

First, let's do some basic analysis on the data. Find how many records we have per year, and print them out sorted by year.

**Solution**:

```Scala
sqlContext.sql("""select   year(date), count(*)
                  from     properties
                  group by year(date)
                  order by year(date)""").collect()
```

All right, so everyone knows that properties in London are expensive. Find the average property price by county, and print the top 10 most expensive counties.

**Solution**:

```Scala
sqlContext.sql("""select   county, avg(price)
                  from     properties
                  group by county
                  order by avg(price) desc
                  limit    10""").collect()
```

Is there any trend for property sales during the year? Find the average property price in Greater London month over month in 2015 and 2016, and print it out by month.

**Solution**:

```Scala
sqlContext.sql("""select   year(date) as yr, month(date) as mth, avg(price)
                  from     properties
                  where    county='GREATER LONDON'
                  and      year(date) >= 2015
                  group by year(date), month(date)
                  order by year(date), month(date)""").collect()
```


????????????????????????????????????????????????????????????????????????????????
????????????????????????????????????????????????????????????????????????????????
Bonus: use the Python `matplotlib` module to plot the property price changes month-over-month across the entire dataset.

> The `matplotlib` module is installed in the instructor-provided VirtualBox appliance. For your own system, follow the [installation instructions](http://matplotlib.org/users/installing.html).

**Solution**:

```Scala
monthPrices = sqlContext.sql("""select   year(date), month(date), avg(price)
                                from     properties
                                group by year(date), month(date)
                                order by year(date), month(date)""").collect()
import matplotlib
values = map(lambda row: row._c2)
plt.rcdefaults()
plt.scatter(xrange(0,len(values[0])), values[1])
plt.show()
```
????????????????????????????????????????????????????????????????????????????????
????????????????????????????????????????????????????????????????????????????????
___

#### Discussion

Now that you have experience in working with Spark SQL and `DataFrames`, what are the advantages and disadvantages of using it compared to the core RDD functionality (such as `map`, `filter`, `reduceByKey`, and so on)? Consider which approach produces more maintainable code, offers more opportunities for optimization, makes it easier to solve certain problems, and so on.
