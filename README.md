<div align="center">

# Asian Quant

A lightweight, asynchronous, multi-strategy market scanning engine.

<br/>

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Made with ❤️](https://img.shields.io/badge/made%20with-%E2%9D%A4-red.svg)]()

</div>

---

## 🌟 Overview

**Asian Quant** is a high-performance market scanning engine designed for traders and developers who need speed and flexibility. It leverages Python's asynchronous capabilities to process vast amounts of market data, calculate complex indicator chains, and identify trading opportunities across multiple strategies simultaneously.

## ✨ Features

-   **Asynchronous Batch Processing:** Powered by `asyncio` for high-concurrency data fetching and computation.
-   **Chained Indicator Calculation:** Efficiently link multiple technical indicators where the output of one serves as the input for another.
-   **Multi-Strategy Support:** Scan the entire market using various strategy logics in a single pass.
-   **Signal & Report Generation:** Automatically outputs strategy signals and generates comprehensive analytical reports for decision-making.
-   **Lightweight & Scalable:** Minimal overhead with a focus on core scanning performance.

---

## 🛠 Installation & Setup

### Prerequisites

-   **Python:** 3.11 or higher
-   **Database:** MySQL 8.0+

### Step-by-Step Setup

1.  **Environment Preparation**
    Create and activate a virtual environment to keep your dependencies isolated:
    ```bash
    python3.11 -m venv ./asian-quant/venv311
    
    # On macOS/Linux:
    source ./asian-quant/venv311/bin/activate
    # On Windows:
    # .\asian-quant\venv311\Scripts\activate
    ```

2.  **Install Dependencies**
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```

3.  **Database Initialization**
    Initialize your MySQL database using the provided schema:
    ```bash
    # Execute the SQL script in your MySQL client
    # Path: data/sqls
    ```

4.  **Run the Engine**
    ```bash
    python app.py
    ```

---

## 📂 Project Structure (Optional)

-   `data/`: Contains database schemas and static data.
-   `strategies/`: Define your custom trading logic here.
-   `indicators/`: Library for chained technical indicators.
-   `reports/`: Automated output of market analysis.

---

## 📄 License

This project is licensed under the **MIT License**.

---