### Lab 3: Analyzing Startup Companies

In this lab, you will analyze a real-world dataset -- information about startup companies. The source of this dataset is [jSONAR](http://jsonstudio.com/resources/).

___

#### Task 1: Inspecting the Data

This time, the data is provided as a JSON document, one entry per line. You can find it in `~/data/companies.json`. Take a look at the first entry by using the following command:

```
head -n 1 ~/data/companies.json
```

As you can see, the schema is fairly complicated -- it has a bunch of fields, nested objects, arrays, and so on. It describes the company's products, key people, acquisition data, and more. We are going to use Spark SQL to infer the schema of this JSON document, and then issue queries using a natural SQL syntax.

___

#### Task 2: Parsing the Data

Open a PySpark shell (by running `bin/pyspark` from the Spark installation directory in a terminal window). Note that you have access to a pre-initialized `SQLContext` object named `sqlContext`.

Create a `DataFrame` from the JSON file so that its schema is automatically inferred, print out the resulting schema, and register it as a temporary table called "companies".

**Solution**:

```python
companies = sqlContext.read.json("file:///home/vagrant/data/companies.json")
companies.printSchema()
companies.registerTempTable("companies")
```

___

#### Task 3: Querying the Data

First, let's talk about the money; figure out what the average acquisition price was.

**Solution**:

```python
sqlContext.sql("select avg(acquisition.price_amount) from companies").first()
```

Not too shabby. Let's get some additional detail -- print the average acquisition price grouped by number of years the company was active.

**Solution**:

```python
sqlContext.sql(
    """select   acquisition.acquired_year-founded_year as years_active,
                avg(acquisition.price_amount) as acq_price
       from     companies
       where    acquisition.price_amount is not null
       group by acquisition.acquired_year-founded_year
       order by acq_price desc""").collect()
```

Finally, let's try to figure out the relationship between the company's total funding and acquisition price. In order to do that, you'll need a UDF (user-defined function) that, given a company, returns the sum of all its funding rounds. First, build that function and register it with the name "total_funding".

**Solution**:

```python
 sqlContext.registerFunction("total_funding", lambda investments: sum(
      [inv.funding_round.raised_amount or 0 for inv in investments]
    ), IntegerType())
```

Test your function by retrieving the total funding for a few companies, such as Facebook, Paypal, and Alibaba. Now, find the average ratio between the acquisition price and the total funding (which, in a simplistic way, represents return on investment).

**Solution**:

```python
sqlContext.sql(
    """select avg(acquisition.price_amount/total_funding(investments))
       from   companies
       where  acquisition.price_amount is not null
       and    total_funding(investments) != 0""").collect()
```

___

#### Discussion

See discussion for the [next lab](lab4-propprices.md).
