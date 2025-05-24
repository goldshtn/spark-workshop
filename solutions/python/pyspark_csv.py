#
# Copyright 2017 Databricks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from pyspark.sql.types import BooleanType, FloatType, StructType, StructField, StringType, TimestampType
from dateutil.parser import parse

# The MIT License (MIT)
#
# Copyright (c) 2014 Wimmics INRIA Sophia Antipolis
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

TrueStrings = frozenset(['TRUE', 'T'])
FalseStrings = frozenset(['FALSE', 'F'])

def infer_schema(sc, rdd, header=True, num_rows=5, default_type=StringType()):
    first_line = rdd.first()
    column_names = first_line.split(',')
    if not header:
        column_names = ['C%d' % i for i in range(len(column_names))] # Python 3: range

    data_rows = rdd.take(num_rows+1)[1:] if header else rdd.take(num_rows)
    
    column_types = []
    for i in range(len(column_names)): # Python 3: range
        column_values = [row.split(',')[i] for row in data_rows if i < len(row.split(','))] # Added bounds check
        column_types.append(infer_type(column_values, default_type))
    
    fields = []
    for i in range(len(column_names)): # Python 3: range
        fields.append(StructField(column_names[i].strip(), column_types[i], True)) # Added strip()
        
    return StructType(fields)

def infer_type(values, default_type=StringType()):
    values = [v for v in values if v is not None and v != ""] # Pythonic filter
    if not values: # Check if empty after filtering
        return default_type
    
    if all(is_int(v) for v in values): # Pythonic all with generator
        return FloatType() 
    elif all(is_float(v) for v in values): # Pythonic all with generator
        return FloatType()
    elif all(is_bool(v) for v in values): # Pythonic all with generator
        return BooleanType()
    elif all(is_date(v) for v in values): # Pythonic all with generator
        return TimestampType()
    else:
        return default_type

def is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False

def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False

def is_bool(value):
    return value.upper() in TrueStrings or value.upper() in FalseStrings

def is_date(value):
    if not isinstance(value, str): return False # Ensure value is a string
    try:
        parse(value)
        return True
    except: 
        return False

def str_to_bool(value):
    u_value = value.upper()
    if u_value in TrueStrings:
        return True
    elif u_value in FalseStrings:
        return False
    else:
        return None 

def load_csv(sc, path, header=True, num_rows_infer_schema=5, 
             delimiter=',', default_type=StringType(), 
             replace_empty_str_with_null=True, custom_schema=None):
    
    raw_rdd = sc.textFile(path)
    
    if custom_schema:
        schema = custom_schema
    else:
        schema = infer_schema(sc, raw_rdd, header, num_rows_infer_schema, default_type)
    
    column_names = schema.names # Get column names from the (inferred or custom) schema

    def parse_row(row_str):
        # This is a simplified parser. Real CSVs can have quoted delimiters, newlines etc.
        # Python's 'csv' module handles these complexities, but RDD parsing is row-by-row.
        # For robust CSV parsing with complex cases, using spark.read.csv is preferred.
        row_values = row_str.split(delimiter)
        
        parsed_values = []
        for i, val_str in enumerate(row_values):
            if i < len(schema.fields):
                field = schema.fields[i]
                field_type = field.dataType
                
                if replace_empty_str_with_null and val_str == "":
                    parsed_values.append(None)
                elif val_str is None or val_str == "": # Double check after split
                    parsed_values.append(None)
                elif isinstance(field_type, FloatType):
                    parsed_values.append(float(val_str) if is_float(val_str) else None)
                elif isinstance(field_type, BooleanType):
                    parsed_values.append(str_to_bool(val_str) if is_bool(val_str) else None)
                elif isinstance(field_type, TimestampType):
                    # Ensure dateutil.parser.parse is used for TimestampType
                    parsed_values.append(parse(val_str) if is_date(val_str) else None)
                elif isinstance(field_type, StringType):
                    parsed_values.append(val_str)
                else: # Default or unknown, try to cast or leave as string
                    try:
                        # Attempt a generic conversion based on what infer_type might have found
                        # This part is tricky if default_type was complex.
                        if is_int(val_str): parsed_values.append(float(val_str))
                        elif is_float(val_str): parsed_values.append(float(val_str))
                        elif is_bool(val_str): parsed_values.append(str_to_bool(val_str))
                        elif is_date(val_str): parsed_values.append(parse(val_str))
                        else: parsed_values.append(val_str)
                    except:
                        parsed_values.append(val_str) # Fallback to string
            else:
                # If row has more values than schema fields, append as string (or handle as error)
                parsed_values.append(val_str) 
        
        # Ensure the number of parsed values matches the number of schema fields
        # Pad with None if fewer values were parsed than expected by schema
        while len(parsed_values) < len(schema.fields):
            parsed_values.append(None)
        # Truncate if more values were parsed (e.g. due to extra delimiters in data not handled by simple split)
        # This simple split won't handle quoted delimiters well.
        return tuple(parsed_values[:len(schema.fields)])


    data_rdd = raw_rdd.mapPartitionsWithIndex(
        lambda idx, it: list(it)[1:] if header and idx == 0 else it
    ).map(parse_row)
    
    from pyspark.sql import SparkSession, Row
    spark = SparkSession.builder.getOrCreate()

    # It's safer to create RDD of Row objects for createDataFrame
    # Ensure column_names are stripped of any extra spaces from header parsing
    clean_column_names = [name.strip() for name in column_names]
    
    def list_to_row(values_list):
        return Row(*values_list)

    # This part requires careful handling of schema and data types
    # The schema used for createDataFrame must match the data structure from parse_row
    # And parse_row must correctly convert types or Spark will error.
    # For robustness, spark.read.csv is generally preferred.
    
    # This version of load_csv is simplified. A full version would be much more complex
    # to correctly handle all CSV edge cases and type conversions.
    # The current schema inference and parsing is basic.
    
    # For creating DataFrame, ensure data_rdd outputs Row objects or tuples that Spark can infer.
    # If schema is StructType, RDD should contain list/tuple of values in schema order.
    return spark.createDataFrame(data_rdd, schema)


def evaluateType(x, default_type=StringType()):
    if x is None or x == "":
        # For Spark DataFrames, it's better to return None, which becomes SQL NULL.
        # The type will be taken from the StructField's type.
        # This function is more for schema inference helper.
        return default_type 

    if is_int(x):
        return FloatType() # Consistent with infer_type
    if is_float(x):
        return FloatType()
    if is_bool(x):
        return BooleanType()
    if is_date(x):
        return TimestampType()
    return default_type
