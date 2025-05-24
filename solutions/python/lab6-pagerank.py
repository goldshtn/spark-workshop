import re
import os # Added for SPARK_HOME check and path handling if needed
import sys # Added for potential command-line argument handling
from pyspark.sql import SparkSession

def parse_movie_links(line):
    """
    Parses a line from processed-movie-links.txt.
    Example line: "1: 2 3 4" (movie_id: linked_movie_id1 linked_movie_id2 ...)
    Returns a tuple (movie_id, [linked_movie_ids]) or None if malformed.
    """
    parts = line.split(':', 1) # Split only on the first colon
    if len(parts) != 2:
        # print(f"DEBUG: Malformed line (no colon or unexpected format): {line}")
        return None 
    movie_id = parts[0].strip()
    if not movie_id: # Check for empty movie_id
        # print(f"DEBUG: Malformed line (empty movie_id): {line}")
        return None
        
    linked_ids_str = parts[1].strip()
    if not linked_ids_str: # No outgoing links (e.g., "123:")
        return (movie_id, [])
    
    # Filter out empty strings that might result from multiple spaces or trailing spaces
    linked_ids = [lid.strip() for lid in linked_ids_str.split(' ') if lid.strip()]
    return (movie_id, linked_ids)

def compute_contribs(target_movie_ids_list, rank_of_source_movie):
    """
    Calculates contributions to send to linked movies.
    Args:
        target_movie_ids_list: A list of movie_ids that the source movie links to.
        rank_of_source_movie: The rank of the movie sending the contributions.
    Returns:
        A list of (target_movie_id, contribution_value) tuples.
    """
    num_links = len(target_movie_ids_list)
    if num_links == 0:
        return [] # No contributions if no outgoing links

    contribution = rank_of_source_movie / num_links
    return [(target_movie_id, contribution) for target_movie_id in target_movie_ids_list]

