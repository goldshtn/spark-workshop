import os
import sys
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, DateType
import matplotlib # Important: Use a non-interactive backend for scripts
matplotlib.use('Agg') # Must be called before importing pyplot
import matplotlib.pyplot as plt

# Assuming pyspark_csv.py is in the same directory as this script
# Add the directory of this script to sys.path to locate pyspark_csv
script_dir = os.path.dirname(os.path.abspath(__file__))
# If solutions/python/pyspark_csv.py, then script_dir is solutions/python
# So pyspark_csv should be found directly if it's in the same dir.
sys.path.insert(0, script_dir) 


# Now import the load_csv function
try:
    # This will look for pyspark_csv.py in script_dir (solutions/python)
    from pyspark_csv import load_csv 
except ImportError as e:
    print(f"Error importing pyspark_csv: {e}")
    print(f"Make sure pyspark_csv.py is in the directory: {script_dir} or on PYTHONPATH.")
    # Attempt to give more context on where it's looking
    print(f"Current sys.path: {sys.path}")
    # Check if the file actually exists where expected
    expected_path = os.path.join(script_dir, "pyspark_csv.py")
    if not os.path.exists(expected_path):
        print(f"File not found at expected path: {expected_path}")
    sys.exit(1)

def run(data_path="~/data/uk-property-prices.csv", plot_path="solutions/python/property_prices_plot.png"):
    spark = None
    try:
        spark = SparkSession.builder \
            .appName("UKPropertyPriceAnalysis") \
            .master("local[*]") \
            .getOrCreate()
        
        sc = spark.sparkContext

        # Add pyspark_csv.py to SparkContext so workers can use it
        pyspark_csv_path = os.path.join(script_dir, "pyspark_csv.py")
        if os.path.exists(pyspark_csv_path):
            sc.addFile(pyspark_csv_path)
            print(f"Added {pyspark_csv_path} to SparkContext")
        else:
            # This case should ideally be caught by the import check earlier if running locally,
            # but good for workers if path issues occur.
            print(f"CRITICAL: {pyspark_csv_path} not found. UDFs or modules relying on it on workers might fail.")
            # Depending on strictness, might sys.exit(1) here too.

        print(f"Loading CSV data from: {data_path}")
        # The custom load_csv function requires SparkContext as its first argument.
        # The pyspark_csv.py I wrote in the previous step uses sc.textFile and SparkSession.builder.getOrCreate()
        # It is better to ensure it uses the passed SparkContext.
        # For now, assuming the load_csv in my pyspark_csv.py is compatible or adapts.
        prop_df = load_csv(sc, data_path, header=True)

        print("Schema inferred by pyspark_csv.py:")
        prop_df.printSchema()
        
        # Data Cleaning and Transformation
        # Convert Price to Double, Date to DateType.
        # Need to check actual column names from CSV header, pyspark_csv should strip them.
        # Example Header: Transaction unique identifier,Price,Date of Transfer,Postcode,Property Type,Old/New,Duration
        # Assuming standard names for now: Price, Date, Postcode, PropertyType
        
        # Standardize column names (example: remove spaces, convert to snake_case)
        # For now, assume pyspark_csv.py handles basic stripping of quotes/spaces from header names.
        # Let's use the names as they might appear (case-sensitive)
        
        price_col_name = "Price" # Adjust if CSV header is different
        date_col_name = "Date of Transfer" # Adjust if CSV header is different (e.g. "Date")
        postcode_col_name = "Postcode"
        property_type_col_name = "Property Type" # Adjust (e.g. "PropertyType")

        # Check if columns exist before trying to cast
        if price_col_name not in prop_df.columns:
            print(f"Error: Price column '{price_col_name}' not found in DataFrame. Available: {prop_df.columns}")
            # Fallback or raise error
            # For now, let's try a common alternative or let it fail if truly missing.
            price_col_name = next((c for c in prop_df.columns if c.lower() == "price"), None)
            if not price_col_name: raise ValueError("Price column not found")
        
        if date_col_name not in prop_df.columns:
            print(f"Error: Date column '{date_col_name}' not found in DataFrame. Available: {prop_df.columns}")
            date_col_name = next((c for c in prop_df.columns if "date" in c.lower()), None)
            if not date_col_name: raise ValueError("Date column not found")


        if dict(prop_df.dtypes)[price_col_name] == 'string':
            prop_df = prop_df.withColumn(price_col_name, F.col(price_col_name).cast(DoubleType()))
        
        # Date handling: pyspark_csv.py's infer_type returns TimestampType for dates.
        # If it's still string, parsing might have failed.
        # Spark's to_date can be more robust if format is known or mostly standard.
        if dict(prop_df.dtypes)[date_col_name] == 'string':
            prop_df = prop_df.withColumn(date_col_name, F.to_date(F.col(date_col_name))) # Assumes standard date format
        
        # Ensure it's DateType for year() function, not TimestampType for simplicity here.
        # If it's TimestampType from pyspark_csv, cast to DateType.
        if str(dict(prop_df.dtypes)[date_col_name]).lower().startswith('timestamp'):
             prop_df = prop_df.withColumn(date_col_name, F.col(date_col_name).cast(DateType()))

        prop_df = prop_df.withColumn("Year", F.year(F.col(date_col_name)))
        
        # Rename columns for easier SQL querying if needed (e.g. remove spaces)
        prop_df = prop_df.withColumnRenamed(price_col_name, "Price") \
                         .withColumnRenamed(date_col_name, "Date") \
                         .withColumnRenamed(postcode_col_name, "Postcode") \
                         .withColumnRenamed(property_type_col_name, "PropertyType")

        prop_df.createOrReplaceTempView("property_prices")
        print(f"Successfully loaded and processed records. Count: {prop_df.count()}")
        prop_df.persist()

        # Query 1: Average price per year
        print("\nQuery 1: Average price per year")
        avg_price_per_year = spark.sql("""
            SELECT Year, AVG(Price) as AveragePrice
            FROM property_prices
            WHERE Price IS NOT NULL AND Year IS NOT NULL AND Price > 0 /* Basic sanity check */
            GROUP BY Year
            ORDER BY Year
        """)
        avg_price_per_year.show()

        # Query 2: Top 5 postcodes with the highest average price in the most recent year
        print("\nQuery 2: Top 5 postcodes with highest average price (most recent year)")
        max_year_row = prop_df.select(F.max("Year")).first()
        if max_year_row and max_year_row[0] is not None:
            most_recent_year = max_year_row[0]
            spark.sql(f"""
                SELECT Postcode, AVG(Price) as AveragePrice
                FROM property_prices
                WHERE Year = {most_recent_year} AND Price IS NOT NULL AND Postcode IS NOT NULL AND Price > 0
                GROUP BY Postcode
                ORDER BY AveragePrice DESC
                LIMIT 5
            """).show()
        else:
            print("Could not determine the most recent year or 'Year' column missing/empty.")

        # Query 3: Number of sales per property type
        print("\nQuery 3: Number of sales per property type")
        spark.sql("""
            SELECT PropertyType, COUNT(*) as NumberOfSales
            FROM property_prices
            WHERE PropertyType IS NOT NULL
            GROUP BY PropertyType
            ORDER BY NumberOfSales DESC
        """).show()

        print("\nPreparing data for plotting (Average price per year)...")
        plot_data_pd = avg_price_per_year.orderBy("Year").toPandas()

        if not plot_data_pd.empty:
            plt.figure(figsize=(12, 7)) # Adjusted size
            plt.plot(plot_data_pd["Year"], plot_data_pd["AveragePrice"], marker='o', linestyle='-')
            plt.title("Average Property Price in the UK Over Years", fontsize=16)
            plt.xlabel("Year", fontsize=14)
            plt.ylabel("Average Price (£)", fontsize=14)
            plt.grid(True, which='both', linestyle='--', linewidth=0.5)
            
            # Ensure years are integers and displayed nicely
            min_year, max_year = int(plot_data_pd["Year"].min()), int(plot_data_pd["Year"].max())
            plt.xticks(range(min_year, max_year + 1, max(1, (max_year - min_year) // 10))) # Auto-adjust step
            plt.tick_params(axis='x', rotation=45)
            plt.gca().get_yaxis().set_major_formatter(
                plt.FuncFormatter(lambda x, p: format(int(x), ','))) # Format y-axis ticks as numbers with commas

            plt.tight_layout()
            
            plot_dir = os.path.dirname(os.path.abspath(plot_path)) # Use absolute path for safety
            if not os.path.exists(plot_dir) and plot_dir:
                os.makedirs(plot_dir)
                print(f"Created directory for plot: {plot_dir}")

            plt.savefig(plot_path, dpi=150) # Save with higher DPI
            print(f"Plot saved to {os.path.abspath(plot_path)}")
        else:
            print("No data to plot or plot data frame was empty.")

        prop_df.unpersist()

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc() # Print full traceback
    finally:
        if spark:
            spark.stop()
            print("SparkSession stopped.")

if __name__ == "__main__":
    print("Starting UK Property Price Analysis Spark job.")
    default_data_path = "~/data/uk-property-prices.csv" 
    # Ensure plot path is relative to the repo root or an absolute path the user can access
    default_plot_path = os.path.join(os.getcwd(), "solutions", "python", "property_prices_plot.png")

    data_path_arg = sys.argv[1] if len(sys.argv) > 1 else default_data_path
    plot_path_arg = sys.argv[2] if len(sys.argv) > 2 else default_plot_path
    
    print(f"Using data path: {data_path_arg}")
    print(f"Plot will be saved to: {plot_path_arg}")
    run(data_path_arg, plot_path_arg)
    print("UK Property Price Analysis Spark job finished.")
