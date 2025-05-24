import os
import sys
import time
import json
import threading
from collections import deque, Counter

import requests
from requests_oauthlib import OAuth1Session

from pyspark import SparkConf, SparkContext
from pyspark.streaming import StreamingContext

# --- Configuration ---
# IMPORTANT: Fill in your Twitter API credentials below
# You can get these by creating an app at https://developer.twitter.com/
TWITTER_API_KEY = "YOUR_API_KEY"  # Also known as Consumer Key
TWITTER_API_SECRET_KEY = "YOUR_API_SECRET_KEY"  # Also known as Consumer Secret
TWITTER_ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
TWITTER_ACCESS_TOKEN_SECRET = "YOUR_ACCESS_TOKEN_SECRET"

# Check if credentials are set
CREDENTIALS_CONFIGURED = not any(val.startswith("YOUR_") for val in [
    TWITTER_API_KEY, TWITTER_API_SECRET_KEY, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET
])

if not CREDENTIALS_CONFIGURED:
    print("ERROR: Twitter API credentials are not configured in the script.")
    print("Please fill in TWITTER_API_KEY, TWITTER_API_SECRET_KEY, TWITTER_ACCESS_TOKEN, and TWITTER_ACCESS_TOKEN_SECRET.")
    print("The script will not attempt to connect to Twitter without these credentials.")
    # For a lab environment, we might want to allow Spark to set up,
    # so we don't sys.exit(1) here but the fetcher thread won't run.

# Streaming settings
BATCH_INTERVAL_SECONDS = 10  # Process data every 10 seconds
STREAMING_DURATION_SECONDS = 300  # How long to run the streaming job (5 minutes)
QUEUE_SIZE_LIMIT = 1000 # Max tweets in memory queue (for fetched tweet strings)

# Filtering criteria
KEYWORDS_TO_TRACK = ["riot", "protest", "demonstration", "unrest", "march"] # Example keywords
# Approx bounding box for England: [SW_lon, SW_lat, NE_lon, NE_lat]
LOCATION_BOUNDING_BOX_ENGLAND = "-5.7,49.9,1.7,55.8" 

# Global flag to signal threads to stop
stop_event = threading.Event()

class TweetFetcher(threading.Thread):
    def __init__(self, output_queue):
        super().__init__()
        self.output_queue = output_queue # This is a simple Python deque for JSON strings
        self.name = "TweetFetcherThread"
        self.daemon = True 

        if not CREDENTIALS_CONFIGURED:
            print(f"{self.name}: Twitter API credentials not configured. Fetcher will not start.")
            self.auth = None
            return

        self.auth = OAuth1Session(TWITTER_API_KEY,
                                  client_secret=TWITTER_API_SECRET_KEY,
                                  resource_owner_key=TWITTER_ACCESS_TOKEN,
                                  resource_owner_secret=TWITTER_ACCESS_TOKEN_SECRET)

    def run(self):
        if not self.auth:
            print(f"{self.name}: Auth not initialized. Exiting.")
            return

        print(f"{self.name}: Starting to fetch tweets (Keywords: {KEYWORDS_TO_TRACK}, Location: England)...")
        stream_url = 'https://stream.twitter.com/1.1/statuses/filter.json'
        params = {
            'track': ",".join(KEYWORDS_TO_TRACK),
            'locations': LOCATION_BOUNDING_BOX_ENGLAND
        }
        
        try:
            resp = self.auth.post(stream_url, data=params, stream=True, timeout=(10, 60)) # (connect_timeout, read_timeout)
            resp.raise_for_status()

            print(f"{self.name}: Connected to Twitter stream. Waiting for tweets...")
            for line in resp.iter_lines():
                if stop_event.is_set():
                    print(f"{self.name}: Stop event received, breaking from stream.")
                    break
                if line:
                    try:
                        tweet_json_str = line.decode('utf-8')
                        if len(self.output_queue) < QUEUE_SIZE_LIMIT:
                            self.output_queue.append(tweet_json_str)
                        else:
                            # Log dropped tweet, consider sampling if queue often full
                            pass # print(f"{self.name}: Output queue full. Tweet dropped.")
                    except Exception as e:
                        # print(f"{self.name}: Error processing line: {e}") # Can be noisy
                        pass 
                time.sleep(0.01) # Small sleep to prevent tight loop on errors/empty lines

        except requests.exceptions.RequestException as e:
            print(f"{self.name}: RequestException: {e}")
        except Exception as e:
            print(f"{self.name}: An unexpected error occurred: {e}")
        finally:
            print(f"{self.name}: Stream closed or error. Thread finishing.")
            if 'resp' in locals() and resp:
                resp.close()

