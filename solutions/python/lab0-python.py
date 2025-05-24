def wordcount(words):
    freqs = {}
    for word in words:
        freqs[word] = freqs.setdefault(word, 0) + 1
    return freqs

def evens(numbers):
    return filter(lambda n: n % 2 == 0, numbers)

def squares(numbers):
    return map(lambda n: n * n, numbers)

def avg_length(words):
    # Ensure words is not empty to avoid ZeroDivisionError
    if not words:
        return 0.0
    return reduce(lambda sum_len, word: sum_len + len(word), words, 0) / float(len(words))

def problem6():
    # xrange is for Python 2. In Python 3, range behaves like xrange.
    # Assuming Python 2 context as per the lab description.
    # If running in Python 3, replace xrange with range.
    try:
        # For Python 2
        nums = xrange(1, 101) # Corrected to include 100
    except NameError:
        # For Python 3
        nums = range(1, 101) # Corrected to include 100

    sum_of_squares = sum(map(lambda x: x*x, nums))
    square_of_sum = sum(nums)**2
    return square_of_sum - sum_of_squares # The problem asks for square_of_sum - sum_of_squares

def run():
    print("Lab 0: Python Fundamentals")
    print("Testing wordcount:")
    print(wordcount(["the", "fox", "jumped", "over", "the", "dog"]))
    # Expected: {'the': 2, 'fox': 1, 'jumped': 1, 'over': 1, 'dog': 1} (order may vary)

    print("\nTesting evens:")
    print(list(evens(range(10)))) # Use list() to display filter object output
    # Expected: [0, 2, 4, 6, 8]

    print("\nTesting squares:")
    print(list(squares(range(5)))) # Use list() to display map object output
    # Expected: [0, 1, 4, 9, 16]

    print("\nTesting avg_length:")
    print(avg_length(["hello", "world", "python"]))
    # Expected: (5 + 5 + 6) / 3.0 = 5.333...
    print(avg_length([])) # Test empty list case
    # Expected: 0.0

    print("\nTesting problem6:")
    print(problem6())
    # Expected: 25164150 (for first 100 natural numbers)

if __name__ == "__main__":
    # Make sure to import reduce for Python 3 if not already available
    # from functools import reduce # Uncomment if using Python 3 and reduce is not found
    run()
