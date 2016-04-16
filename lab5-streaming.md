### Lab 5: Social Panic Analysis

In this lab, you will use Spark Streaming to analyze Twitter statuses for civil unrest and map them by the place they are coming from. This lab is based on Will Farmer's work, ["Twitter Civil Unrest Analysis with Apache Spark"](http://will-farmer.com/twitter-civil-unrest-analysis-with-apache-spark.html). It is a simplified version that doesn't have as many external dependencies.

> **NOTE**: If you are running this lab on your system (and not the instructor-provided VirtualBox appliance), you will need to install a couple of Python modules in case you don't have them already. Run the following commands from a terminal window:

```
sudo easy_install requests
sudo easy_install requests_oauthlib
```

___

#### Task 1: Creating a Twitter Application and Obtaining Credentials

Making requests to the [Twitter Streaming API](https://dev.twitter.com/streaming/overview) requires credentials. You will need a Twitter account, and you will need to create a Twitter application and connect it to your account. That's all a lot simpler than it sounds!

First, navigate to the [Twitter Application Management](https://apps.twitter.com) page. Sign in if necessary. If you do not have a Twitter account, this is the opportunity to create one.

Next, create a new app. You will be prompted for a name, a description, and a website. Fill in anything you want (the name must be unique, though), accept the developer agreement, and continue.

Switch to the **Keys and Access Tokens** tab on your new application's page. Copy the **Consumer Key** and **Consumer Secret** to a separate text file (in this order). Next, click **Create my access token** to authorize the application to access your own account. Copy the **Access Token** and **Access Token Secret** to the same text file (again, in this order). These four credentials are necessary for making requests to the Twitter Streaming API.

___

#### Task 2: Inspecting the Analysis Program

Open the `analysis.py` file from the `~/data` folder in a text editor. This is a Spark Streaming application that connects to the Twitter Streaming API and produces a stream of (up to 50) tweets from England every 60 seconds. These tweets are then analyzed for suspicious words like "riot" and "http", and grouped by the location they are coming from.

Inspect the source code for the application -- make sure you understand what the various functions do, and how data flows through the application. Most importantly, here is the key analysis piece:

```python
stream.map(lambda line: ast.literal_eval(line))              \
                .filter(filter_posts)                        \
                .map(lambda data: (data[1]['name'], 1))      \
                .reduceByKey(lambda a, b: a + b)             \
                .pprint()
```

To make this program work with your credentials, insert the four values you copied in the previous task in the appropriate locations in the source code:

```python
auth = requests_oauthlib.OAuth1('API KEY', 'API SECRET',
                                'ACCESS TOKEN', 'ACCESS TOKEN SECRET')
```

___

#### Task 3: Looking for Civil Unrest

You're now ready to run the program and look for civil unrest! From a terminal window, navigate to the Spark installation directory (`~/spark` on the VirtualBox appliance) and run:

```
bin/spark-submit ~/data/analysis.py
```

You should see the obtained statistics printed every 60 seconds. If you aren't getting enough results, modify the keywords the program is looking for, or modify the bounding box to a larger area.

If anything goes wrong, you should see the Twitter HTTP response details amidst the Spark log stream. For example:

```
https://stream.twitter.com/1.1/statuses/filter.json?language=en&locations=-0.489,51.28,0.236,51.686 <Response [420]>
Exceeded connection limit for user
```

By the way, while we're at it, it's a good idea to learn how to configure the Spark driver's default log level. Navigate to the `~/spark/conf` directory in a terminal window, and inspect the `log4j.properties.template` file. Copy it to a file called `log4j.properties` (this is the one Spark actually reads), and in a text editor modify the following line to read "WARN" instead of "INFO":

```
log4j.rootCategory=INFO, console
```

Subsequent launches of `pyspark`, `spark-submit`, etc. will use the new log configuration, and print out only messages that have log level WARN or higher.

___

#### Discussion

Spark Streaming is not a real-time data processing engine -- it still relies on micro-batches of elements, grouped into RDDs. Is this a serious limitation for our scenario? What are some scenarios in which it can be a serious limitation?

Bonus reading: the [Apache Flink](https://flink.apache.org) project is an alternative data processing framework that is real-time-first, batch-second. It can be a better fit in some scenarios that require real-time processing with no batching at all.
