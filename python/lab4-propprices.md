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

In a previous lab, we used the Python `csv` module to parse CSV files. However, because we're working with structured data, the Spark SQL framework can be easier to use and provide better performance. We are going to use the `pyspark_csv` third-party open source module to create a `DataFrame` from an RDD of CSV lines.

> **NOTE**: The `pyspark_csv.py` file is in the `Downloads` directory on the VirtualBox appliance. You can also [download it yourself](https://github.com/seahboonsiew/pyspark-csv) and place it in some directory.
> 
> This module also depends on the `dateutils` module, which typically doesn't ship with Python. It is already installed in the VirtualBox appliance. To install it on your own machine, run the following from a terminal window:

```
sudo easy_install dateutils
```

To import `pyspark_csv`, you'll need the following snippet of code that adds its path to the module search path, and adds it to the Spark executors so they can find it as well:

```python
import sys
sys.path.append('/home/vagrant/Downloads')   # replace as necessary
import pyspark_csv
sc.addFile('/home/vagrant/Downloads/pyspark_csv.py')    # ditto
```

Next, load the `prop-prices.csv` file as an RDD, and use the `csvToDataFrame` function from the `pyspark_csv` module to create a `DataFrame` and register it as a temporary table so that you can run SQL queries:

```python
columns = ['id', 'price', 'date', 'zip', 'type', 'new', 'duration', 'PAON',
           'SAON', 'street', 'locality', 'town', 'district', 'county', 'ppd',
           'status']

rdd = sc.textFile("file:///home/vagrant/data/prop-prices.csv")
df = pyspark_csv.csvToDataFrame(sqlContext, rdd, columns=columns)
df.registerTempTable("properties")
df.persist()
```

___

#### Task 3: Analyzing Property Price Trends

First, let's do some basic analysis on the data. Find how many records we have per year, and print them out sorted by year.

**Solution**:

```python
sqlContext.sql("""select   year(date), count(*)
                  from     properties
                  group by year(date)
                  order by year(date)""").collect()
```

All right, so everyone knows that properties in London are expensive. Find the average property price by county, and print the top 10 most expensive counties.

**Solution**:

```python
sqlContext.sql("""select   county, avg(price)
                  from     properties
                  group by county
                  order by avg(price) desc
                  limit    10""").collect()
```

Is there any trend for property sales during the year? Find the average property price in Greater London month over month in 2015 and 2016, and print it out by month.

**Solution**:

```python
sqlContext.sql("""select   year(date) as yr, month(date) as mth, avg(price)
                  from     properties
                  where    county='GREATER LONDON'
                  and      year(date) >= 2015
                  group by year(date), month(date)
                  order by year(date), month(date)""").collect()
```

Bonus: use the Python `matplotlib` module to plot the property price changes month-over-month across the entire dataset.

> The `matplotlib` module is installed in the instructor-provided VirtualBox appliance. For your own system, follow the [installation instructions](http://matplotlib.org/users/installing.html).

**Solution**:

```python
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

___

#### Discussion

Now that you have experience in working with Spark SQL and `DataFrames`, what are the advantages and disadvantages of using it compared to the core RDD functionality (such as `map`, `filter`, `reduceByKey`, and so on)? Consider which approach produces more maintainable code, offers more opportunities for optimization, makes it easier to solve certain problems, and so on.
