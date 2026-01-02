import matplotlib.pyplot as plt

# Reducer counts
reducers = [2, 4, 8, 16]

# Execution times (seconds)
task1 = [1080, 610, 440, 335]   # Popular Routes
task2 = [1025, 585, 405, 312]   # Expensive Routes
task3 = [970, 535, 365, 290]    # Visited Locations
task4 = [915, 392, 302, 298]    # Nightlife

# Plot style
plt.figure(figsize=(8,6))
plt.plot(reducers, task1, 'o-', label='Task 1: Popular Routes')
plt.plot(reducers, task2, 's--', label='Task 2: Expensive Routes')
plt.plot(reducers, task3, 'd-.', label='Task 3: Visited Locations')
plt.plot(reducers, task4, '^-', label='Task 4: Nightlife')

plt.title('Reducer Count vs Execution Time for All MapReduce Tasks', fontsize=14)
plt.xlabel('Number of Reducers', fontsize=12)
plt.ylabel('Execution Time (seconds)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.6)
plt.legend()
plt.tight_layout()
plt.savefig('reducers_vs_time_all.jpeg', dpi=300)
plt.show()
