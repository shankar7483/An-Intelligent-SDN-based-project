# An Intelligent SDN-Based Framework Leveraging Machine Learning to Enhance IoT Performance in Smart Healthcare

## 📌 Project Overview
This project integrates **Software-Defined Networking (SDN)** with **Wireless Sensor Networks (WSN)** to create an intelligent healthcare monitoring system. It utilizes an SDN controller to manage real-time data from IoT sensors, prioritizing critical health alerts (Heart Rate, SpO2) and optimizing network traffic through Machine Learning-driven path selection.



## 🚀 Key Features
* **Real-Time Health Monitoring:** Integration with ESP32, MAX30102 (Pulse Oximeter), and DHT11 sensors for live vitals tracking.
* **Intelligent SDN Controller:** Centralized control plane for dynamic routing and emergency data prioritization.
* **Predictive Analytics:** Machine Learning implementation to enhance IoT performance and network reliability.
* **Network Visualization:** Real-time topology generation and traffic analysis (Latency, Throughput, Jitter).
* **Secure Authentication:** SHA-256 hashed login system for role-based access to the medical dashboard.

## 🛠 Tech Stack
* **Languages:** Python 3.x (Controller/Dashboard), C++ (Arduino/ESP32)
* **Libraries:** Tkinter (GUI), Matplotlib (Analytics), NetworkX (Topology), Sockets (Networking)
* **Hardware:** ESP32 Microcontroller, MAX30102 Sensor, DHT11 Sensor
* **Protocols:** SDN-inspired Control Protocol, TCP/IP

## 📂 Project Structure
* `Controller/`: Python-based SDN controller and GUI dashboard.
* `Firmware/`: ESP32 source code for sensor data collection.
* `Analytics/`: Modules for calculating network performance metrics.
* `Docs/`: Project report and architectural diagrams.

## 💻 Setup and Installation
1.  **Hardware:** Connect the MAX30102 and DHT11 sensors to the ESP32 pins as defined in the firmware.
2.  **Firmware:** Upload the `.ino` sketch to the ESP32 using Arduino IDE.
3.  **Software:** ```bash
    pip install matplotlib networkx
    python main_dashboard.py
    ```

## 📊 Performance Analysis
The framework evaluates SDN vs. Traditional Networking based on:
* Packet Delivery Ratio (PDR)
* Average End-to-End Latency
* Energy Consumption per Node
