from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql import types as T
import sys

def calculate_total_funding_py(funding_rounds):
    """
    Calculates the total funding from a list of funding rounds.
    Each round is a struct that might have a 'raised_amount'.
    Handles None for funding_rounds list or missing 'raised_amount'.
    """
    total_funding = 0.0
    if funding_rounds is not None:
        for round_info in funding_rounds:
            # Check if round_info is a Row and has 'raised_amount'
            if round_info is not None and hasattr(round_info, 'raised_amount') and round_info.raised_amount is not None:
                total_funding += float(round_info.raised_amount)
    return total_funding

def run(data_path="~/data/companies.json"):
    spark = None
    try:
        spark = SparkSession.builder \
            .appName("StartupAnalysis") \
            .master("local[*]") \
            .getOrCreate()

        # Register the UDF
        # It's good practice to define the UDF schema explicitly.
        # The funding_rounds field is an ArrayType of StructType.
        # We need to define the StructType for the elements within the array.
        # However, the UDF receives a Python list of Row objects.
        # Spark will handle the conversion. The input type to the UDF is ArrayType(StructType(...))
        # but the python function receives a list of Row-like objects.
        # The return type is DoubleType.
        
        # Define a simplified schema for a funding round for UDF robustness,
        # though Spark infers this from the DataFrame. The key is that the UDF
        # itself handles potentially missing 'raised_amount'.
        funding_round_schema = T.StructType([
            T.StructField("raised_amount", T.DoubleType(), True) 
            # Other fields in funding_rounds are not needed for this UDF
        ])
        
        spark.udf.register("calculate_total_funding", 
                           calculate_total_funding_py, 
                           T.DoubleType()) # Return type of the UDF

        print(f"Loading data from: {data_path}")
        # Spark's read.json can handle ~ paths usually.
        df = spark.read.json(data_path)
        df.createOrReplaceTempView("companies")
        
        print("Schema of the DataFrame:")
        df.printSchema()

        print(f"Successfully loaded {df.count()} records.")
        df.persist()

        # --- Queries ---

        # Query 1: Companies founded in 2005
        print("\nQuery 1: Companies founded in 2005")
        if "founded_year" in df.columns:
            spark.sql("""
                SELECT name, founded_year 
                FROM companies 
                WHERE founded_year = 2005
            """).show()
        else:
            print("Column 'founded_year' not found for Query 1.")

        # Query 2: Top 10 companies by number of employees
        print("\nQuery 2: Top 10 companies by number of employees")
        if "number_of_employees" in df.columns:
            spark.sql("""
                SELECT name, number_of_employees 
                FROM companies 
                WHERE number_of_employees IS NOT NULL
                ORDER BY number_of_employees DESC 
                LIMIT 10
            """).show()
        else:
            print("Column 'number_of_employees' not found for Query 2.")

        # Query 3: Companies with "Web" category and founded after 2000
        print("\nQuery 3: Companies with 'Web' category and founded after 2000")
        # category_code is often the field, but the lab implies checking 'tag_list' or 'category_code'
        # Assuming 'category_code' for simplicity as per typical schemas. If it means tags, query would change.
        if "category_code" in df.columns and "founded_year" in df.columns:
            spark.sql("""
                SELECT name, category_code, founded_year 
                FROM companies 
                WHERE category_code = 'web' AND founded_year > 2000
            """).show()
        elif "tag_list" in df.columns and "founded_year" in df.columns: # Alternative if category_code not present
             spark.sql("""
                SELECT name, tag_list, founded_year 
                FROM companies 
                WHERE array_contains(split(tag_list, ', '), 'web') AND founded_year > 2000
            """).show()
        else:
            print("Required columns ('category_code' or 'tag_list', and 'founded_year') not found for Query 3.")


        # Query 4: Top 10 companies by total funding (using UDF)
        print("\nQuery 4: Top 10 companies by total funding (using UDF)")
        if "funding_rounds" in df.columns: # UDF depends on this column
            spark.sql("""
                SELECT name, calculate_total_funding(funding_rounds) AS total_funding
                FROM companies
                ORDER BY total_funding DESC
                LIMIT 10
            """).show()
        else:
            print("Column 'funding_rounds' not found for Query 4 (UDF).")


        # Query 5: Companies with 'social' in their overview
        print("\nQuery 5: Companies with 'social' in their overview")
        if "overview" in df.columns:
            spark.sql("""
                SELECT name, overview 
                FROM companies 
                WHERE overview LIKE '%social%'
            """).show(truncate=50)
        else:
            print("Column 'overview' not found for Query 5.")

        # Query 6: Companies that have offices in 'New York'
        print("\nQuery 6: Companies with offices in 'New York'")
        # Offices is an array of structs. Each struct has a 'city'.
        if "offices" in df.columns:
            # This query requires exploding the offices array and then filtering.
            # This is more complex than a simple SQL check for column existence,
            # as it depends on the *structure* within the 'offices' column.
            # We assume 'offices' is an array of structs, and each struct has a 'city' field.
            # A robust check would inspect df.schema['offices'].dataType
            
            # A simpler way to check if the field likely exists and is an array:
            if isinstance(df.schema["offices"].dataType, T.ArrayType):
                 # Further check if the element type is a StructType and has 'city'
                 # For now, let's assume the structure if the column exists.
                 # The query will fail if the structure is not as expected.
                spark.sql("""
                    SELECT name, offices.city AS office_cities
                    FROM companies
                    WHERE array_contains(offices.city, 'New York')
                """).show()
            else:
                print("'offices' column is not an ArrayType as expected for Query 6.")
        else:
            print("Column 'offices' not found for Query 6.")

        df.unpersist()

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        if spark:
            spark.stop()
            print("SparkSession stopped.")

if __name__ == "__main__":
    print("Starting Startup Analysis Spark SQL job.")
    # Default path as per lab, can be overridden by command-line argument
    default_data_path = "~/data/companies.json" 
    
    # Example of how to allow path override via command line:
    # data_path = sys.argv[1] if len(sys.argv) > 1 else default_data_path
    # For this script, we'll stick to the default or a hardcoded one for simplicity
    # if not running via spark-submit with args.
    
    print(f"Using data path: {default_data_path}. Ensure this path is correct for your environment.")
    run(default_data_path)
    print("Startup Analysis Spark SQL job finished.")
