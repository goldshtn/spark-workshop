import csv
from pyspark import SparkConf, SparkContext

# Use io.StringIO for Python 3 compatibility, fallback to StringIO for Python 2
try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

def parse_line(line, fieldnames):
    """Parses a CSV line using the given fieldnames."""
    si = StringIO(line)
    return next(csv.DictReader(si, fieldnames=fieldnames))

def get_float_or_zero(value_str):
    """Converts a string to float, returns 0.0 if empty or invalid."""
    if value_str and value_str.strip():
        try:
            return float(value_str)
        except ValueError:
            return 0.0
    return 0.0

def run(data_path="~/data/airline-delays.csv"):
    conf = SparkConf().setAppName("AirlineDelayAnalysis").setMaster("local[*]")
    sc = SparkContext(conf=conf)

    results = {}

    try:
        # Construct the full file path, handling the file:// prefix if data_path doesn't have it
        # Spark's textFile can handle local paths directly, but explicit file:// is clearer for local files.
        # However, if the user provides file:///..., we don't want file://file:///...
        if not data_path.startswith("file://") and not data_path.startswith("/") : # a relative path like "data/file.csv" or "~/data/..."
             # Assuming ~/data for lab consistency; spark-submit usually handles ~ correctly.
             # For robustness, absolute paths are better.
             pass # Keep it as is, Spark will try to resolve it.
        
        # For local files, sc.textFile can take a path directly.
        # If on a cluster, it would be hdfs:// or s3:// etc.
        # The lab uses "file:////home/ubuntu/data/airline-delays.csv"
        # We will assume data_path is correctly specified for the environment.
        # For this exercise, we will assume the file is accessible by the Spark driver/workers.
        
        print(f"Attempting to load data from: {data_path}")
        rdd = sc.textFile(data_path)
        
        header_line = rdd.first()
        field_names = [field.strip('"') for field in header_line.split(',') if field.strip('"')]
        
        flights = rdd.filter(lambda line: line != header_line) \
                     .map(lambda line: parse_line(line, field_names))
        
        flights.persist()
        print(f"Successfully loaded and parsed {flights.count()} flight records.")

        # Query 1: Airline with most flights from Boston
        boston_flights_by_carrier = flights.filter(lambda f: f.get('OriginCityName') == "Boston, MA") \
                                           .map(lambda f: (f.get('Carrier', 'UnknownCarrier'), 1)) \
                                           .reduceByKey(lambda a, b: a + b) \
                                           .sortBy(lambda x: x[1], ascending=False) \
                                           .first()
        results["most_flights_from_boston"] = boston_flights_by_carrier
        print(f"Q1 - Most flights from Boston: {boston_flights_by_carrier}")

        # Query 2: Overall worst average delay by airline
        # Ensure ArrDelay is not empty and convert to float
        worst_avg_delay = flights.filter(lambda f: f.get('ArrDelay') and f.get('ArrDelay').strip()) \
                               .map(lambda f: (f.get('Carrier', 'UnknownCarrier'), get_float_or_zero(f.get('ArrDelay')))) \
                               .combineByKey(
                                   lambda delay: (delay, 1),
                                   lambda acc, delay: (acc[0] + delay, acc[1] + 1),
                                   lambda acc1, acc2: (acc1[0] + acc2[0], acc1[1] + acc2[1])
                               ) \
                               .mapValues(lambda x: x[0] / x[1] if x[1] != 0 else float('inf')) \
                               .sortBy(lambda x: x[1], ascending=False) \
                               .first() # Gets the one with highest average delay
        results["worst_avg_delay"] = worst_avg_delay
        print(f"Q2 - Worst average delay: {worst_avg_delay}")

        # Query 3: Farthest 10 destinations from Chicago, IL
        farthest_from_chicago = flights.filter(lambda f: f.get('OriginCityName') == "Chicago, IL" and f.get('Distance') and f.get('Distance').strip()) \
                                       .map(lambda f: (f.get('DestCityName', 'UnknownDest'), get_float_or_zero(f.get('Distance')))) \
                                       .distinct() \
                                       .sortBy(lambda x: x[1], ascending=False) \
                                       .take(10)
        results["farthest_from_chicago"] = farthest_from_chicago
        print(f"Q3 - Farthest 10 from Chicago: {farthest_from_chicago}")

        # Query 4: Best airline (min total delay) for New York, NY to San Francisco, CA
        # The lab solution sums delays, which might not be "best record" if it means lowest average.
        # Let's stick to the lab's interpretation (sum of delays).
        best_airline_ny_sf = flights.filter(lambda f: f.get('OriginCityName') == "New York, NY" and
                                                          f.get('DestCityName') == "San Francisco, CA" and
                                                          f.get('ArrDelay') and f.get('ArrDelay').strip()) \
                                    .map(lambda f: (f.get('Carrier', 'UnknownCarrier'), get_float_or_zero(f.get('ArrDelay')))) \
                                    .reduceByKey(lambda a, b: a + b) \
                                    .sortBy(lambda x: x[1], ascending=True) \
                                    .first()
        results["best_airline_ny_sf"] = best_airline_ny_sf
        print(f"Q4 - Best airline NY to SF (by total delay): {best_airline_ny_sf}")

        # Query 5: Best 1-stop flight (San Jose -> X -> Boston) by average arrival delay
        sjc_flights = flights.filter(lambda f: f.get('OriginCityName') == 'San Jose, CA' and f.get('DestCityName')) \
                             .map(lambda f: (f['DestCityName'], f)) # Key by destination (intermediate stop)

        bos_flights = flights.filter(lambda f: f.get('DestCityName') == 'Boston, MA' and f.get('OriginCityName')) \
                             .map(lambda f: (f['OriginCityName'], f)) # Key by origin (intermediate stop)

        def calculate_total_delay(flight1, flight2):
            delay1 = get_float_or_zero(flight1.get('ArrDelay'))
            delay2 = get_float_or_zero(flight2.get('ArrDelay'))
            # Consider DepDelay as well for the connection? Lab implies only ArrDelay.
            # For simplicity, sticking to ArrDelay as per lab structure.
            return delay1 + delay2

        # Join on the intermediate city
        one_stop_flights = sjc_flights.join(bos_flights) \
            .map(lambda joined: (
                joined[0], # Intermediate city
                (joined[1][0], joined[1][1]) # (flight_sjc_to_X, flight_X_to_bos)
            ))

        best_one_stop = one_stop_flights.map(lambda x: (x[0], calculate_total_delay(x[1][0], x[1][1]))) \
            .combineByKey(
                lambda delay: (delay, 1),
                lambda acc, delay: (acc[0] + delay, acc[1] + 1),
                lambda acc1, acc2: (acc1[0] + acc2[0], acc1[1] + acc2[1])
            ) \
            .mapValues(lambda x: x[0] / x[1] if x[1] != 0 else float('inf')) \
            .sortBy(lambda x: x[1], ascending=True) \
            .first() # (intermediate_city, avg_total_delay)
            
        results["best_one_stop_sjc_bos"] = best_one_stop
        print(f"Q5 - Best 1-stop SJC to BOS (via {best_one_stop[0] if best_one_stop else 'N/A'}): {best_one_stop}")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        sc.stop()
        print("SparkContext stopped.")
    return results

if __name__ == "__main__":
    print("Starting Airline Delay Analysis Spark job.")
    # Note: The '~/data/airline-delays.csv' path is from the lab's VM setup.
    # This path might need to be changed depending on where the data is stored
    # when running this script. For example, if data.zip from the repo is extracted
    # in the repo root, the path might be "./data/airline-delays.csv".
    default_data_path = "~/data/airline-delays.csv"
    print(f"Using data path: {default_data_path}. Ensure this path is correct for your environment.")
    
    # It's generally better to pass the data_path as a command-line argument.
    # import sys
    # if len(sys.argv) > 1:
    #    data_path = sys.argv[1]
    # else:
    #    data_path = default_data_path
    
    run(default_data_path)
    print("Airline Delay Analysis Spark job finished.")
