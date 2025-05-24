import os
import re
import sys # For potential command-line args
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StringType, StructType, StructField
from pyspark.ml.feature import HashingTF, IDF, RegexTokenizer, StopWordsRemover
# pyspark.ml.linalg.Vector is the type for 'features' column from IDFModel
from pyspark.ml.linalg import Vector as MLVector 
# For converting ML Vector to MLLib Vector if using MLLib's LSH or other utilities
# from pyspark.mllib.linalg import Vectors as MLLibVectors 

def clean_text_udf_func(text_content):
    """
    Cleans text by lowercasing, removing most punctuation (keeps basic sentence structure, apostrophes).
    Designed for use as a PySpark UDF.
    """
    if text_content is None:
        return ""
    text = text_content.lower()
    # Remove punctuation except for spaces, basic sentence terminators (.), and apostrophes (') within words.
    # This regex aims to preserve word contractions and simple sentence structure.
    text = re.sub(r"[^a-z0-9\s'.]", "", text) # Allow apostrophes and periods
    text = re.sub(r"(\s\.|\.\s)", ". ", text) # Normalize spaces around periods
    text = re.sub(r"\s+", " ", text).strip() # Normalize whitespace
    return text

def calculate_cosine_similarity_udf_func(candidate_vector_bc):
    """
    Returns a UDF that calculates cosine similarity between a row's vector and a broadcasted candidate vector.
    """
    def _cos_sim(essay_vector):
        if essay_vector is None or not isinstance(essay_vector, MLVector):
            return 0.0 # Or None, depending on how you want to handle missing vectors

        # candidate_vector_bc.value is the actual MLVector
        cand_vec = candidate_vector_bc.value
        
        norm_essay = essay_vector.norm(2)
        norm_cand = cand_vec.norm(2)

        if norm_essay == 0.0 or norm_cand == 0.0:
            return 0.0 # Avoid division by zero; similarity is undefined or zero

        dot_product = essay_vector.dot(cand_vec)
        return float(dot_product / (norm_essay * norm_cand))
    return F.udf(_cos_sim, StringType()) # Return type is float, but UDFs often return string for flexibility or use DoubleType()

from pyspark.sql.types import DoubleType # For UDF return type

