from pyspark import SparkContext, SparkConf

def run(data_path="~/data/*.txt"):
    # Configure Spark
    # In a real cluster, master URL would be different, e.g., spark://host:port or yarn
    # For local development and testing, "local[*]" uses all available cores.
    conf = SparkConf().setAppName("PythonWordCount").setMaster("local[*]")
    sc = SparkContext(conf=conf)

    try:
        # Read all text files from the specified path
        lines = sc.textFile(data_path)

        # Split each line into words
        # Filter out empty strings that might result from multiple spaces
        words = lines.flatMap(lambda line: filter(None, line.split()))

        # Filter out words shorter than 4 characters
        filtered_words = words.filter(lambda word: len(word) >= 4)

        # Count the occurrences of each word
        # map each word to a (word, 1) pair
        pairs = filtered_words.map(lambda word: (word.lower(), 1)) # Convert to lowercase for consistent counting

        # reduce by key to sum counts for each word
        freqs = pairs.reduceByKey(lambda a, b: a + b)

        # Sort by frequency in descending order and take the top 10
        # sortBy's second argument True means ascending, False means descending.
        # Or, as in the lab, negate the count for ascending sort to achieve descending.
        top10 = freqs.sortBy(lambda pair: pair[1], ascending=False).take(10)

        print("Top 10 most frequent words (4+ characters):")
        for (word, count) in top10:
            print("'%s': %d" % (word, count))

    finally:
        # Stop the SparkContext
        sc.stop()

if __name__ == "__main__":
    # The lab uses "/home/ubuntu/data/*.txt".
    # Make this configurable or pass as an argument if needed for broader use.
    # For now, hardcoding as per the lab's context.
    # Note: '~' expansion might not work directly with sc.textFile in all environments
    # when run via spark-submit. It's generally better to use absolute paths
    # or paths relative to where spark-submit is run.
    # However, for consistency with the lab, I'll keep it.
    # A more robust solution would take this path as a command-line argument.
    
    # For the purpose of this solution file, we'll assume data is in '~/data/'
    # If running this script, ensure the data path is correct for your environment.
    # For example, if data.zip from the repo is extracted in the repo root,
    # the path might be "./data/*.txt" when running from the repo root.
    
    # Since the worker environment might not have ~/data, and to make it runnable
    # in a generic context, let's print a message about the data path.
    print("Attempting to run WordCount.")
    print("Please ensure your data path is correctly configured if you are not using the lab environment.")
    print("The default path in this script is '~/data/*.txt'.")
    print("If this path is not accessible or does not exist, the script will fail or produce no output.")
    
    # It's better to make the path an argument for spark-submit.
    # For now, to adhere to the lab structure as much as possible:
    default_data_path = "~/data/*.txt" 
    # For testing within a CI/CD or automated environment, this path often needs to be concrete.
    # We could use a placeholder or an environment variable.
    # For now, we'll use the one from the lab, with a note.

    run(default_data_path)
    print("WordCount finished.")