def process_batch_rdd(time, rdd): # `time` is the batch time, rdd is the RDD for this batch
    if rdd.isEmpty():
        # print(f"Batch at {time}: RDD is empty.")
        return

    print(f"\n--- Processing Batch at {time} --- ({rdd.count()} raw items received)")

    def extract_place_from_json_string(tweet_str):
        try:
            tweet = json.loads(tweet_str)
            if 'user' not in tweet or 'text' not in tweet: # Basic check for tweet structure
                return []

            text = tweet.get('text', '').lower()
            # Stream 'track' can be broad; ensure keywords are present.
            if not any(keyword in text for keyword in KEYWORDS_TO_TRACK):
                return []

            if tweet.get('place'):
                place_name = tweet['place'].get('full_name') or tweet['place'].get('name')
                # Additional filter: check if the tweet's location is within England (if place.country_code is 'GB')
                # For simplicity, this example relies on the stream's location filter.
                if place_name and tweet['place'].get('country_code') == 'GB':
                     # Or more specific check if bounding box is available for the place
                    return [place_name.strip()]
            return []
        except json.JSONDecodeError:
            return [] # Malformed JSON
        except Exception: # Other errors during parsing
            return []

    place_counts = rdd.flatMap(extract_place_from_json_string) \
                      .map(lambda place: (place, 1)) \
                      .reduceByKey(lambda a, b: a + b) \
                      .sortBy(lambda pair: pair[1], ascending=False) \
                      .collect() # Collect to driver for printing
    
    if place_counts:
        print(f"Top places in England for this batch (Keywords: {KEYWORDS_TO_TRACK}):")
        for place, count in place_counts[:10]: # Print top 10
            print(f"- {place}: {count}")
    else:
        print("No relevant places found in England for this batch.")


def run_spark_streaming():
    if not CREDENTIALS_CONFIGURED:
        print("Spark Streaming will not run live data due to missing Twitter credentials.")
        print("You can still see the Spark setup, but no tweets will be fetched or processed.")
        # We allow the script to proceed to show Spark setup, but fetcher won't start.

    spark_conf = SparkConf().setAppName("TwitterStreamAnalysis").setMaster("local[*]")
    sc = SparkContext(conf=spark_conf)
    ssc = StreamingContext(sc, BATCH_INTERVAL_SECONDS)

    # This is the Python deque that will hold tweet JSON strings from the TweetFetcher thread
    live_tweet_queue = deque(maxlen=QUEUE_SIZE_LIMIT)
    
    fetcher_thread = None
    if CREDENTIALS_CONFIGURED:
        fetcher_thread = TweetFetcher(live_tweet_queue)
        fetcher_thread.start()
        time.sleep(2) # Give fetcher a moment to connect
        if not fetcher_thread.is_alive() and not stop_event.is_set():
             print("WARN: Tweet fetcher thread started but may have exited prematurely. Check logs and credentials.")
    else:
        print("TweetFetcher thread not started due to missing credentials.")

    # Create a DStream from the Python deque. Spark will periodically check this deque for new RDDs.
    # We need to wrap items from live_tweet_queue into RDDs for queueStream.
    # The queueStream expects a queue of RDDs.
    
    # This is the Python list that Spark's queueStream will monitor. We append RDDs to this list.
    python_rdd_list_for_spark_queue = deque() 
    tweet_dstream = ssc.queueStream(python_rdd_list_for_spark_queue, oneAtATime=False)

    # Process the DStream
    tweet_dstream.foreachRDD(process_batch_rdd)
    
    ssc.start()
    print(f"Spark StreamingContext started. Monitoring for {STREAMING_DURATION_SECONDS} seconds.")
    
    start_time = time.time()
    try:
        while (time.time() - start_time) < STREAMING_DURATION_SECONDS and not stop_event.is_set():
            if CREDENTIALS_CONFIGURED and fetcher_thread and not fetcher_thread.is_alive() and not stop_event.is_set():
                print("ERROR: TweetFetcher thread died unexpectedly. Stopping stream.")
                stop_event.set()
                break

            # Take all tweets currently in live_tweet_queue (from fetcher) and make one RDD
            current_batch_strings = []
            while live_tweet_queue: # Drain our intermediate queue
                try:
                    current_batch_strings.append(live_tweet_queue.popleft())
                except IndexError:
                    break
            
            if current_batch_strings:
                # Create an RDD from the collected tweet strings for this interval
                batch_rdd = sc.parallelize(current_batch_strings)
                python_rdd_list_for_spark_queue.append(batch_rdd) # Add RDD to Spark's monitored queue
                # print(f"Added batch of {len(current_batch_strings)} tweets to Spark's DStream queue at {time.strftime('%H:%M:%S')}")
            
            # Wait for a short duration before checking live_tweet_queue again.
            # This loop's frequency should be aligned with how often you want to create RDDs.
            # For example, sleep for 1 second. Spark will process based on BATCH_INTERVAL_SECONDS.
            time.sleep(1) 

        print("Streaming duration reached or stop signal received.")

    except KeyboardInterrupt:
        print("KeyboardInterrupt received. Shutting down...")
    except Exception as e:
        print(f"An error occurred during streaming loop: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        stop_event.set() # Signal all threads/loops to stop

        if ssc:
            print("Stopping Spark StreamingContext...")
            try:
                # stopGracefully=True allows existing batches to finish
                ssc.stop(stopSparkContext=True, stopGracefully=True)
                print("Spark StreamingContext stopped.")
            except Exception as e:
                print(f"Error stopping StreamingContext: {e}", file=sys.stderr)
        
        if fetcher_thread and fetcher_thread.is_alive():
            print("Waiting for TweetFetcher thread to join...")
            fetcher_thread.join(timeout=5)
            if fetcher_thread.is_alive():
                print("TweetFetcher thread did not join in time.")
        
        print("Shutdown complete.")

if __name__ == "__main__":
    print("Starting Twitter Stream Analysis (Lab 5).")
    print(f"Ensure 'requests' and 'requests-oauthlib' are installed (`pip install requests requests-oauthlib`).")
    
    if not os.environ.get("SPARK_HOME"):
        print("WARNING: SPARK_HOME environment variable is not set.")

    run_spark_streaming()
    print("Twitter Stream Analysis (Lab 5) finished.")