def run_plagiarism_detection(
    essays_path_glob="~/data/essays/*.txt", 
    candidate_file_path="~/data/essays/candidate.txt", 
    num_features_tf=10000,
    top_n_similar=5
):
    spark = None
    try:
        spark = SparkSession.builder \
            .appName("PlagiarismDetectionLab7") \
            .master("local[*]") \
            .config("spark.sql.execution.arrow.pyspark.enabled", "true") # Recommended for UDF performance
            .config("spark.sql.codegen.wholeStage", "false") # Can help with complex UDFs if issues arise
            .getOrCreate()
        sc = spark.sparkContext

        # Expand paths
        essays_path_glob_expanded = os.path.expanduser(essays_path_glob)
        candidate_file_path_expanded = os.path.expanduser(candidate_file_path)

        print(f"Attempting to load essays from: {essays_path_glob_expanded}")
        print(f"Attempting to load candidate file from: {candidate_file_path_expanded}")

        if not os.path.exists(candidate_file_path_expanded):
            print(f"Error: Candidate file not found at '{candidate_file_path_expanded}'. Exiting.")
            return

        # Load essays and candidate file. Using wholeTextFiles to get (filepath, content).
        try:
            # Check if glob pattern resolves to any files for essays
            # Note: Spark's wholeTextFiles might error on an empty glob or non-existent dir.
            # A more robust check might involve Python's glob module first if Spark has issues.
            essays_rdd = sc.wholeTextFiles(essays_path_glob_expanded)
            if essays_rdd.isEmpty():
                print(f"Error: No essay files found matching glob '{essays_path_glob_expanded}' or directory is empty. Exiting.")
                return
        except Exception as e: # Catch path errors from Spark
             print(f"Spark Error loading essays from '{essays_path_glob_expanded}': {e}. Check path and permissions.")
             return
        
        candidate_rdd = sc.wholeTextFiles(candidate_file_path_expanded)

        # Define schema for DataFrame conversion
        docs_schema = StructType([
            StructField("filepath", StringType(), False),
            StructField("text_content", StringType(), False)
        ])

        essays_df = essays_rdd.toDF(docs_schema)
        candidate_df = candidate_rdd.toDF(docs_schema).withColumnRenamed("filepath", "cand_filepath") \
                                                   .withColumnRenamed("text_content", "cand_text_content")
        
        # For robust processing, handle if candidate_df is empty (should be caught by os.path.exists earlier)
        if candidate_df.count() == 0:
            print(f"Error: Candidate file '{candidate_file_path_expanded}' could not be loaded by Spark or is empty. Exiting.")
            return

        # Text Cleaning (using UDF)
        clean_udf = F.udf(clean_text_udf_func, StringType())
        cleaned_essays_df = essays_df.withColumn("cleaned_text", clean_udf(F.col("text_content")))
        cleaned_candidate_df = candidate_df.withColumn("cleaned_text", clean_udf(F.col("cand_text_content")))

        # Tokenization
        tokenizer = RegexTokenizer(inputCol="cleaned_text", outputCol="raw_words", pattern="\\s+|[.?!]", toLowercase=False)
        # pattern splits by spaces or sentence terminators. Adjust if needed.
        tokenized_essays_df = tokenizer.transform(cleaned_essays_df)
        tokenized_candidate_df = tokenizer.transform(cleaned_candidate_df)

        # Stop Words Removal (optional, but can improve relevance)
        stopwords_remover = StopWordsRemover(inputCol="raw_words", outputCol="words")
        processed_essays_df = stopwords_remover.transform(tokenized_essays_df)
        processed_candidate_df = stopwords_remover.transform(tokenized_candidate_df)
        
        # Filter out docs that are empty after processing (no words)
        # This check should be on the 'words' column
        processed_essays_df = processed_essays_df.filter(F.size(F.col("words")) > 0)
        if processed_essays_df.count() == 0:
            print(f"Error: No essay documents have content after text processing. Exiting.")
            return
        
        # Same check for candidate (though it's a single doc)
        candidate_word_count = processed_candidate_df.select(F.size(F.col("words")).alias("wc")).first()["wc"]
        if candidate_word_count == 0:
            print(f"Error: Candidate document has no content after text processing. Exiting.")
            return

        # TF-IDF Feature Engineering
        hashing_tf = HashingTF(inputCol="words", outputCol="raw_features", numFeatures=num_features_tf)
        tf_essays_df = hashing_tf.transform(processed_essays_df)
        tf_candidate_df = hashing_tf.transform(processed_candidate_df)

        idf = IDF(inputCol="raw_features", outputCol="features")
        # Fit IDF model on the corpus of essays (excluding candidate for strictness, or include for global IDF)
        # For this lab, common practice is to fit IDF on the main corpus.
        idf_model = idf.fit(tf_essays_df) 
        
        tfidf_essays_df = idf_model.transform(tf_essays_df)
        tfidf_candidate_df = idf_model.transform(tf_candidate_df) # Use same IDF model

        # Extract candidate TF-IDF vector
        candidate_vector_row = tfidf_candidate_df.select("features").first()
        if not candidate_vector_row or candidate_vector_row["features"] is None:
            print("Error: Failed to compute TF-IDF vector for the candidate document.")
            return
        candidate_vector = candidate_vector_row["features"]

        if candidate_vector.norm(2) == 0.0:
            print("Error: Candidate TF-IDF vector has zero norm (empty or all zero features). Cannot compute similarity.")
            return

        # Broadcast candidate vector for efficient use in UDF
        candidate_vector_bc = sc.broadcast(candidate_vector)

        # Calculate Cosine Similarity using UDF
        # The UDF needs to be created with the broadcast variable in its closure
        cosine_similarity_udf = F.udf(calculate_cosine_similarity_udf_func(candidate_vector_bc), DoubleType())

        # Apply UDF to essays DataFrame
        # Select only filepath and features to avoid issues with other columns in UDF
        essays_with_similarity_df = tfidf_essays_df.select("filepath", "features") \
            .withColumn("similarity", cosine_similarity_udf(F.col("features")))

        # Filter out essays identical to the candidate (if candidate was in essays_path_glob)
        # This uses basename for comparison, assuming candidate filename is unique.
        candidate_basename = os.path.basename(candidate_file_path_expanded)
        essays_with_similarity_df = essays_with_similarity_df.filter(F.element_at(F.split(F.col("filepath"), "/"), -1) != candidate_basename)

        # Sort by similarity (descending) and take top N
        top_similar_df = essays_with_similarity_df.orderBy(F.col("similarity").desc()).limit(top_n_similar)
        
        print(f"\n--- Top {top_n_similar} most similar essays to '{candidate_basename}' ---")
        results = top_similar_df.select("filepath", "similarity").collect() # Collect results to driver

        if not results:
            print("No similar essays found (or all similarities were zero).")
        else:
            for row in results:
                filename = os.path.basename(row.filepath)
                print(f"- {filename}: Similarity = {row.similarity:.4f}")

    except Exception as e:
        print(f"An critical error occurred during Plagiarism Detection: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        if spark:
            print("\nStopping SparkSession.")
            spark.stop()

if __name__ == "__main__":
    print("Starting Plagiarism Detection analysis (Lab 7 - Python MLLib).")
    
    # Default paths
    # Ensure these paths are correct for the execution environment.
    default_essays_glob = "~/data/essays/*.txt" 
    default_candidate_file = "~/data/essays/candidate.txt" # Example name

    # Check SPARK_HOME
    if not os.environ.get("SPARK_HOME"):
        print("WARNING: SPARK_HOME environment variable is not set.")
        
    # Allow overriding paths via command-line arguments (example)
    essays_glob_arg = sys.argv[1] if len(sys.argv) > 1 else default_essays_glob
    candidate_file_arg = sys.argv[2] if len(sys.argv) > 2 else default_candidate_file
    
    print(f"Using essays glob: {essays_glob_arg}")
    print(f"Using candidate file: {candidate_file_arg}")

    run_plagiarism_detection(essays_glob_arg, candidate_file_arg)
    print("\nPlagiarism Detection analysis finished.")