def run_pagerank(data_path="~/data/processed-movie-links.txt", iterations=10):
    spark = None
    try:
        spark = SparkSession.builder \
            .appName("PythonPageRankMovies") \
            .master("local[*]") \
            .getOrCreate()
        sc = spark.sparkContext

        print(f"Loading movie links data from: {data_path}")
        # Expand home directorytilde if present
        if data_path.startswith("~"):
            data_path = os.path.expanduser(data_path)

        if not os.path.exists(data_path):
            print(f"Error: Input data file not found at {data_path}. Exiting.")
            # For a lab, it might be better to create dummy data if file not found
            # to allow the script to run through its logic.
            # For now, we'll exit.
            return

        lines_rdd = sc.textFile(data_path)

        if lines_rdd.isEmpty():
            print(f"Warning: Input file at {data_path} is empty.")
            # Depending on requirements, either exit or proceed (PageRank will yield no results)
            # For now, let's allow it to proceed; all_movie_ids will be empty.


        links = lines_rdd.map(parse_movie_links).filter(lambda x: x is not None and x[0] != "").cache()
        
        # Handle case where parsing results in an empty RDD (e.g. all lines malformed or empty file)
        if links.isEmpty() and not lines_rdd.isEmpty(): # If original RDD wasn't empty but links is
            print("Error: Links RDD is empty after parsing, but input file was not empty. Check file format.")
            # This could happen if all lines are malformed according to parse_movie_links
            return
        elif links.isEmpty() and lines_rdd.isEmpty(): # Both empty, means input file was empty
             print("Input file was empty, so no links to process.")
             # Allow to continue, will result in no ranks.

        # Create a list of all unique movie IDs.
        # This includes movies that link out (x[0]) and movies that are linked to (from x[1]).
        all_movie_ids = links.flatMap(lambda x: [x[0]] + x[1]).distinct().cache()
        
        num_all_movies = all_movie_ids.count()
        if num_all_movies == 0:
            print("Error: No movie IDs found after processing the input file. Cannot run PageRank.")
            return
            
        print(f"Found {num_all_movies} unique movie IDs.")
        
        # Initialize ranks: (movie_id, 1.0) for all unique movies
        ranks = all_movie_ids.map(lambda movie_id: (movie_id, 1.0))
        
        # PageRank iterations
        for i in range(1, iterations + 1):
            # Join links with current ranks: RDD of (movie_id, ([list_of_linked_ids], current_rank))
            # Example element: ('1', (['2', '3'], 1.0))
            joined_rdd = links.join(ranks)

            # Calculate contributions: RDD of (target_movie_id, contribution_share)
            # Each element in joined_rdd is (source_id, (list_of_target_ids, rank_of_source_id))
            contributions = joined_rdd.flatMap(
                lambda x: compute_contribs(x[1][0], x[1][1]) # x[1][0] is list_of_target_ids, x[1][1] is rank
            )
            
            # Sum contributions for each movie: RDD of (movie_id, total_received_contribution_score)
            summed_contribs = contributions.reduceByKey(lambda x, y: x + y)

            # Update ranks using the PageRank formula: rank = 0.15 + 0.85 * summed_contribs
            # Use leftOuterJoin with all_movie_ids (mapped to a dummy 0 value for the join)
            # to ensure movies that received no contributions (i.e., not in summed_contribs)
            # still get their rank updated with the damping factor.
            # (movie_id, (dummy_val_from_all_movies, Optional[sum_contrib_for_this_movie_id]))
            
            # Create a base RDD of all movies with a dummy value (e.g., 0.0) to ensure all movies are included.
            base_for_join = all_movie_ids.map(lambda mid: (mid, 0.0))
            
            new_ranks = base_for_join.leftOuterJoin(summed_contribs) \
                .mapValues(lambda x: 0.15 + 0.85 * (x[1] if x[1] is not None else 0.0))
            
            ranks = new_ranks # Update ranks for the next iteration
            # You could print `ranks.take(5)` here for debugging if needed.
            print(f"Iteration {i} complete. Sample rank: {ranks.take(1)}")


        print(f"\n--- PageRank calculation complete after {iterations} iterations ---")

        # Sort movies by rank in descending order and take top 10
        top_10_movies = ranks.sortBy(lambda x: x[1], ascending=False).take(10)

        print("\nTop 10 movies by PageRank (Movie ID: Rank):")
        if not top_10_movies:
            print("No movies to rank or all ranks are zero.")
        for movie_id, rank in top_10_movies:
            print(f"{movie_id}: {rank:.4f}")
            
        # Note about GraphX (Task 3 from the lab description)
        print("\n--- Note regarding Lab Task 3 (GraphX) ---")
        print("The original lab's Task 3 involves using GraphX for PageRank, which is a Scala-specific API within Spark.")
        print("This Python script uses PySpark's RDD operations to implement PageRank.")
        print("For graph processing in Python with PySpark, one might explore GraphFrames,")
        print("which is a separate package providing DataFrame-based graph operations.")

    except Exception as e:
        print(f"An critical error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if spark:
            print("\nStopping SparkSession.")
            spark.stop()

if __name__ == "__main__":
    print("Starting PageRank analysis for movie dataset (Lab 6 - Python RDD version).")
    
    # Default path for the processed movie links file.
    # This path should be accessible by the Spark driver and workers.
    # For local mode, it's typically a path on the local filesystem.
    # In a cluster, it would be an HDFS path or similar.
    default_input_path = "~/data/processed-movie-links.txt" 
    
    # Check if SPARK_HOME is set, often useful for lab environments
    if not os.environ.get("SPARK_HOME"):
        print("WARNING: SPARK_HOME environment variable is not set. Ensure PySpark is correctly configured.")
        
    # Allow overriding the input path via command-line argument
    input_path_arg = default_input_path
    if len(sys.argv) > 1:
        input_path_arg = sys.argv[1]
        print(f"Using input path from command line: {input_path_arg}")
    else:
        print(f"Using default input path: {default_input_path}")
    
    num_iterations_arg = 10 # Default iterations
    if len(sys.argv) > 2:
        try:
            num_iterations_arg = int(sys.argv[2])
            print(f"Using number of iterations from command line: {num_iterations_arg}")
        except ValueError:
            print(f"Warning: Second argument '{sys.argv[2]}' is not a valid integer for iterations. Using default {num_iterations_arg}.")

    run_pagerank(data_path=input_path_arg, iterations=num_iterations_arg)
    print("\nPageRank analysis finished.")
