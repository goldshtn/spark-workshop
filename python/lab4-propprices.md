### Lab 4: Analyzing UK Property Prices

In this lab, you will work with another real-world dataset that contains residential property sales across the UK, as reported to the Land Registry. You can download this dataset and many others from [data.gov.uk](https://data.gov.uk/dataset/land-registry-monthly-price-paid-data).

___

#### Task 1: Inspecting the Data

As always, we begin by inspecting the data, which is in the `~/data/prop-prices.csv` file. Run the following command to take a look at some of the entries:

```
head ~/data/prop-prices.csv
```

Note that this time, the CSV file does not have headers. To determine which fields are available, consult the [guidance page](https://www.gov.uk/guidance/about-the-price-paid-data).

___

#### Task 2: Importing the Data

In a previous lab, we used the Python `csv` module to parse CSV files. However, because we're working with structured data, the Spark SQL framework can be easier to use and provide better performance. We are going to use the `spark.read.csv` to create a `DataFrame` from an RDD of CSV lines.

> **NOTE**: The `pyspark_csv.py` file, a third-party package for loading csv files for Spark 1.x, is in the `~/externals` directory on the appliance. You can also [download it yourself](https://github.com/seahboonsiew/pyspark-csv) and place it in some directory.
> 
> This module also depends on the `dateutils` module, which typically doesn't ship with Python. It is already installed in the appliance. To install it on your own machine, run the following from a terminal window:

```
sudo easy_install dateutils
```

To import `pyspark_csv` (if needed in Spark 1.x, for Spark 2.x, skip this step), you'll need the following snippet of code that adds its path to the module search path, and adds it to the Spark executors so they can find it as well:

```python
import sys
sys.path.append('/home/ubuntu/externals')   # replace as necessary
import pyspark_csv
sc.addFile('/home/ubuntu/externals/pyspark_csv.py')    # ditto
```

Next, load the `prop-prices.csv` file as an RDD, and use the `csvToDataFrame` function from the `pyspark_csv` module to create a `DataFrame` and register it as a temporary table so that you can run SQL queries:

```python
columns = ['id', 'price', 'date', 'zip', 'type', 'new', 'duration', 'PAON',
           'SAON', 'street', 'locality', 'town', 'district', 'county', 'ppd',
           'status']

df = spark.read.option("inferSchema", "true").option("header", "false").csv("file:///home/ubuntu/data/prop-prices.csv")
selectExpr = map(lambda (i, c): "_c%d as %s" % (i, c), enumerate(columns))
df = df.selectExpr(selectExpr)
df.registerTempTable("properties")
df.persist()
```

___

#### Task 3: Analyzing Property Price Trends

First, let's do some basic analysis on the data. Find how many records we have per year, and print them out sorted by year.

**Solution**:

```python
spark.sql("""select   year(date), count(*)
                  from     properties
                  group by year(date)
                  order by year(date)""").collect()
```

All right, so everyone knows that properties in London are expensive. Find the average property price by county, and print the top 10 most expensive counties.

**Solution**:

```python
spark.sql("""select   county, avg(price)
                  from     properties
                  group by county
                  order by avg(price) desc
                  limit    10""").collect()
```

Is there any trend for property sales during the year? Find the average property price in Greater London month over month in 2015 and 2016, and print it out by month.

**Solution**:

```python
spark.sql("""select   year(date) as yr, month(date) as mth, avg(price)
                  from     properties
                  where    county='GREATER LONDON'
                  and      year(date) >= 2015
                  group by year(date), month(date)
                  order by year(date), month(date)""").collect()
```

Bonus: use the Python `matplotlib` module to plot the property price changes month-over-month across the entire dataset.

> The `matplotlib` module is installed in the instructor-provided appliance. However, there is no X environment, so you will not be able to view the actual plot. For your own system, follow the [installation instructions](http://matplotlib.org/users/installing.html).

**Solution**:

```python
monthPrices = spark.sql("""select   year(date), month(date), avg(price)
                                from     properties
                                group by year(date), month(date)
                                order by year(date), month(date)""").collect()
import matplotlib.pyplot as plt
values = map(lambda row: row._c2, monthPrices)
plt.rcdefaults()
plt.scatter(xrange(0,len(values)), values)
plt.show()
```

___

#### Discussion

Now that you have experience in working with Spark SQL and `DataFrames`, what are the advantages and disadvantages of using it compared to the core RDD functionality (such as `map`, `filter`, `reduceByKey`, and so on)? Consider which approach produces more maintainable code, offers more opportunities for optimization, makes it easier to solve certain problems, and so on.
