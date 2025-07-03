# 🛠️ Final Project - EPD048: Heuristics and Metaheuristics

---

## 📘 Project Overview

This repository contains the final project for the course **EPD048 - Heuristics and Metaheuristics**, focusing on solving the **Flexible Job Shop Scheduling Problem (FJSSP)** — also known as the **Job Shop Problem with Parallel Machines**.

---

## 🧩 Problem Description

The **FJSSP** is a complex combinatorial optimization problem where each operation can be processed on one of several machines, introducing flexibility in routing. The challenge lies in selecting the machine for each operation and scheduling the operations to minimize the overall makespan.

---

## 🧠 Implemented Approaches

This project explores two main strategies:

- **Modified Shifting Bottleneck Procedure (SBP)**:  
  A classical approach for solving the Job Shop Scheduling Problem (JSSP), adapted here to better accommodate the flexibility of FJSSP. The method first assigns machines to operations, transforming the FJSSP into a JSSP instance, which is then solved using the SBP.

- **Simulated Annealing (SA)**:  
  A metaheuristic technique integrated with the SBP to enhance solution quality by escaping local optima and exploring the solution space more effectively.

---

## 🧑‍💻 Software Engineering Practices

The codebase is designed with **robustness**, **modularity**, and **scalability** in mind:

- Developed using **Object-Oriented Programming (OOP)** principles
- Structured for **readability** and **maintainability**
- Follows **best practices** in software engineering to ensure production-readiness

---

## 🚀 How to Run

To execute the tool, use the `main.py` script with the following command-line arguments:

```bash
python main.py -i path/to/instance.txt -m SA -t 60
```

### 🔸 Available Arguments
- _**-i**_ or _**--instance**_:
Path to the input file containing the FJSSP instance.

- _**-m**_ or _**--method**_:
Solution method to be used. Available options:

  - **'cbc'**: solves the problem using the CBC solver

  - **'SA'**: applies Simulated Annealing

  - **'both'**: runs both approaches for comparison

- _**-t**_ or _**--timelimit**_:
Time limit in seconds for solving the problem (default: 300 seconds).

---

## 📄 Instance Format  

Each instance consists of:  
- First line: `<number of jobs> <number of machines>`
- Then one line per job: `<number of operations>` and then, for each operation, `<number of machines for this operation>` and for each machine, a pair `<machine> <processing time>`.
- Machine index starts at 0.

### 🔹 Example:  

```plaintext
2 3                             # 2 jobs, 3 machines

2 2 0 1 1 2 1 1 3               # job 0: 2 ops | 1st op: 2 eligible machines (p_m0 = 1, p_m1 = 2) | 2nd op: 1 eligible machine (p_m1 = 3)
3 2 0 2 2 1 1 1 2 2 1 3 2 4     # job 1: 3 ops | 1st op: 2 eligible machines (p_m0 = 2, p_m2 = 1) | 2nd op: 1 eligible machine (p_m1 = 2) | 3rd op: 2 eligible machines (p_m1 = 3, p_m2 = 4)
```
